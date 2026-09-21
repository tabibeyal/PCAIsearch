import json

import pytest

from backend.app.services.answer_composer import AnswerComposer
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.passage_context import PassageStore
from backend.app.services.scope_guard import OUT_OF_SCOPE_MESSAGE
from backend.app.services.share_receipt import verify_receipt
from backend.app.services.sutta_title_index import SuttaTitleIndex

from fakes import (
    FakeCitationSupportCheck,
    FakePipeline,
    FakeScopeGuard,
    MidStreamRaisingFakePipeline,
    RaisingFakePipeline,
)

RECEIPT_KEY = "fake-signing-value-for-tests"


def _raw_context():
    # Fresh dicts per call: _attach_titles/_attach_passages mutate chunks in
    # place, so a shared module-level list would couple tests to each other.
    return [
        {"id": "MN 10:1", "english": "Right mindfulness is awareness of the present moment"},
        {"id": "DN 1:1", "english": "Too short"},
    ]


def _composer(
    context=None,
    answer="The teaching is in [MN 10:1].",
    guardrail=None,
    scope_guard=None,
    citation_support_check=None,
):
    pipeline = FakePipeline(_raw_context() if context is None else context, answer)
    composer = AnswerComposer(
        pipeline=pipeline,
        guardrail=guardrail if guardrail is not None else CitationGuardrail(),
        passages=PassageStore(),
        title_index=SuttaTitleIndex([{"sutta_id": "MN10", "title_pali": "x", "title_english": "y"}]),
        receipt_secret=RECEIPT_KEY,
        scope_guard=scope_guard,
        citation_support_check=citation_support_check,
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


# --- scope guard wiring (#198) --------------------------------------------

@pytest.mark.asyncio
async def test_answer_returns_refusal_when_guard_says_out_of_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=False))
    result = await composer.answer("what is the best way to cook rice", top_k=10)
    assert result["answer"] == OUT_OF_SCOPE_MESSAGE


@pytest.mark.asyncio
async def test_answer_skips_pipeline_search_when_guard_says_out_of_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=False))
    await composer.answer("what is the best way to cook rice", top_k=10)
    assert pipeline.search_calls == []


@pytest.mark.asyncio
async def test_answer_runs_pipeline_when_guard_says_in_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=True))
    result = await composer.answer("mindfulness", top_k=10)
    assert result["answer"] == "The teaching is in [MN 10:1]."


@pytest.mark.asyncio
async def test_answer_runs_pipeline_unguarded_when_guard_fails():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(raises=True))
    result = await composer.answer("mindfulness", top_k=10)
    assert result["answer"] == "The teaching is in [MN 10:1]."


@pytest.mark.asyncio
async def test_answer_without_a_guard_always_runs_the_pipeline():
    composer, pipeline = _composer()
    await composer.answer("what is the best way to cook rice", top_k=10)
    assert len(pipeline.search_calls) == 1


@pytest.mark.asyncio
async def test_answer_stream_yields_only_a_done_event_when_out_of_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=False))
    events = await _collect(composer.answer_stream("what is the best way to cook rice", top_k=10))
    assert [e["type"] for e in events] == ["done"]


@pytest.mark.asyncio
async def test_answer_stream_done_event_carries_the_refusal_when_out_of_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=False))
    events = await _collect(composer.answer_stream("what is the best way to cook rice", top_k=10))
    assert events[-1]["answer"] == OUT_OF_SCOPE_MESSAGE


@pytest.mark.asyncio
async def test_answer_stream_skips_pipeline_search_when_out_of_scope():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(in_scope=False))
    await _collect(composer.answer_stream("what is the best way to cook rice", top_k=10))
    assert pipeline.search_calls == []


@pytest.mark.asyncio
async def test_answer_stream_runs_pipeline_unguarded_when_guard_fails():
    composer, pipeline = _composer(scope_guard=FakeScopeGuard(raises=True))
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert events[-1]["answer"] == "The teaching is in [MN 10:1]."


# --- citation support check wiring (#208) ---------------------------------

@pytest.mark.asyncio
async def test_answer_leaves_citation_unmarked_when_check_disabled():
    composer, _ = _composer()
    result = await composer.answer("mindfulness", top_k=10)
    assert result["answer"] == "The teaching is in [MN 10:1]."


@pytest.mark.asyncio
async def test_answer_leaves_supported_citation_unmarked():
    check = FakeCitationSupportCheck(relation="supports")
    composer, _ = _composer(citation_support_check=check)
    result = await composer.answer("mindfulness", top_k=10)
    assert result["answer"] == "The teaching is in [MN 10:1]."


@pytest.mark.asyncio
async def test_answer_flags_a_citation_the_check_says_contradicts():
    check = FakeCitationSupportCheck(relation="contradicts")
    composer, _ = _composer(citation_support_check=check)
    result = await composer.answer("mindfulness", top_k=10)
    assert "[MN 10:1 unsupported]" in result["answer"]


@pytest.mark.asyncio
async def test_answer_flags_a_citation_the_check_says_says_nothing():
    check = FakeCitationSupportCheck(relation="says_nothing")
    composer, _ = _composer(citation_support_check=check)
    result = await composer.answer("mindfulness", top_k=10)
    assert "[MN 10:1 unsupported]" in result["answer"]


@pytest.mark.asyncio
async def test_answer_flagged_citation_receipt_still_verifies():
    check = FakeCitationSupportCheck(relation="contradicts")
    composer, _ = _composer(citation_support_check=check)
    result = await composer.answer("mindfulness", top_k=10)
    assert verify_receipt(result["query"], result["answer"], result["context"], result["receipt"], RECEIPT_KEY)


@pytest.mark.asyncio
async def test_answer_publishes_citation_unmarked_when_check_fails():
    check = FakeCitationSupportCheck(raises=True)
    composer, _ = _composer(citation_support_check=check)
    result = await composer.answer("mindfulness", top_k=10)
    assert result["answer"] == "The teaching is in [MN 10:1]."


@pytest.mark.asyncio
async def test_answer_does_not_check_an_unverified_citation():
    # A citation to an ID that wasn't retrieved this turn is guardrail.py's
    # business ([Unverified]/[Hallucinated]), not this check's — it never
    # reaches CitationSupportCheck.check() at all.
    check = FakeCitationSupportCheck(relation="contradicts")
    composer, _ = _composer(answer="Also see [DN 99:99].", citation_support_check=check)
    await composer.answer("mindfulness", top_k=10)
    assert check.batches == []


@pytest.mark.asyncio
async def test_answer_batches_multiple_citations_into_one_check_call():
    check = FakeCitationSupportCheck(relation="supports")
    composer, _ = _composer(
        context=[
            {"id": "MN 10:1", "english": "Right mindfulness is awareness of the present moment"},
            {"id": "SN 45:8", "english": "The eightfold path leads to the end of suffering"},
        ],
        answer="One point is in [MN 10:1]. Another is in [SN 45:8].",
        citation_support_check=check,
    )
    await composer.answer("mindfulness", top_k=10)
    assert len(check.batches) == 1
    assert len(check.batches[0]) == 2


@pytest.mark.asyncio
async def test_answer_stream_flags_a_citation_the_check_says_contradicts():
    check = FakeCitationSupportCheck(relation="contradicts")
    composer, _ = _composer(citation_support_check=check)
    events = await _collect(composer.answer_stream("mindfulness", top_k=10))
    assert "[MN 10:1 unsupported]" in events[-1]["answer"]

