"""Unit tests for Retriever commentary exclusion.

The in-memory Qdrant used by the e2e suite supports payload filters, so it
can't reproduce the Qdrant Cloud free-tier limitation that forces commentary
to be excluded in Python (#105): the free tier rejects any filtered query
with "Index required but not found" and also blocks index creation. These
tests use a fake client to assert the post-filter contract directly —
commentary is dropped in Python and no `section` filter reaches Qdrant.
"""
import pytest

from backend.app.services.retriever import Retriever


class _Point:
    def __init__(self, payload, score):
        self.payload = payload
        self.score = score


class _Response:
    def __init__(self, points):
        self.points = points


class _FakeEmbeddingMgr:
    def encode(self, _query):
        return [0.0, 0.0, 0.0]


class FakeQdrantClient:
    """Records query_points calls and returns a fixed candidate pool."""

    def __init__(self, points):
        self._points = points
        self.calls = []

    async def query_points(self, *, collection_name, query, limit, with_payload, query_filter):
        self.calls.append({"limit": limit, "query_filter": query_filter})
        # Return the whole pool; the retriever's post-filter + trim handles sizing.
        return _Response(list(self._points))


# Commentary interleaved with canon so that dropping commentary still leaves
# enough canon to fill top_k.
CANDIDATES = [
    _Point({"id": "MN 10:1", "pali": "sati", "english": "Right mindfulness of breathing", "nikaya": "MN"}, 0.9),
    _Point({"id": "AN 4:1", "pali": "", "english": "Translator notes metta means kindness", "nikaya": "AN", "section": "commentary"}, 0.8),
    _Point({"id": "SN 22.59:1", "pali": "anicca", "english": "Form is impermanent", "nikaya": "SN"}, 0.7),
    _Point({"id": "DN 1:2", "pali": "", "english": "This sutta introduces the Buddha", "nikaya": "DN", "section": "commentary"}, 0.6),
    _Point({"id": "MN 22:1", "pali": "", "english": "The snake simile", "nikaya": "MN"}, 0.5),
]


def _retriever():
    return Retriever(
        client=FakeQdrantClient(CANDIDATES),
        embedding_mgr=_FakeEmbeddingMgr(),
        collection_name="pali_canon",
        executor=None,
    )


@pytest.mark.asyncio
async def test_exclude_commentary_returns_only_canon_ids():
    r = _retriever()
    results = await r.retrieve("mindfulness kindness", top_k=3, exclude_commentary=True)
    assert [c["id"] for c in results] == ["MN 10:1", "SN 22.59:1", "MN 22:1"]


@pytest.mark.asyncio
async def test_exclude_commentary_drops_every_commentary_chunk():
    r = _retriever()
    results = await r.retrieve("mindfulness kindness", top_k=3, exclude_commentary=True)
    assert all(c.get("section") != "commentary" for c in results)


@pytest.mark.asyncio
async def test_exclude_commentary_fills_top_k_with_canon():
    # Even with commentary ranked above some canon, enough canon survives the
    # post-filter to fill the requested top_k (the point of over-retrieving).
    r = _retriever()
    results = await r.retrieve("mindfulness kindness", top_k=3, exclude_commentary=True)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_exclude_commentary_sends_no_section_filter():
    # The free tier can't filter on `section`, so commentary exclusion must not
    # push a must_not section condition into Qdrant (#105).
    r = _retriever()
    await r.retrieve("mindfulness", top_k=3, exclude_commentary=True)
    assert r.client.calls[0]["query_filter"] is None


@pytest.mark.asyncio
async def test_default_retrieve_keeps_commentary_marker():
    r = _retriever()
    results = await r.retrieve("mindfulness kindness", top_k=5)
    by_id = {c["id"]: c for c in results}
    assert by_id["AN 4:1"]["section"] == "commentary"


@pytest.mark.asyncio
async def test_default_retrieve_omits_section_on_canon():
    r = _retriever()
    results = await r.retrieve("mindfulness kindness", top_k=5)
    by_id = {c["id"]: c for c in results}
    assert "section" not in by_id["MN 10:1"]