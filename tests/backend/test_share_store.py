import pytest

from backend.app.services.share_store import SQLiteShareStore, SupabaseShareStore
from tests.backend.fakes import FakeSupabaseRestClient


@pytest.fixture(params=["supabase", "sqlite"])
def share_store(request, tmp_path):
    if request.param == "supabase":
        return SupabaseShareStore(FakeSupabaseRestClient())
    return SQLiteShareStore(tmp_path / "feedback.db")


def test_fetch_unknown_id_returns_none(share_store):
    assert share_store.fetch("does-not-exist") is None


def test_save_then_fetch_preserves_query(share_store):
    share_store.save("abc123", "What is dukkha?", "Suffering.", [{"id": "MN 10:1"}])

    assert share_store.fetch("abc123")["query"] == "What is dukkha?"


def test_save_then_fetch_preserves_answer(share_store):
    share_store.save("abc123", "What is dukkha?", "Suffering.", [{"id": "MN 10:1"}])

    assert share_store.fetch("abc123")["answer"] == "Suffering."


def test_save_then_fetch_preserves_context(share_store):
    context = [{"id": "MN 10:1", "english": "Suffering is...", "title": "Mindfulness Meditation"}]
    share_store.save("abc123", "What is dukkha?", "Suffering.", context)

    assert share_store.fetch("abc123")["context"] == context


def test_save_is_keyed_by_share_id(share_store):
    share_store.save("first-id", "q1", "a1", [])
    share_store.save("second-id", "q2", "a2", [])

    assert share_store.fetch("second-id")["query"] == "q2"
