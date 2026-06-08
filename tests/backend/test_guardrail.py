from pathlib import Path
import pytest
from backend.app.services.guardrail import CitationGuardrail
from backend.app.services.citation_oracle import CitationOracle

DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"


def test_guardrail_detects_hallucinations():
    # Without a CitationOracle: any citation not in retrieved chunks is a hallucination.
    guardrail = CitationGuardrail()
    context_chunks = [
        {"id": "DN 1:1", "pali": "...", "english": "..."},
        {"id": "DN 1:2", "pali": "...", "english": "..."},
    ]
    response = "The Buddha taught this in [DN 1:1] and also in [DN 5:10]."

    result = guardrail.process_response(response, context_chunks)

    assert result["is_faithful"] is False
    assert "DN 5:10" in result["hallucinations"]
    assert "[DN 5:10]" not in result["text"]
    assert "[Hallucinated]" in result["text"]
    assert "[DN 1:1]" in result["text"]


def test_guardrail_all_faithful():
    guardrail = CitationGuardrail()
    context_chunks = [{"id": "MN 10:1", "pali": "...", "english": "..."}]
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


# ── Canon-aware tests ──────────────────────────────────────────────────────────

def test_canon_guardrail_distinguishes_canonical_miss():
    # DN 15:1 exists in canon but isn't in the retrieved context.
    # With an oracle it should be a canonical_miss, not a hallucination.
    oracle = CitationOracle(DUMPS_DIR)
    guardrail = CitationGuardrail(oracle=oracle)
    context_chunks = [{"id": "MN 10:1", "pali": "...", "english": "..."}]
    response = "See also [DN 15:1] and [MN 10:1]."

    result = guardrail.process_response(response, context_chunks)

    assert "DN 15:1" not in result["hallucinations"]
    assert "DN 15:1" in result["canonical_misses"]
    assert "[Unverified]" in result["text"]   # canonical miss label
    assert "[DN 15:1]" not in result["text"]
    assert "[MN 10:1]" in result["text"]      # retrieved citation kept


def test_canon_guardrail_flags_nonexistent_sutta():
    # DN 999:1 does not exist in the canon — should be a hallucination.
    oracle = CitationOracle(DUMPS_DIR)
    guardrail = CitationGuardrail(oracle=oracle)
    context_chunks = [{"id": "MN 10:1", "pali": "...", "english": "..."}]
    response = "The text says [DN 999:1]."

    result = guardrail.process_response(response, context_chunks)

    assert "DN 999:1" in result["hallucinations"]
    assert "DN 999:1" not in result["canonical_misses"]
    assert "[Hallucinated]" in result["text"]


def test_guardrail_compound_sutta_id():
    # Compound IDs like SN 12.2:3 must be detected, not silently passed through.
    oracle = CitationOracle(DUMPS_DIR)
    guardrail = CitationGuardrail(oracle=oracle)
    context_chunks = [{"id": "SN 12.2:3", "pali": "...", "english": "..."}]
    response = "See [SN 12.2:3] and the invented [SN 12.2:999]."

    result = guardrail.process_response(response, context_chunks)

    assert "[SN 12.2:3]" in result["text"]       # retrieved: kept intact
    assert "SN 12.2:999" in result["hallucinations"]  # verse doesn't exist
    assert "[Hallucinated]" in result["text"]


def test_canon_guardrail_is_faithful_no_hallucinations():
    # Retrieved citation + canonical miss → is_faithful True (no invented suttas)
    oracle = CitationOracle(DUMPS_DIR)
    guardrail = CitationGuardrail(oracle=oracle)
    context_chunks = [{"id": "MN 10:1", "pali": "...", "english": "..."}]
    response = "See [MN 10:1] and also [DN 15:1]."

    result = guardrail.process_response(response, context_chunks)

    assert result["is_faithful"] is True   # no hallucinations
    assert len(result["canonical_misses"]) == 1
