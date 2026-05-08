import pytest
from backend.app.services.guardrail import CitationGuardrail

def test_guardrail_detects_hallucinations():
    guardrail = CitationGuardrail()

    # Mock context containing only DN 1:1 and DN 1:2
    context_chunks = [
        {"id": "DN 1:1", "pali": "...", "english": "..."},
        {"id": "DN 1:2", "pali": "...", "english": "..."},
    ]

    # Response with one correct and one hallucinated citation
    response = "The Buddha taught this in [DN 1:1] and also in [DN 5:10]."

    result = guardrail.process_response(response, context_chunks)

    assert result["is_faithful"] is False
    assert "DN 5:10" in result["hallucinations"]
    assert "[DN 5:10]" not in result["text"]
    assert "[Unverified]" in result["text"]
    assert "[DN 1:1]" in result["text"]

def test_guardrail_all_faithful():
    guardrail = CitationGuardrail()
    context_chunks = [
        {"id": "MN 10:1", "pali": "...", "english": "..."},
    ]
    response = "Check [MN 10:1] for details."

    result = guardrail.process_response(response, context_chunks)

    assert result["is_faithful"] is True
    assert len(result["hallucinations"]) == 0
    assert result["text"] == response

def test_guardrail_no_citations():
    guardrail = CitationGuardrail()
    context_chunks = [{"id": "DN 1:1", "pali": "...", "english": "..."}]
    response = "The Buddha taught the Four Noble Truths."

    result = guardrail.process_response(response, context_chunks)

    assert result["is_faithful"] is True
    assert result["text"] == response
