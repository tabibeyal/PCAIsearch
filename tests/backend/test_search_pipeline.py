import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.search_pipeline import SearchPipeline, ExpansionPrompt
from backend.app.services.bm25_retriever import BM25Retriever
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


@pytest.mark.asyncio
async def test_search_with_bm25_surfaces_exact_match():
    """BM25 path surfaces a passage whose exact words match the query."""
    chunks = [
        {"id": "SN 56.11:1", "pali": "", "english": "noble eightfold path right view intention speech"},
        {"id": "DN 1:1", "pali": "evam", "english": "Thus have I heard at one time"},
        {"id": "MN 10:1", "pali": "citta", "english": "mindfulness contemplating body feelings mind"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("noble eightfold path", top_k=3)
    ids = [r["id"] for r in results]
    assert "SN 56.11:1" in ids


@pytest.mark.asyncio
async def test_nikaya_filter_excludes_other_nikayas_from_final_results():
    """nikayas=["MN"] must exclude non-MN verses even after BM25+RRF fusion."""
    chunks = [
        {"id": "MN 10:1", "nikaya": "MN", "pali": "citta", "english": "right mindfulness body"},
        {"id": "MN 10:2", "nikaya": "MN", "pali": "vedana", "english": "right mindfulness feelings"},
        {"id": "DN 1:1", "nikaya": "DN", "pali": "evam", "english": "right view thus heard"},
        {"id": "SN 22.59:1", "nikaya": "SN", "pali": "rupam", "english": "right mindfulness impermanent form"},
    ]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.bm25_retriever = BM25Retriever(chunks)

    results = await pipeline.search("right mindfulness", top_k=5, nikayas=["MN"])
    non_mn = [r for r in results if not r["id"].startswith("MN ")]
    assert not non_mn, f"Non-MN results leaked through: {non_mn}"


@pytest.mark.asyncio
async def test_bm25_runs_on_all_expanded_queries():
    """BM25 must be called for every expanded query variant, not just the original."""
    from unittest.mock import MagicMock
    chunks = [{"id": "MN 10:1", "pali": "", "english": "foundations of mindfulness"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)

    mock_bm25 = MagicMock()
    mock_bm25.retrieve.return_value = []
    pipeline.bm25_retriever = mock_bm25
    pipeline.expand_query = AsyncMock(return_value=["original query", "satipatthana meditation"])

    await pipeline.search("original query", top_k=5)

    called_queries = [call.args[0] for call in mock_bm25.retrieve.call_args_list]
    assert "satipatthana meditation" in called_queries, (
        f"BM25 must be called with expanded variant; got calls: {called_queries}"
    )


def test_search_pipeline_constructor_accepts_bm25_retriever():
    verses = [{"id": "MN 1:1", "pali": "", "english": "test verse"}]
    bm25 = BM25Retriever(verses)
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline(bm25_retriever=bm25)
    assert pipeline.bm25_retriever is bm25


@pytest.mark.asyncio
async def test_dense_results_use_rrf_fuse_multi_not_first_seen():
    """Pipeline must call rrf_fuse_multi on per-query dense results, not first-seen dedup."""
    chunks = [{"id": "MN 10:1", "pali": "", "english": "mindfulness body"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.expand_query = AsyncMock(return_value=["query one", "query two"])

    with patch("backend.app.services.search_pipeline.rrf_fuse_multi") as mock_multi:
        mock_multi.return_value = []
        await pipeline.search("mindfulness", top_k=5)

    mock_multi.assert_called_once()
    call_arg = mock_multi.call_args[0][0]
    assert isinstance(call_arg, list), "rrf_fuse_multi must receive a list of lists"
    assert len(call_arg) == 2, f"Expected 2 per-query result lists, got {len(call_arg)}"


def test_expansion_prompt_v2_exists():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_expansion_prompt_v2_has_two_line_structure():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Line 1" in prompt
    assert "Line 2" in prompt


def test_expansion_prompt_v2_mentions_pali_terms():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Pali" in prompt or "Pāli" in prompt or "Pāḷi" in prompt


def test_expansion_prompt_v2_forbids_sutta_numbers():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "sutta number" in prompt.lower() or "sutta numbers" in prompt.lower()


def test_search_pipeline_default_uses_v2():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt.version == "v2"
