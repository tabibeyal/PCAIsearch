import json

import pytest

from backend.app.services.answer_composer import AnswerComposer
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.share_receipt import verify_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex

from fakes import FakePipeline, MidStreamRaisingFakePipeline, RaisingFakePipeline

RECEIPT_KEY = "fake-signing-value-for-tests"


def _raw_context():
    # Fresh dicts per call: _attach_titles/_attach_passages mutate chunks in
    # place, so a shared module-level list would couple tests to each other.
    return [
        {"id": "MN 10:1", "english": "Right mindfulness is awareness of the present moment"},
        {"id": "DN 1:1", "english": "Too short"},
    ]


def _composer(context=None, answer="The teaching is in [MN 10:1].", guardrail=None):
    pipeline = FakePipeline(_raw_context() if context is None else context, answer)
    composer = AnswerComposer(
        pipeline=pipeline,
        guardrail=guardrail if guardrail is not None else CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
    )
    return composer, pipeline


@pytest.mark.asyncio
async def test_answer_returns_expected_shape():
    composer, _ = _composer()
    result = await composer.answer("mindfulness", top_k=10)
    assert set(result) == {
        "query", "answer", "hallucinations", "canonical_misses", "is_faithful", "context", "receipt",
    }


@pytest.mark.asyncio
async def test_answer_drops_short_chunk_from_returned_context():
    composer, _ = _composer()
    result = await composer.answer("mindfulness", top_k=10)
    assert [c["id"] for c in result["context"]] == ["MN 10:1"]


@pytest.mark.asyncio
async def test_answer_receipt_verifies_against_returned_context():
    composer, _ = _composer()
    result = await composer.answer("mindfulness", top_k=10)
    assert verify_receipt(result["query"], result["answer"], result["context"], result["receipt"], RECEIPT_KEY)


@pytest.mark.asyncio
async def test_answer_forwards_nikayas_to_pipeline_search():
    composer, pipeline = _composer()
    await composer.answer("mindfulness", top_k=10, nikayas=["MN", "SN"])
    assert pipeline.search_calls[0]["nikayas"] == ["MN", "SN"]


@pytest.mark.asyncio
async def test_answer_requests_global_best_policy():
    composer, pipeline = _composer()
    await composer.answer("mindfulness", top_k=10)
    assert pipeline.search_calls[0]["policy"] == "global_best"


@pytest.mark.asyncio
async def test_answer_requests_canon_only_context():
    composer, pipeline = _composer()
    await composer.answer("mindfulness", top_k=10)
    assert pipeline.search_calls[0]["exclude_commentary"] is True


@pytest.mark.asyncio
async def test_answer_context_is_exactly_what_llm_saw():
    composer, pipeline = _composer()
    result = await composer.answer("mindfulness", top_k=10)
    assert [c["id"] for c in result["context"]] == [c["id"] for c in pipeline.synthesize_contexts[0]]


@pytest.mark.asyncio
async def test_answer_marks_real_but_unretrieved_citation_unverified(tmp_path):
    (tmp_path / "sn45.json").write_text(
        json.dumps({"sutta_id": "SN45", "verses": [{"number": 8}]}), encoding="utf-8"
    )
    guardrail = CitationGuardrail(oracle=CitationOracle(tmp_path))
    composer, _ = _composer(answer="Also see [SN 45:8].", guardrail=guardrail)
    result = await composer.answer("mindfulness", top_k=10)
    assert "[Unverified]" in result["answer"]


@pytest.mark.asyncio
async def test_answer_marks_citation_to_nonexistent_sutta_as_not_faithful():
    composer, _ = _composer(answer="Also see [DN 99:99].")
    result = await composer.answer("mindfulness", top_k=10)
    assert result["is_faithful"] is False


@pytest.mark.asyncio
async def test_answer_marks_citation_to_nonexistent_sutta_hallucinated():
    composer, _ = _composer(answer="Also see [DN 99:99].")
    result = await composer.answer("mindfulness", top_k=10)
    assert "[Hallucinated]" in result["answer"]


@pytest.mark.asyncio
async def test_answer_propagates_pipeline_failure():
    composer = AnswerComposer(
        pipeline=RaisingFakePipeline(),
        guardrail=CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
    )
    with pytest.raises(RuntimeError, match="search failed"):
        await composer.answer("mindfulness", top_k=10)


async def _collect(agen):
    return [event async for event in agen]


@pytest.mark.asyncio
async def test_answer_stream_yields_events_in_order():
    composer, _ = _composer(answer="hi")
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    types = [e["type"] for e in events]
    assert types == ["status", "status", "chunk", "status", "done"]


@pytest.mark.asyncio
async def test_answer_stream_done_payload_matches_answer_shape():
    composer, _ = _composer()
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    done = events[-1]
    assert set(done) - {"type"} == {
        "query", "answer", "hallucinations", "canonical_misses", "is_faithful", "context", "receipt",
    }


@pytest.mark.asyncio
async def test_answer_stream_done_matches_answer_for_same_inputs():
    composer, _ = _composer()
    stream_events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    done = stream_events[-1]
    direct = await composer.answer("mindfulness", top_k=10)
    assert {k: v for k, v in done.items() if k != "type"} == direct


@pytest.mark.asyncio
async def test_answer_stream_forwards_nikayas_to_pipeline_search():
    composer, pipeline = _composer()
    await _collect(composer.answer_stream("mindfulness", top_k=10, nikayas=["MN", "SN"]))
    assert pipeline.search_calls[0]["nikayas"] == ["MN", "SN"]


@pytest.mark.asyncio
async def test_answer_stream_requests_global_best_policy():
    composer, pipeline = _composer()
    await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert pipeline.search_calls[0]["policy"] == "global_best"


@pytest.mark.asyncio
async def test_answer_stream_requests_canon_only_context():
    composer, pipeline = _composer()
    await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert pipeline.search_calls[0]["exclude_commentary"] is True


@pytest.mark.asyncio
async def test_answer_stream_drops_short_chunk_from_done_context():
    composer, _ = _composer()
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert [c["id"] for c in events[-1]["context"]] == ["MN 10:1"]


@pytest.mark.asyncio
async def test_answer_stream_marks_citation_to_nonexistent_sutta_as_not_faithful():
    composer, _ = _composer(answer="Also see [DN 99:99].")
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert events[-1]["is_faithful"] is False


@pytest.mark.asyncio
async def test_answer_stream_marks_citation_to_nonexistent_sutta_hallucinated():
    composer, _ = _composer(answer="Also see [DN 99:99].")
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert "[Hallucinated]" in events[-1]["answer"]


@pytest.mark.asyncio
async def test_answer_stream_propagates_pipeline_search_failure():
    composer = AnswerComposer(
        pipeline=RaisingFakePipeline(),
        guardrail=CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
    )
    with pytest.raises(RuntimeError, match="search failed"):
        await _collect(composer.answer_stream("mindfulness", top_k=10))


@pytest.mark.asyncio
async def test_answer_stream_propagates_mid_generator_failure():
    composer = AnswerComposer(
        pipeline=MidStreamRaisingFakePipeline(_raw_context()),
        guardrail=CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
    )
    with pytest.raises(RuntimeError, match="synthesis failed"):
        await _collect(composer.answer_stream("mindfulness", top_k=10))
