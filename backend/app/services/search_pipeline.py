from typing import List, Dict, Any
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
import anthropic
import numpy as np
from sentence_transformers import CrossEncoder
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import EmbeddingManager


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
    "Never invent sutta numbers or modify source text."
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
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        llm_model: str = os.environ.get("LLM_MODEL", "claude-sonnet-4-6"),
    ):
        self.client = AsyncQdrantClient(url=qdrant_url)
        self.embedding_mgr = EmbeddingManager(model_name=model_name)
        self.collection_name = "pali_canon"
        self.llm_model = llm_model
        self.llm = anthropic.AsyncAnthropic()
        self.reranker = Reranker()
        self._executor = ThreadPoolExecutor(max_workers=4)

    def shutdown(self):
        self._executor.shutdown(wait=True)

    async def expand_query(self, query: str) -> List[str]:
        message = await self.llm.messages.create(
            model=self.llm_model,
            max_tokens=256,
            system=_EXPANSION_PROMPT,
            messages=[{"role": "user", "content": query}],
        )
        raw = message.content[0].text
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

    async def synthesize(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join(
            f"[{c['id']}] Pali: {c['pali']}\nEnglish: {c['english']}"
            for c in context_chunks
        )
        message = await self.llm.messages.create(
            model=self.llm_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nQuestion: {query}",
                }
            ],
        )
        return message.content[0].text
