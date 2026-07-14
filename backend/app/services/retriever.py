from typing import Any
import asyncio
from concurrent.futures import Executor

from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from backend.app.core.indexing import EmbeddingManager

# Commentary is ~6% of the corpus, so a 4x over-retrieve leaves ample canon
# headroom after the post-filter; the cap bounds Qdrant fetch latency (#105).
COMMENTARY_OVER_RETRIEVE_FACTOR = 4
COMMENTARY_OVER_RETRIEVE_CAP = 200


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
        if nikayas:
            must.append(models.FieldCondition(key="nikaya", match=models.MatchAny(any=nikayas)))
        qdrant_filter = models.Filter(must=must) if must else None

        # Qdrant Cloud free tier rejects any filtered query that lacks a payload
        # index ("Index required but not found") and also blocks index creation,
        # so a must_not on `section` can't work there (#105). Exclude commentary
        # in Python instead: over-retrieve, then drop `section: commentary`
        # chunks. Mirrors BM25Retriever's in-memory exclusion.
        limit = top_k
        if exclude_commentary:
            limit = min(top_k * COMMENTARY_OVER_RETRIEVE_FACTOR, COMMENTARY_OVER_RETRIEVE_CAP)

        response = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            query_filter=qdrant_filter,
        )
        results: list[dict[str, Any]] = []
        for r in response.points:
            if not r.payload.get("english", "").strip():
                continue
            if exclude_commentary and r.payload.get("section") == "commentary":
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
            if exclude_commentary and len(results) >= top_k:
                break
        return results
