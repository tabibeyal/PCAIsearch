import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


@pytest.fixture
def pipeline():
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient"), \
         patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        from backend.app.services.search_pipeline import SearchPipeline
        return SearchPipeline()


def _mock_llm(pipeline, reply: str) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = reply
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    pipeline.llm = mock_client
    return mock_client


# --- expand_query unit tests ---

@pytest.mark.asyncio
async def test_expand_query_includes_original(pipeline):
    _mock_llm(pipeline, "sati awareness\nright mindfulness eightfold path")
    variants = await pipeline.expand_query("What is mindfulness?")
    assert "What is mindfulness?" in variants


@pytest.mark.asyncio
async def test_expand_query_calls_llm_once(pipeline):
    mock_client = _mock_llm(pipeline, "sati awareness")
    await pipeline.expand_query("mindfulness")
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_expand_query_uses_expansion_model_not_llm_model(pipeline):
    """expand_query must use expansion_model, not llm_model."""
    mock_client = _mock_llm(pipeline, "sati awareness")
    pipeline.expansion_model = "google/gemma-3n-e4b-it"
    pipeline.llm_model = "meta/llama-3.3-70b-instruct"
    await pipeline.expand_query("mindfulness")
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "google/gemma-3n-e4b-it"


@pytest.mark.asyncio
async def test_synthesize_uses_llm_model_not_expansion_model(pipeline):
    """synthesize must use llm_model, not expansion_model."""
    mock_client = _mock_llm(pipeline, "The answer is impermanence.")
    pipeline.expansion_model = "google/gemma-3n-e4b-it"
    pipeline.llm_model = "meta/llama-3.3-70b-instruct"
    await pipeline.synthesize("what is anicca?", [{"id": "SN1:1", "pali": "anicca", "english": "impermanence"}])
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "meta/llama-3.3-70b-instruct"


@pytest.mark.asyncio
async def test_expand_query_parses_llm_lines_as_variants(pipeline):
    # Original query + 2 variants = 3 total (capped at 3)
    _mock_llm(pipeline, "sati awareness\nright mindfulness eightfold path\nkāyagatāsati body mindfulness")
    variants = await pipeline.expand_query("mindfulness")
    assert len(variants) == 3
    assert any("sati" in v for v in variants)
    assert any("eightfold" in v for v in variants)
    assert not any("kāyagatāsati" in v for v in variants)


@pytest.mark.asyncio
async def test_expand_query_deduplicates_if_llm_echoes_original(pipeline):
    _mock_llm(pipeline, "mindfulness\nsati awareness")
    variants = await pipeline.expand_query("mindfulness")
    assert variants.count("mindfulness") == 1


@pytest.mark.asyncio
async def test_expand_query_returns_at_least_two_variants(pipeline):
    _mock_llm(pipeline, "sati meditation\nright mindfulness")
    variants = await pipeline.expand_query("mindfulness")
    assert len(variants) >= 2


@pytest.mark.asyncio
async def test_expand_query_strictly_limits_to_three_variants(pipeline):
    _mock_llm(pipeline, "v1\nv2\nv3\nv4\nv5")
    variants = await pipeline.expand_query("mindfulness")
    assert len(variants) <= 3, "Query expansion must be capped at 3 variants"


@pytest.fixture
def in_memory_pipeline():
    """Pipeline wired to an in-memory Qdrant for retrieval integration tests."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        from backend.app.services.search_pipeline import SearchPipeline
        p = SearchPipeline()
    client = AsyncQdrantClient(":memory:")
    p.retriever.client = client

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
async def test_search_calls_expand_query(in_memory_pipeline):
    in_memory_pipeline.expand_query = AsyncMock(return_value=["mindfulness"])
    await in_memory_pipeline.search("mindfulness", top_k=5)
    in_memory_pipeline.expand_query.assert_called_once_with("mindfulness")


@pytest.mark.asyncio
async def test_search_deduplicates_results_across_variants(in_memory_pipeline):
    """Results retrieved by multiple variants should not contain duplicates."""
    p = in_memory_pipeline

    text = "sammā-sati right mindfulness"
    vector = p.retriever.embedding_mgr.encode(text)
    await p.retriever.client.upsert(
        collection_name=p.collection_name,
        points=[models.PointStruct(id=0, vector=vector, payload={
            "id": "MN 10:1", "pali": "sammā-sati", "english": "Right Mindfulness"
        })]
    )

    p.expand_query = AsyncMock(return_value=["right mindfulness", "sammā-sati meditation"])
    results = await p.search("mindfulness", top_k=10)

    in_memory_pipeline.expand_query.assert_called_once_with("mindfulness")
    ids = [r["id"] for r in results]
    assert ids.count("MN 10:1") == 1, "Same chunk must not appear twice"
