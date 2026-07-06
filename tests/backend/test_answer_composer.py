import pytest

from backend.app.services.answer_composer import AnswerComposer
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.share_receipt import verify_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex

from fakes import FakePipeline, MidStreamRaisingFakePipeline, RaisingFakePipeline

RECEIPT_KEY = "fake-signing-value-for-tests"

RAW_CONTEXT = [
    {"id": "MN 10:1", "pali": "sammā-sati", "english": "Right mindfulness is awareness of the present moment"},
    {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Too short"},
]


def _composer(context=RAW_CONTEXT, answer="The teaching is in [MN 10:1]."):
    pipeline = FakePipeline(context, answer)
    composer = AnswerComposer(
        pipeline=pipeline,
        guardrail=CitationGuardrail(),
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
        pipeline=MidStreamRaisingFakePipeline(RAW_CONTEXT),
        guardrail=CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
    )
    with pytest.raises(RuntimeError, match="synthesis failed"):
        await _collect(composer.answer_stream("mindfulness", top_k=10))
