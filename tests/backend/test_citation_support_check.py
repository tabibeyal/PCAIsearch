"""Unit tests for CitationSupportCheck and its pure text-marking helpers.

httpx.MockTransport stands in for the network — the one system boundary
this class has (testing.md: mock only at boundaries). Everything else
(batched question shape, marker splicing) runs for real.
"""
import httpx
import pytest

from backend.app.services.citation_support_check import (
    CitationSupportCheck,
    CitationSupportCheckError,
    find_checkable_citations,
    mark_unsupported,
)

_FAKE_KEY = "test123"


def _checker(handler) -> CitationSupportCheck:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return CitationSupportCheck(api_key=_FAKE_KEY, client=client)


def _choice_response(relations: dict[str, str]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"answers": {k: {"choice": v} for k, v in relations.items()}},
    )


@pytest.mark.asyncio
async def test_check_returns_relations_in_order():
    checker = _checker(lambda request: _choice_response({"c0": "supports", "c1": "contradicts"}))
    citations = [
        {"claim": "Anger is unwholesome.", "passage": "Anger is an unwholesome state."},
        {"claim": "The Buddha praised anger.", "passage": "The Buddha condemned anger."},
    ]
    assert await checker.check(citations) == ["supports", "contradicts"]


@pytest.mark.asyncio
async def test_check_empty_list_makes_no_request():
    called = False

    def handler(request):
        nonlocal called
        called = True
        return _choice_response({})

    checker = _checker(handler)
    assert await checker.check([]) == []
    assert called is False


@pytest.mark.asyncio
async def test_check_sends_one_batched_request_for_multiple_citations():
    requests = []

    def handler(request):
        requests.append(request)
        return _choice_response({"c0": "supports", "c1": "supports", "c2": "says_nothing"})

    checker = _checker(handler)
    citations = [{"claim": f"claim {i}", "passage": f"passage {i}"} for i in range(3)]
    await checker.check(citations)
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_check_sends_bearer_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return _choice_response({"c0": "supports"})

    checker = _checker(handler)
    await checker.check([{"claim": "x", "passage": "y"}])
    assert seen["auth"] == f"Bearer {_FAKE_KEY}"


@pytest.mark.asyncio
async def test_check_raises_citation_support_check_error_on_http_failure():
    def handler(request):
        return httpx.Response(500, json={"error": "internal"})

    checker = _checker(handler)
    with pytest.raises(CitationSupportCheckError):
        await checker.check([{"claim": "x", "passage": "y"}])


@pytest.mark.asyncio
async def test_check_raises_citation_support_check_error_on_malformed_body():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    checker = _checker(handler)
    with pytest.raises(CitationSupportCheckError):
        await checker.check([{"claim": "x", "passage": "y"}])


@pytest.mark.asyncio
async def test_check_raises_citation_support_check_error_on_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    checker = _checker(handler)
    with pytest.raises(CitationSupportCheckError):
        await checker.check([{"claim": "x", "passage": "y"}])


# ── find_checkable_citations ─────────────────────────────────────────────────

def test_find_checkable_citations_includes_retrieved_id_with_passage():
    text = "Anger is unwholesome [DN 1:1]."
    found = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "Anger is an unwholesome state."})
    assert [c["id"] for c in found] == ["DN 1:1"]


def test_find_checkable_citations_excludes_id_not_retrieved_this_turn():
    text = "Anger is unwholesome [DN 1:1]."
    found = find_checkable_citations(text, set(), {"DN 1:1": "Anger is an unwholesome state."})
    assert found == []


def test_find_checkable_citations_excludes_id_with_no_passage_text():
    text = "Anger is unwholesome [DN 1:1]."
    found = find_checkable_citations(text, {"DN 1:1"}, {})
    assert found == []


def test_find_checkable_citations_captures_the_sentence_before_the_bracket():
    text = "First sentence here. Anger is unwholesome [DN 1:1]."
    found = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "..."})
    assert found[0]["claim"] == "Anger is unwholesome"


def test_find_checkable_citations_preserves_appearance_order():
    text = "One [MN 1:1]. Two [DN 1:1]."
    found = find_checkable_citations(
        text, {"MN 1:1", "DN 1:1"}, {"MN 1:1": "...", "DN 1:1": "..."}
    )
    assert [c["id"] for c in found] == ["MN 1:1", "DN 1:1"]


# ── mark_unsupported ──────────────────────────────────────────────────────────

def test_mark_unsupported_leaves_supported_citation_untouched():
    text = "Anger is unwholesome [DN 1:1]."
    citations = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "..."})
    assert mark_unsupported(text, citations, ["supports"]) == text


def test_mark_unsupported_flags_a_contradicting_citation():
    text = "Anger is unwholesome [DN 1:1]."
    citations = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "..."})
    result = mark_unsupported(text, citations, ["contradicts"])
    assert "[DN 1:1 unsupported]" in result


def test_mark_unsupported_flags_a_says_nothing_citation_the_same_as_contradicts():
    text = "Anger is unwholesome [DN 1:1]."
    citations = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "..."})
    result = mark_unsupported(text, citations, ["says_nothing"])
    assert "[DN 1:1 unsupported]" in result


def test_mark_unsupported_keeps_the_citation_id_intact_for_click_navigation():
    text = "Anger is unwholesome [DN 1:1]."
    citations = find_checkable_citations(text, {"DN 1:1"}, {"DN 1:1": "..."})
    result = mark_unsupported(text, citations, ["contradicts"])
    assert "DN 1:1" in result


def test_mark_unsupported_only_flags_the_unsupported_one_of_several():
    text = "One [MN 1:1]. Two [DN 1:1]."
    citations = find_checkable_citations(
        text, {"MN 1:1", "DN 1:1"}, {"MN 1:1": "...", "DN 1:1": "..."}
    )
    result = mark_unsupported(text, citations, ["supports", "contradicts"])
    assert "[MN 1:1]" in result
    assert "[DN 1:1 unsupported]" in result
