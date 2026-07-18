"""
Tests for SuttaTitleIndex integration in SearchPipeline.

Scenario: A query like "four foundations of mindfulness" is semantically diffuse —
many suttas score similarly on embeddings. The title index should force MN10 verses
into the candidate pool so the reranker can promote them.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.sutta_title_index import SuttaTitleIndex
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models


MINDFULNESS_CHUNKS = [
    # MN10 canonical source
    {"id": "MN10:9", "english": "The four kinds of mindfulness meditation are the path."},
    {"id": "MN10:11", "english": "A mendicant meditates observing an aspect of the body."},
    # Generic mentions scattered across other suttas
    {"id": "AN3.16:2", "english": "One should practice mindfulness and clear comprehension."},
    {"id": "SN47.1:3", "english": "The cultivation of the establishments of mindfulness."},
    {"id": "DN2:45", "english": "Mindful and clearly comprehending."},
]

TITLE_ENTRIES = [
    {"sutta_id": "MN10", "title_pali": "Satipaṭṭhānasutta", "title_english": "Mindfulness Meditation"},
    {"sutta_id": "AN3.16", "title_pali": "Acelakasutta", "title_english": "Naked Ascetics"},
    {"sutta_id": "SN47.1", "title_pali": "Ambapālīsutta", "title_english": "With Ambapālī"},
    {"sutta_id": "DN2", "title_pali": "Sāmaññaphalasutta", "title_english": "The Fruits of the Ascetic Life"},
    {"sutta_id": "MN26", "title_pali": "Ariyapariyesanāsutta", "title_english": "The Noble Search"},
]


async def _make_pipeline(chunks, title_entries=None):
    client = AsyncQdrantClient(":memory:")
    title_index = SuttaTitleIndex(title_entries) if title_entries else None
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline(title_index=title_index)
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
                vector=pipeline.retriever.embedding_mgr.encode(c['english']),
                payload=c,
            )
            for idx, c in enumerate(chunks)
        ]
        await client.upsert(collection_name=collection_name, points=points)
    return pipeline


@pytest.mark.asyncio
async def test_pipeline_accepts_title_index_parameter():
    title_index = SuttaTitleIndex(TITLE_ENTRIES)
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline(title_index=title_index)
    assert pipeline.title_index is title_index


@pytest.mark.asyncio
async def test_pipeline_without_title_index_is_unchanged():
    """No title_index → pipeline behaves exactly as before."""
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.title_index is None


@pytest.mark.asyncio
async def test_title_boost_forces_canonical_sutta_into_results():
    """
    With title_index, a query matching MN10's title forces MN10 verses into
    the candidate pool even when semantic scores are similar across suttas.
    """
    pipeline = await _make_pipeline(MINDFULNESS_CHUNKS, title_entries=TITLE_ENTRIES)
    results = await pipeline.search("four foundations of mindfulness", top_k=5)
    result_ids = [r["id"] for r in results]
    mn10_ids = [rid for rid in result_ids if rid.startswith("MN10")]
    assert len(mn10_ids) >= 1, f"Expected MN10 in results, got: {result_ids}"


@pytest.mark.asyncio
async def test_title_boost_does_not_duplicate_chunks():
    """Chunks boosted via title should not appear twice in final results."""
    pipeline = await _make_pipeline(MINDFULNESS_CHUNKS, title_entries=TITLE_ENTRIES)
    results = await pipeline.search("four foundations of mindfulness", top_k=5)
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids)), f"Duplicate IDs in results: {ids}"


@pytest.mark.asyncio
async def test_no_title_match_returns_normal_results():
    """Query with no title match still returns results (fallback to vector search)."""
    pipeline = await _make_pipeline(MINDFULNESS_CHUNKS, title_entries=TITLE_ENTRIES)
    results = await pipeline.search("fruits of the ascetic life sāmaññaphala", top_k=3)
    assert len(results) > 0
