from typing import Any
import asyncio
from concurrent.futures import Executor

from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import EmbeddingManager


class Retriever:
    """
    Vector retrieval against a single Qdrant collection.
    Decoupled from query expansion and reranking.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        embedding_mgr: EmbeddingManager,
        collection_name: str,
        executor: Executor,
    ):
        self.client = client
        self.embedding_mgr = embedding_mgr
        self.collection_name = collection_name
        self.executor = executor

    async def retrieve(
        self,
        query: str,
        top_k: int,
        nikayas: list[str] | None = None,
        exclude_commentary: bool = False,
    ) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        query_vector = await loop.run_in_executor(self.executor, self.embedding_mgr.encode, query)
        must: list[models.FieldCondition] = []
        must_not: list[models.FieldCondition] = []
        if nikayas:
            must.append(models.FieldCondition(key="nikaya", match=models.MatchAny(any=nikayas)))
        if exclude_commentary:
            # Canon verses omit `section`; commentary verses carry "commentary"
            # (#101). must_not drops commentary while leaving canon intact, so
            # the answer flow's context slots fill with canon passages (#102).
            must_not.append(models.FieldCondition(key="section", match=models.MatchValue(value="commentary")))
        qdrant_filter = None
        if must or must_not:
            qdrant_filter = models.Filter(must=must, must_not=must_not)
        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=qdrant_filter,
        )
        results: list[dict[str, Any]] = []
        for r in response.points:
            if not r.payload.get("english", "").strip():
                continue
            chunk: dict[str, Any] = {
                "id": r.payload.get("id"),
                "pali": r.payload.get("pali"),
                "english": r.payload.get("english"),
                "score": r.score,
            }
            # Translator-commentary marker, carried through so the results API
            # can flag commentary and the answer flow can exclude it (#101).
            section = r.payload.get("section")
            if section:
                chunk["section"] = section
            results.append(chunk)
        return results
