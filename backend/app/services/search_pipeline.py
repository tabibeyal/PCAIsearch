from typing import List, Dict, Any, Optional, Set
import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor
from openai import AsyncOpenAI
import numpy as np
from sentence_transformers import CrossEncoder
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import EmbeddingManager
from backend.app.services.canon_graph import CanonGraph


def _extract_sutta_id(chunk_id: str) -> Optional[str]:
    """Extract 'DN 15' from a chunk ID like 'DN 15:3'."""
    parts = chunk_id.rsplit(":", 1)
    return parts[0].strip() if len(parts) == 2 else None


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: List[dict]) -> List[dict]:
        if not chunks:
            return []
        pairs = [(query, f"{c.get('pali', '')} {c.get('english', '')}") for c in chunks]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(chunks, scores.tolist()), key=lambda x: x[1], reverse=True)
        return [{**chunk, "rerank_score": score} for chunk, score in ranked]

_SYSTEM_PROMPT = (
    "You are a scholarly assistant for the Pali Canon. "
    "Answer questions using only the provided context. "
    "Always cite sources with the exact [ID:Verse] format (e.g., [DN 1:1], [MN 10:5]). "
    "Never invent sutta numbers or modify source text. "
    "No HTML tags. "
    "\n\n"
    "Format your response as follows:\n"
    "- Write a full introductory paragraph that situates the topic in its doctrinal context.\n"
    "- Follow with a bullet-point section that breaks down the key teachings, one idea per bullet. "
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
    "- End with a closing paragraph that draws the threads together and notes any nuance or limitation in the retrieved texts.\n"
    "\n"
    "Aim for a thorough, well-developed answer — roughly three times longer than a minimal response would be. "
    "Let there be visual breathing room between sections."
)

_EXPANSION_PROMPT = (
    "You are a search query expander for a Pali Canon database. "
    "Given a user query, output up to 3 alternative phrasings that will improve "
    "semantic retrieval — include Pali terms, synonyms, and related concepts where relevant. "
    "Output one query per line, no numbering, no explanation."
)

class SearchPipeline:
    """
    Implements the RAG pipeline: Query Expansion -> Retrieval -> Synthesis.
    """
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        llm_model: str = os.environ.get("LLM_MODEL", "google/gemma-3n-e4b-it"),
        canon_graph: Optional[CanonGraph] = None,
    ):
        self.client = AsyncQdrantClient(url=qdrant_url)
        self.embedding_mgr = EmbeddingManager(model_name=model_name)
        self.collection_name = "pali_canon"
        self.llm_model = llm_model
        self.llm = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY"),
            timeout=30.0,
        )
        self.reranker = Reranker()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.canon_graph = canon_graph

    def shutdown(self):
        self._executor.shutdown(wait=True)

    async def expand_query(self, query: str) -> List[str]:
        message = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": _EXPANSION_PROMPT},
                {"role": "user", "content": query},
            ],
        )
        raw = _strip_thinking(message.choices[0].message.content)
        extras = [line.strip() for line in raw.splitlines() if line.strip()]
        seen: set = {query}
        variants = [query]
        for v in extras:
            if v not in seen:
                seen.add(v)
                variants.append(v)
        return variants[:3]

    async def _retrieve_one(self, q: str, top_k: int) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        query_vector = await loop.run_in_executor(self._executor, self.embedding_mgr.encode, q)
        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "id": r.payload.get("id"),
                "pali": r.payload.get("pali"),
                "english": r.payload.get("english"),
                "score": r.score,
            }
            for r in response.points
        ]

    async def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        queries = await self.expand_query(query)

        per_query = await asyncio.gather(*[self._retrieve_one(q, top_k) for q in queries])

        seen_ids: set = set()
        all_results: List[Dict[str, Any]] = []
        for batch in per_query:
            for result in batch:
                if result["id"] not in seen_ids:
                    seen_ids.add(result["id"])
                    all_results.append(result)

        return self.reranker.rerank(query, all_results)[:top_k]

    def get_related_suttas(self, results: List[Dict[str, Any]], top_n: int = 5) -> List[str]:
        """
        Return canonically related sutta IDs not already in the top results.
        Uses the CanonGraph's doctrinal pairs and structural adjacency.
        """
        if self.canon_graph is None:
            return []
        retrieved_suttas: Set[str] = set()
        for r in results[:top_n]:
            sid = _extract_sutta_id(r.get("id", ""))
            if sid:
                retrieved_suttas.add(sid)
        related: Set[str] = set()
        for sutta_id in retrieved_suttas:
            for ref in self.canon_graph.get_related(sutta_id):
                if ref not in retrieved_suttas:
                    related.add(ref)
        return sorted(related)

    async def synthesize(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join(
            f"[{c['id']}] Pali: {c['pali']}\nEnglish: {c['english']}"
            for c in context_chunks
        )
        message = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"},
            ],
        )
        return _strip_thinking(message.choices[0].message.content)

    async def stream_synthesize(self, query: str, context_chunks: List[Dict[str, Any]]):
        context_text = "\n\n".join(
            f"[{c['id']}] Pali: {c['pali']}\nEnglish: {c['english']}"
            for c in context_chunks
        )
        stream = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            stream=True,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"},
            ],
        )
        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield {"type": "chunk", "text": delta}
        yield {"type": "full", "text": _strip_thinking(full_text)}
