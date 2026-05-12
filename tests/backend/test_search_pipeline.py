import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.search_pipeline import SearchPipeline
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


async def _make_pipeline_with_client(chunks: list) -> tuple:
    client = AsyncQdrantClient(":memory:")
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    pipeline.retriever.client = client
    pipeline.expand_query = AsyncMock(side_effect=lambda q, **_: [q])

    collection_name = "pali_canon"
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=pipeline.retriever.embedding_mgr.dimension,
            distance=models.Distance.COSINE,
        ),
    )

    if chunks:
        points = [
            models.PointStruct(
                id=idx,
                vector=pipeline.retriever.embedding_mgr.encode(f"{c['pali']} {c['english']}"),
                payload=c,
            )
            for idx, c in enumerate(chunks)
        ]
        await client.upsert(collection_name=collection_name, points=points)

    return pipeline, client


@pytest.mark.asyncio
async def test_search_pipeline_retrieval():
    chunks = [
        {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Thus have I heard"},
        {"id": "DN 1:2", "pali": "tada", "english": "then"},
        {"id": "MN 10:1", "pali": "Samyutta", "english": "Connected Discourses"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)

    results = await pipeline.search("Thus have I heard", top_k=1)

    assert len(results) == 1
    assert results[0]["id"] == "DN 1:1"
    assert results[0]["english"] == "Thus have I heard"


@pytest.mark.asyncio
async def test_search_pipeline_empty_results():
    pipeline, _ = await _make_pipeline_with_client([])

    results = await pipeline.search("something that doesn't exist", top_k=5)
    assert len(results) == 0
