import asyncio
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


# ---------------------------------------------------------------------------
# Reranker unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def reranker():
    from backend.app.services.search_pipeline import Reranker
    with patch("backend.app.services.search_pipeline.CrossEncoder") as MockCE:
        MockCE.return_value = MagicMock()
        r = Reranker()
    return r


@pytest.fixture
def two_chunks():
    return [
        {"id": "DN 1:1", "english": "Thus have I heard"},
        {"id": "MN 10:1", "english": "Right Mindfulness"},
    ]


def test_reranker_preserves_all_chunks(reranker, two_chunks):
    reranker.model.predict = MagicMock(return_value=np.array([0.8, 0.4]))
    result = reranker.rerank_multi(["mindfulness"], two_chunks)
    assert len(result) == 2


def test_reranker_adds_rerank_score(reranker, two_chunks):
    reranker.model.predict = MagicMock(return_value=np.array([0.8, 0.4]))
    result = reranker.rerank_multi(["mindfulness"], two_chunks)
    for chunk in result:
        assert "rerank_score" in chunk
        assert isinstance(chunk["rerank_score"], float)


def test_reranker_orders_highest_score_first(reranker, two_chunks):
    # MN 10:1 (index 1) scores higher; it should come first after reranking
    reranker.model.predict = MagicMock(return_value=np.array([0.3, 0.9]))
    result = reranker.rerank_multi(["mindfulness"], two_chunks)
    assert result[0]["id"] == "MN 10:1"
    assert result[1]["id"] == "DN 1:1"


def test_reranker_scores_reflect_model_output(reranker, two_chunks):
    reranker.model.predict = MagicMock(return_value=np.array([0.3, 0.9]))
    result = reranker.rerank_multi(["mindfulness"], two_chunks)
    # After sorting: MN 10:1 (0.9) first, DN 1:1 (0.3) second
    assert abs(result[0]["rerank_score"] - 0.9) < 1e-5
    assert abs(result[1]["rerank_score"] - 0.3) < 1e-5


def test_reranker_empty_input(reranker):
    result = reranker.rerank_multi(["any query"], [])
    assert result == []


def test_reranker_single_chunk(reranker):
    chunk = {"id": "SN 5:1", "english": "..."}
    reranker.model.predict = MagicMock(return_value=np.array([0.7]))
    result = reranker.rerank_multi(["query"], [chunk])
    assert len(result) == 1
    assert abs(result[0]["rerank_score"] - 0.7) < 1e-5


def test_reranker_reuses_loaded_model():
    """Heavy CrossEncoder models must be shared, not reloaded per instance."""
    from backend.app.services.search_pipeline import Reranker
    reranker_one = Reranker()
    reranker_two = Reranker()
    assert reranker_one.model is reranker_two.model


# ---------------------------------------------------------------------------
# Search pipeline integration
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_pipeline():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        from backend.app.services.search_pipeline import SearchPipeline
        p = SearchPipeline()
    client = AsyncQdrantClient(":memory:")
    p.retriever.client = client
    p.expand_query = AsyncMock(side_effect=lambda q, **_: [q])

    async def _setup():
        await client.create_collection(
            collection_name=p.collection_name,
            vectors_config=models.VectorParams(
                size=p.retriever.embedding_mgr.dimension,
                distance=models.Distance.COSINE,
            ),
        )

    asyncio.run(_setup())
    return p


@pytest.mark.asyncio
async def test_search_calls_reranker(in_memory_pipeline):
    p = in_memory_pipeline
    p.reranker = MagicMock()
    p.reranker.rerank_multi = MagicMock(return_value=[])

    await p.search("mindfulness", top_k=5)

    p.reranker.rerank_multi.assert_called_once()
    call_args = p.reranker.rerank_multi.call_args
    assert "mindfulness" in call_args.args[0]


@pytest.mark.asyncio
async def test_search_result_order_follows_reranker(in_memory_pipeline):
    """When the reranker reverses the retrieval order, the pipeline honours that order."""
    p = in_memory_pipeline

    chunks = [
        {"id": "DN 1:1", "english": "Thus have I heard"},
        {"id": "MN 10:1", "english": "Right Mindfulness"},
    ]
    for idx, c in enumerate(chunks):
        vector = p.retriever.embedding_mgr.encode(c['english'])
        await p.retriever.client.upsert(
            collection_name=p.collection_name,
            points=[models.PointStruct(id=idx, vector=vector, payload=c)],
        )

    reranked: list = []

    def fake_rerank(queries, candidates):
        result = [
            {**c, "rerank_score": 0.9 - i * 0.5}
            for i, c in enumerate(reversed(candidates))
        ]
        reranked.extend(result)
        return result

    p.reranker = MagicMock()
    p.reranker.rerank_multi = MagicMock(side_effect=fake_rerank)

    results = await p.search("Thus have I heard", top_k=10)

    assert "rerank_score" in results[0]
    assert [r["id"] for r in results] == [r["id"] for r in reranked]
