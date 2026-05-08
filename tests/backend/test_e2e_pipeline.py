"""
End-to-end pipeline tests.

Real components: embedding model, cross-encoder reranker, in-memory Qdrant, CitationGuardrail.
Mocked: LLM (expand_query + synthesize) — tested in isolation elsewhere.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from backend.app.services.guardrail import CitationGuardrail

# ---------------------------------------------------------------------------
# Corpus — distinct enough that the reranker reliably distinguishes them
# ---------------------------------------------------------------------------
CORPUS = [
    {"id": "DN 1:1",  "pali": "evam me sutaṃ",  "english": "Thus have I heard"},
    {"id": "MN 10:1", "pali": "sammā-sati",      "english": "Right Mindfulness of breathing"},
    {"id": "SN 5:10", "pali": "dukkha",           "english": "The truth of suffering and its cessation"},
]


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def live_pipeline():
    """Pipeline with real models + in-memory Qdrant; LLM mocked."""
    from backend.app.services.search_pipeline import SearchPipeline
    p = SearchPipeline()
    client = AsyncQdrantClient(":memory:")
    p.client = client

    async def _setup():
        await client.create_collection(
            collection_name=p.collection_name,
            vectors_config=qmodels.VectorParams(
                size=p.embedding_mgr.dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )
        for idx, chunk in enumerate(CORPUS):
            vector = p.embedding_mgr.encode(f"{chunk['pali']} {chunk['english']}")
            await client.upsert(
                collection_name=p.collection_name,
                points=[qmodels.PointStruct(id=idx, vector=vector, payload=chunk)],
            )

    asyncio.run(_setup())
    p.expand_query = AsyncMock(side_effect=lambda q, **_: [q])
    return p


def _mock_synthesis(pipeline, text: str) -> None:
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    pipeline.llm.messages.create = AsyncMock(return_value=resp)


# ---------------------------------------------------------------------------
# Pipeline-level e2e tests (no HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_search_all_chunks_returned_with_rerank_score(live_pipeline):
    results = await live_pipeline.search("mindfulness breathing", top_k=10)
    assert len(results) == len(CORPUS)
    assert all("rerank_score" in r for r in results)


@pytest.mark.asyncio
async def test_e2e_reranker_places_mindfulness_chunk_first(live_pipeline):
    results = await live_pipeline.search("mindfulness breathing", top_k=3)
    assert results[0]["id"] == "MN 10:1"


@pytest.mark.asyncio
async def test_e2e_rerank_scores_are_descending(live_pipeline):
    results = await live_pipeline.search("suffering cessation", top_k=3)
    scores = [r["rerank_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_e2e_synthesis_receives_retrieved_context(live_pipeline):
    """The chunk IDs from search appear in the prompt sent to the LLM."""
    context = await live_pipeline.search("mindfulness", top_k=3)
    context_ids = {c["id"] for c in context}

    _mock_synthesis(live_pipeline, f"See [{context[0]['id']}] for details.")
    await live_pipeline.synthesize("mindfulness", context)

    call_content = live_pipeline.llm.messages.create.call_args.kwargs["messages"][0]["content"]
    for cid in context_ids:
        assert cid in call_content, f"Context ID {cid!r} missing from LLM prompt"


@pytest.mark.asyncio
async def test_e2e_guardrail_passes_for_faithful_citation(live_pipeline):
    context = await live_pipeline.search("mindfulness", top_k=3)
    top_id = context[0]["id"]

    _mock_synthesis(live_pipeline, f"The teaching is in [{top_id}].")
    answer = await live_pipeline.synthesize("mindfulness", context)

    result = CitationGuardrail().process_response(answer, context)
    assert result["is_faithful"] is True
    assert f"[{top_id}]" in result["text"]


@pytest.mark.asyncio
async def test_e2e_guardrail_catches_hallucinated_citation(live_pipeline):
    context = await live_pipeline.search("mindfulness", top_k=3)

    _mock_synthesis(live_pipeline, "See [MN 10:1] and also [DN 99:99].")
    answer = await live_pipeline.synthesize("mindfulness", context)

    result = CitationGuardrail().process_response(answer, context)
    assert result["is_faithful"] is False
    assert "DN 99:99" in result["hallucinations"]
    assert "[DN 99:99]" not in result["text"]
    assert "[Unverified]" in result["text"]


# ---------------------------------------------------------------------------
# API endpoint e2e tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_client(live_pipeline):
    from backend.app.main import app
    with patch("backend.app.main.SearchPipeline", return_value=live_pipeline):
        with TestClient(app) as c:
            yield c


def test_e2e_api_search_returns_reranked_results(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) > 0
    assert all("rerank_score" in r for r in body["results"])


def test_e2e_api_search_top_result_is_most_relevant(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    assert response.json()["results"][0]["id"] == "MN 10:1"


def test_e2e_api_synthesize_faithful_answer(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    assert response.status_code == 200
    body = response.json()
    assert body["is_faithful"] is True
    assert "[MN 10:1]" in body["answer"]
    assert body["hallucinations"] == []
    assert len(body["context"]) > 0


def test_e2e_api_synthesize_hallucination_flagged(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/synthesize?q=mindfulness")
    assert response.status_code == 200
    body = response.json()
    assert body["is_faithful"] is False
    assert "DN 99:99" in body["hallucinations"]
    assert "[DN 99:99]" not in body["answer"]
    assert "[Unverified]" in body["answer"]


# ---------------------------------------------------------------------------
# top_k parameter — not yet exposed on the API
# ---------------------------------------------------------------------------

def test_e2e_api_search_top_k_limits_results(api_client):
    """Corpus has 3 chunks; top_k=1 must return at most 1."""
    response = api_client.get("/search?q=teachings&top_k=1")
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 1


def test_e2e_api_search_top_k_default_is_ten(api_client):
    """No top_k param → endpoint uses the default of 10 (returns all 3 in our corpus)."""
    response = api_client.get("/search?q=teachings")
    assert response.status_code == 200
    assert len(response.json()["results"]) == len(CORPUS)


def test_e2e_api_synthesize_top_k_limits_context(api_client, live_pipeline):
    """top_k=1 → only 1 chunk is passed as context to the LLM."""
    _mock_synthesis(live_pipeline, "Answer.")
    api_client.get("/synthesize?q=mindfulness&top_k=1")

    call_content = live_pipeline.llm.messages.create.call_args.kwargs["messages"][0]["content"]
    # Only one [ID:Verse] block should appear in the context section
    import re
    ids_in_prompt = re.findall(r"\[([A-Z\s]+\d+:\d+)\]", call_content)
    assert len(ids_in_prompt) == 1
