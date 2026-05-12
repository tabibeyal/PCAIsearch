from typing import List, Dict, Any, Optional, Set
import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor
from openai import AsyncOpenAI
from sentence_transformers import CrossEncoder
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from backend.app.core.indexing import EmbeddingManager
from backend.app.services.retriever import Retriever
from backend.app.services.sutta_relations import SuttaRelations


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
    "Never invent sutta numbers or modify source text. "
    "No HTML tags. "
    "\n\n"
    "CITATIONS: After every sentence that draws on a source, insert the citation ID in square brackets "
    "directly after the sentence, e.g. '...all conditioned things are impermanent. [SN 22.12:3]' "
    "Use the exact ID string from the context (the part before the word 'Pali:'). "
    "Multiple citations go in one bracket, comma-separated: [SN 22.12:3, AN 6.98:3]. "
    "NEVER use parentheses () for citations — square brackets [] only. "
    "\n\n"
    "Format your response as follows:\n"
    "- Write a full introductory paragraph that situates the topic in its doctrinal context. Keep each paragraph to at most 5 sentences.\n"
    "- Follow with a bullet-point section that breaks down the key teachings, one idea per bullet. "
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
    "- End with a closing paragraph (at most 5 sentences) that draws the threads together and notes any nuance or limitation in the retrieved texts.\n"
    "\n"
    "Aim for a thorough, well-developed answer — roughly three times longer than a minimal response would be. "
    "Let there be visual breathing room between sections."
)


def _build_messages(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    context_text = "\n\n".join(
        f"[{c['id']}] Pali: {c['pali']}\nEnglish: {c['english']}"
        for c in chunks
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"},
    ]

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
        sutta_relations: Optional[SuttaRelations] = None,
    ):
        self._executor = ThreadPoolExecutor(max_workers=4)
        client = AsyncQdrantClient(url=qdrant_url)
        embedding_mgr = EmbeddingManager(model_name=model_name)
        self.collection_name = "pali_canon"
        self.retriever = Retriever(client, embedding_mgr, self.collection_name, self._executor)
        self.llm_model = llm_model
        self.llm = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY"),
            timeout=30.0,
        )
        self.reranker = Reranker()
        self.sutta_relations = sutta_relations

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

    async def search(self, query: str, top_k: int = 10, nikayas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        queries = await self.expand_query(query)

        per_query = await asyncio.gather(*[self.retriever.retrieve(q, top_k, nikayas) for q in queries])

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
        """
        if self.sutta_relations is None:
            return []
        retrieved_suttas: Set[str] = set()
        for r in results[:top_n]:
            sid = _extract_sutta_id(r.get("id", ""))
            if sid:
                retrieved_suttas.add(sid)
        related: Set[str] = set()
        for sutta_id in retrieved_suttas:
            for ref in self.sutta_relations.get_related(sutta_id):
                if ref not in retrieved_suttas:
                    related.add(ref)
        return sorted(related)

    async def synthesize(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        message = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            messages=_build_messages(query, context_chunks),
        )
        return _strip_thinking(message.choices[0].message.content)

    async def stream_synthesize(self, query: str, context_chunks: List[Dict[str, Any]]):
        stream = await self.llm.chat.completions.create(
            model=self.llm_model,
            max_tokens=1024,
            timeout=120.0,
            stream=True,
            messages=_build_messages(query, context_chunks),
        )
        full_text = ""
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                yield {"type": "chunk", "text": delta}
        yield {"type": "full", "text": _strip_thinking(full_text)}
