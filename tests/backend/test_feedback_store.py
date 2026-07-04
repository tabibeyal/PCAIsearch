from typing import Any

import pytest

from backend.app.services.feedback_store import SQLiteFeedbackStore, SupabaseFeedbackStore
from backend.app.services.gap_detector import FeedbackCandidate
from tests.backend.fakes import FakeSupabaseRestClient


class _SupabaseHarness:
    def __init__(self) -> None:
        self.client = FakeSupabaseRestClient()
        self.writer = SupabaseFeedbackStore(self.client)

    def all_rows(self) -> list[dict[str, Any]]:
        return self.client.get("feedback", "")


class _SQLiteHarness:
    def __init__(self, db_path) -> None:
        self.writer = SQLiteFeedbackStore(db_path)
        self._db_path = db_path

    def all_rows(self) -> list[dict[str, Any]]:
        import sqlite3

        con = sqlite3.connect(self._db_path)
        try:
            cols = ("query", "answer", "rating", "category", "comment")
            rows = con.execute(f"SELECT {', '.join(cols)} FROM feedback").fetchall()
        finally:
            con.close()
        return [dict(zip(cols, row)) for row in rows]


@pytest.fixture(params=["supabase", "sqlite"])
def feedback_writer(request, tmp_path):
    if request.param == "supabase":
        return _SupabaseHarness()
    return _SQLiteHarness(tmp_path / "feedback.db")


def test_insert_persists_query(feedback_writer):
    feedback_writer.writer.insert("What is dukkha?", "Suffering.", "up", None, None)

    assert feedback_writer.all_rows()[0]["query"] == "What is dukkha?"


def test_insert_persists_answer(feedback_writer):
    feedback_writer.writer.insert("What is dukkha?", "Suffering.", "up", None, None)

    assert feedback_writer.all_rows()[0]["answer"] == "Suffering."


def test_insert_persists_rating(feedback_writer):
    feedback_writer.writer.insert("What is dukkha?", "Suffering.", "down", None, None)

    assert feedback_writer.all_rows()[0]["rating"] == "down"


def test_insert_persists_category(feedback_writer):
    feedback_writer.writer.insert("q", "a", "down", "Too vague", None)

    assert feedback_writer.all_rows()[0]["category"] == "Too vague"


def test_insert_persists_comment(feedback_writer):
    feedback_writer.writer.insert("q", "a", "down", "Too vague", "needs more depth")

    assert feedback_writer.all_rows()[0]["comment"] == "needs more depth"


def test_fetch_down_votes_sees_newly_inserted_down_vote():
    store = SupabaseFeedbackStore(FakeSupabaseRestClient())
    store.insert("what is anatta?", "...", "down", "Missing important nuance", "meh")

    candidates = store.fetch_down_votes()

    assert candidates == [
        FeedbackCandidate(id=1, query="what is anatta?", answer="...", category="Missing important nuance", comment="meh")
    ]


def test_fetch_down_votes_excludes_up_votes():
    store = SupabaseFeedbackStore(FakeSupabaseRestClient())
    store.insert("q", "a", "up", None, None)

    assert store.fetch_down_votes() == []


def test_mark_handled_removes_row_from_fetch_down_votes():
    store = SupabaseFeedbackStore(FakeSupabaseRestClient())
    store.insert("q", "a", "down", "Missing important nuance", "meh")
    [candidate] = store.fetch_down_votes()

    store.mark_handled(candidate.id, "https://github.com/x/y/issues/1")

    assert store.fetch_down_votes() == []
