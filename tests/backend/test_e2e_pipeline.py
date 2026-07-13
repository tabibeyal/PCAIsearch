"""
End-to-end pipeline tests.

Real components: embedding model, cross-encoder reranker, in-memory Qdrant, CitationGuardrail.
Mocked: LLM (expand_query + synthesize) — tested in isolation elsewhere.
"""
import asyncio
import json
import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.sutta_title_index import SuttaTitleIndex

# ---------------------------------------------------------------------------
# Corpus — distinct enough that the reranker reliably distinguishes them
# ---------------------------------------------------------------------------
CORPUS = [
    {"id": "DN 1:1",  "pali": "evam me sutaṃ",  "english": "Thus have I heard"},
    {"id": "MN 10:1", "pali": "sammā-sati",      "english": "Right Mindfulness of breathing"},
    {"id": "SN 5:10", "pali": "dukkha",           "english": "The truth of suffering and its cessation"},
    # Translator commentary on mettā/kindness — the answer flow must exclude this
    # at retrieval time while plain /search still returns it (#102).
    {
        "id": "AN 4:1",
        "pali": "",
        "english": "The translator notes that metta means kindness or goodwill throughout this discourse",
        "section": "commentary",
    },
]


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def live_pipeline():
    """Pipeline with real models + in-memory Qdrant; LLM mocked."""
    mp = pytest.MonkeyPatch()
    mp.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    from backend.app.services.search_pipeline import SearchPipeline
    p = SearchPipeline()
    client = AsyncQdrantClient(":memory:")
    p.retriever.client = client

    async def _setup():
        await client.create_collection(
            collection_name=p.collection_name,
            vectors_config=qmodels.VectorParams(
                size=p.retriever.embedding_mgr.dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )
        for idx, chunk in enumerate(CORPUS):
            vector = p.retriever.embedding_mgr.encode(f"{chunk['pali']} {chunk['english']}")
            await client.upsert(
                collection_name=p.collection_name,
                points=[qmodels.PointStruct(id=idx, vector=vector, payload=chunk)],
            )

    asyncio.run(_setup())
    p.expand_query = AsyncMock(side_effect=lambda q, **_: [q])
    p.title_index = SuttaTitleIndex([
        {"sutta_id": "MN10", "title_pali": "Satipaṭṭhānasutta", "title_english": "Mindfulness Meditation"},
    ])
    yield p
    mp.undo()


def _mock_synthesis(pipeline, text: str) -> None:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = text
    pipeline.llm.chat.completions.create = AsyncMock(return_value=resp)


def _mock_stream_synthesis(pipeline, text: str) -> None:
    async def _stream():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = text
        yield chunk

    pipeline.llm.chat.completions.create = AsyncMock(return_value=_stream())


def _stream_done_event(response) -> dict:
    events = [
        json.loads(line[len("data: "):])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    return next(e for e in events if e["type"] == "done")


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
    """The chunk IDs from search appear in the user message sent to the LLM."""
    context = await live_pipeline.search("mindfulness", top_k=3)
    context_ids = {c["id"] for c in context}

    _mock_synthesis(live_pipeline, f"See [{context[0]['id']}] for details.")
    await live_pipeline.synthesize("mindfulness", context)

    messages = live_pipeline.llm.chat.completions.create.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    for cid in context_ids:
        assert cid in user_content, f"Context ID {cid!r} missing from LLM prompt"


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

    # DN 99:99 does not exist — without a CitationOracle this is a hallucination.
    result = CitationGuardrail().process_response(answer, context)
    assert result["is_faithful"] is False
    assert "DN 99:99" in result["hallucinations"]
    assert "[DN 99:99]" not in result["text"]
    assert "[Hallucinated]" in result["text"]


# ---------------------------------------------------------------------------
# API endpoint e2e tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_client(live_pipeline):
    from backend.app.main import app
    # Rate limiting is a production concern, not behaviour under test here;
    # the module issues >10 /synthesize calls, which would otherwise trip the
    # 10/minute limiter mid-suite. Disabled for the fixture's lifetime only.
    limiter = app.state.limiter
    limiter.enabled = False
    try:
        with patch("backend.app.main.SearchPipeline", return_value=live_pipeline):
            with TestClient(app) as c:
                # AnswerComposer takes title_index as its own direct dependency
                # (not reached through pipeline), so the fixture's title_index
                # must be pushed onto the composer too.
                app.state.composer.title_index = live_pipeline.title_index
                yield c
    finally:
        limiter.enabled = True


def test_e2e_api_search_returns_reranked_results(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) > 0
    assert all("rerank_score" in r for r in body["results"])


def test_e2e_api_search_top_result_is_most_relevant(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    assert response.json()["results"][0]["id"] == "MN 10:1"


def test_e2e_api_search_results_include_sutta_title(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert results_by_id["MN 10:1"]["title"] == "Satipaṭṭhānasutta Mindfulness Meditation"


def test_e2e_api_search_results_include_title_pali(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert results_by_id["MN 10:1"]["title_pali"] == "Satipaṭṭhānasutta"


def test_e2e_api_search_results_include_title_english(api_client):
    response = api_client.get("/search?q=mindfulness+breathing")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert results_by_id["MN 10:1"]["title_english"] == "Mindfulness Meditation"


def test_e2e_api_search_omits_title_fields_when_not_in_index(api_client):
    response = api_client.get("/search?q=teachings")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert "title_pali" not in results_by_id["DN 1:1"]
    assert "title_english" not in results_by_id["DN 1:1"]


def test_e2e_api_synthesize_faithful_answer(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    assert response.status_code == 200
    body = response.json()
    assert body["is_faithful"] is True
    assert "[MN 10:1]" in body["answer"]
    assert body["hallucinations"] == []
    assert len(body["context"]) > 0


def test_e2e_api_synthesize_context_includes_sutta_title(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    body = response.json()
    context_by_id = {c["id"]: c for c in body["context"]}
    assert context_by_id["MN 10:1"]["title"] == "Satipaṭṭhānasutta Mindfulness Meditation"


def test_e2e_api_synthesize_context_includes_title_pali(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    body = response.json()
    context_by_id = {c["id"]: c for c in body["context"]}
    assert context_by_id["MN 10:1"]["title_pali"] == "Satipaṭṭhānasutta"


def test_e2e_api_synthesize_context_includes_title_english(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    body = response.json()
    context_by_id = {c["id"]: c for c in body["context"]}
    assert context_by_id["MN 10:1"]["title_english"] == "Mindfulness Meditation"


def test_e2e_api_synthesize_context_omits_title_pali_when_not_in_index(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "See [MN 10:1].")
    response = api_client.get("/synthesize?q=teachings")
    body = response.json()
    context_by_id = {c["id"]: c for c in body["context"]}
    assert "title_pali" not in context_by_id["DN 1:1"]


def test_e2e_api_synthesize_context_omits_title_english_when_not_in_index(api_client, live_pipeline):
    _mock_synthesis(live_pipeline, "See [MN 10:1].")
    response = api_client.get("/synthesize?q=teachings")
    body = response.json()
    context_by_id = {c["id"]: c for c in body["context"]}
    assert "title_english" not in context_by_id["DN 1:1"]


def test_e2e_api_search_still_returns_commentary_chunk(api_client):
    """Plain /search is unchanged by #102: commentary chunks still surface."""
    response = api_client.get("/search?q=kindness+goodwill+metta")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert "AN 4:1" in results_by_id


def test_e2e_api_search_preserves_commentary_marker(api_client):
    """The commentary chunk that plain /search returns keeps its section marker
    so the frontend can label it (#101, unchanged by #102)."""
    response = api_client.get("/search?q=kindness+goodwill+metta")
    results_by_id = {r["id"]: r for r in response.json()["results"]}
    assert results_by_id["AN 4:1"]["section"] == "commentary"


def test_e2e_api_synthesize_excludes_commentary_from_context(api_client, live_pipeline):
    """The answer flow excludes commentary at retrieval time, so the context
    fed to the LLM and returned to the sources pane is canon-only (#102)."""
    _mock_synthesis(live_pipeline, "Kindness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=kindness+goodwill+metta")
    context_ids = {c["id"] for c in response.json()["context"]}
    assert "AN 4:1" not in context_ids


def test_e2e_api_synthesize_keeps_canon_in_context(api_client, live_pipeline):
    """Excluding commentary does not empty the answer-flow context — canon
    passages still fill the slots (#102)."""
    _mock_synthesis(live_pipeline, "Kindness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=kindness+goodwill+metta")
    context_ids = {c["id"] for c in response.json()["context"]}
    assert "MN 10:1" in context_ids


def test_e2e_api_stream_excludes_commentary_from_done_context(api_client, live_pipeline):
    """The streaming answer flow excludes commentary too — the done event's
    context is canon-only (#102)."""
    _mock_stream_synthesis(live_pipeline, "Kindness is in [MN 10:1].")
    response = api_client.get("/stream?q=kindness+goodwill+metta")
    done_event = _stream_done_event(response)
    context_ids = {c["id"] for c in done_event["context"]}
    assert "AN 4:1" not in context_ids


def test_e2e_api_stream_keeps_canon_in_done_context(api_client, live_pipeline):
    """The streaming answer flow still returns canon passages after commentary
    is excluded (#102)."""
    _mock_stream_synthesis(live_pipeline, "Kindness is in [MN 10:1].")
    response = api_client.get("/stream?q=kindness+goodwill+metta")
    done_event = _stream_done_event(response)
    context_ids = {c["id"] for c in done_event["context"]}
    assert "MN 10:1" in context_ids


def test_e2e_api_synthesize_includes_verifiable_receipt(api_client, live_pipeline, monkeypatch):
    from backend.app.main import app
    from backend.app.services.share_receipt import verify_receipt

    # AnswerComposer captures the receipt secret as its own constructor
    # dependency, not a live module-global lookup, so it must be patched on
    # the composer instance directly.
    monkeypatch.setattr(app.state.composer, "receipt_secret", "fake-signing-value-for-tests")
    _mock_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/synthesize?q=mindfulness")
    body = response.json()
    assert verify_receipt(
        body["query"], body["answer"], body["context"], body["receipt"], "fake-signing-value-for-tests"
    )


def test_e2e_api_stream_includes_verifiable_receipt(api_client, live_pipeline, monkeypatch):
    from backend.app.main import app
    from backend.app.services.share_receipt import verify_receipt

    # AnswerComposer captures the receipt secret as its own constructor
    # dependency, not a live module-global lookup, so it must be patched on
    # the composer instance directly.
    monkeypatch.setattr(app.state.composer, "receipt_secret", "fake-signing-value-for-tests")
    _mock_stream_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/stream?q=mindfulness")
    events = [
        json.loads(line[len("data: "):])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    done_event = next(e for e in events if e["type"] == "done")
    assert verify_receipt(
        done_event["query"],
        done_event["answer"],
        done_event["context"],
        done_event["receipt"],
        "fake-signing-value-for-tests",
    )


def test_e2e_api_stream_context_includes_title_pali(api_client, live_pipeline):
    _mock_stream_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/stream?q=mindfulness")
    events = [
        json.loads(line[len("data: "):])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    done_event = next(e for e in events if e["type"] == "done")
    context_by_id = {c["id"]: c for c in done_event["context"]}
    assert context_by_id["MN 10:1"]["title_pali"] == "Satipaṭṭhānasutta"


def test_e2e_api_stream_context_includes_title_english(api_client, live_pipeline):
    _mock_stream_synthesis(live_pipeline, "Mindfulness is in [MN 10:1].")
    response = api_client.get("/stream?q=mindfulness")
    events = [
        json.loads(line[len("data: "):])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    done_event = next(e for e in events if e["type"] == "done")
    context_by_id = {c["id"]: c for c in done_event["context"]}
    assert context_by_id["MN 10:1"]["title_english"] == "Mindfulness Meditation"


def test_e2e_api_synthesize_hallucination_flagged(api_client, live_pipeline):
    # DN 99:99 doesn't exist in the canon — the canon-aware guardrail flags it as hallucinated.
    _mock_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/synthesize?q=mindfulness")
    assert response.status_code == 200
    body = response.json()
    assert body["is_faithful"] is False
    assert "DN 99:99" in body["hallucinations"]
    assert "[DN 99:99]" not in body["answer"]
    assert "[Hallucinated]" in body["answer"]


def test_e2e_api_stream_hallucination_marks_is_faithful_false(api_client, live_pipeline):
    # /stream runs the same Guardrail finalize step as /synthesize; DN 99:99
    # doesn't exist in the canon, so the done event must flag it.
    _mock_stream_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/stream?q=mindfulness")
    done_event = _stream_done_event(response)
    assert done_event["is_faithful"] is False


def test_e2e_api_stream_hallucination_includes_hallucinated_id(api_client, live_pipeline):
    _mock_stream_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/stream?q=mindfulness")
    done_event = _stream_done_event(response)
    assert "DN 99:99" in done_event["hallucinations"]


def test_e2e_api_stream_hallucination_strips_raw_citation(api_client, live_pipeline):
    _mock_stream_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/stream?q=mindfulness")
    done_event = _stream_done_event(response)
    assert "[DN 99:99]" not in done_event["answer"]


def test_e2e_api_stream_hallucination_includes_marker(api_client, live_pipeline):
    _mock_stream_synthesis(live_pipeline, "See [MN 10:1] and [DN 99:99].")
    response = api_client.get("/stream?q=mindfulness")
    done_event = _stream_done_event(response)
    assert "[Hallucinated]" in done_event["answer"]


# ---------------------------------------------------------------------------
# top_k parameter tests
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

    messages = live_pipeline.llm.chat.completions.create.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in messages if m["role"] == "user")
    ids_in_prompt = re.findall(r"\[([A-Z\s]+\d+:\d+)\]", user_content)
    assert len(ids_in_prompt) == 1
