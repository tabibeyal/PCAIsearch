"""Unit tests for ScopeGuard's threshold and failure contract.

httpx.MockTransport stands in for the network — the one system boundary
this class has (testing.md: mock only at boundaries). Everything else
(threshold comparison, error wrapping) runs for real.
"""
import httpx
import pytest

from backend.app.services.scope_guard import ScopeGuard, ScopeGuardError

_FAKE_KEY = "test123"


def _guard(handler) -> ScopeGuard:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ScopeGuard(api_key=_FAKE_KEY, client=client)


def _noul_response(value: float) -> httpx.Response:
    return httpx.Response(200, json={"answers": {"in_scope": {"noul": value}}})


@pytest.mark.asyncio
async def test_is_in_scope_true_above_threshold():
    guard = _guard(lambda request: _noul_response(0.92))
    assert await guard.is_in_scope("what did the Buddha say about anger") is True


@pytest.mark.asyncio
async def test_is_in_scope_false_below_threshold():
    guard = _guard(lambda request: _noul_response(0.02))
    assert await guard.is_in_scope("what is the best way to cook rice") is False


@pytest.mark.asyncio
async def test_is_in_scope_true_exactly_at_threshold():
    guard = _guard(lambda request: _noul_response(0.5))
    assert await guard.is_in_scope("borderline question") is True


@pytest.mark.asyncio
async def test_is_in_scope_sends_bearer_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return _noul_response(0.9)

    guard = _guard(handler)
    await guard.is_in_scope("what did the Buddha teach")
    assert seen["auth"] == f"Bearer {_FAKE_KEY}"


@pytest.mark.asyncio
async def test_is_in_scope_raises_scope_guard_error_on_http_failure():
    def handler(request):
        return httpx.Response(500, json={"error": "internal"})

    guard = _guard(handler)
    with pytest.raises(ScopeGuardError):
        await guard.is_in_scope("what did the Buddha say about anger")


@pytest.mark.asyncio
async def test_is_in_scope_raises_scope_guard_error_on_malformed_body():
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    guard = _guard(handler)
    with pytest.raises(ScopeGuardError):
        await guard.is_in_scope("what did the Buddha say about anger")


@pytest.mark.asyncio
async def test_is_in_scope_raises_scope_guard_error_on_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    guard = _guard(handler)
    with pytest.raises(ScopeGuardError):
        await guard.is_in_scope("what did the Buddha say about anger")
