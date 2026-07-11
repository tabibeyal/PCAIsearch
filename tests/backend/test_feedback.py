import sqlite3
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.feedback_store import SupabaseFeedbackStore
from tests.backend.fakes import FakeSupabaseRestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "feedback.db"))
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def feedback_client(client, tmp_path):
    return client, tmp_path / "feedback.db"


@pytest.fixture
def supabase_feedback_client(client):
    fake = FakeSupabaseRestClient()
    client.app.state.feedback_store = SupabaseFeedbackStore(fake)
    return client, fake


def test_feedback_thumbs_up_stored(feedback_client):
    client, db = feedback_client
    r = client.post("/feedback", json={
        "query": "What is dukkha?",
        "answer": "Dukkha means suffering.",
        "rating": "up",
        "category": None,
        "comment": None,
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    con = sqlite3.connect(db)
    rows = con.execute("SELECT query, rating, category FROM feedback").fetchall()
    con.close()
    assert rows == [("What is dukkha?", "up", None)]


def test_feedback_thumbs_down_with_category_stored(feedback_client):
    client, db = feedback_client
    r = client.post("/feedback", json={
        "query": "What is nibbana?",
        "answer": "Nibbana is the cessation of craving.",
        "rating": "down",
        "category": "Too vague",
        "comment": "Needs more depth",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    con = sqlite3.connect(db)
    rows = con.execute("SELECT rating, category, comment FROM feedback").fetchall()
    con.close()
    assert rows == [("down", "Too vague", "Needs more depth")]


def test_feedback_missing_required_field(feedback_client):
    client, _ = feedback_client
    r = client.post("/feedback", json={"query": "test"})
    assert r.status_code == 422


def _supabase_feedback_payload() -> dict:
    return {
        "query": "What is nibbana?",
        "answer": "Nibbana is the cessation of craving.",
        "rating": "down",
        "category": "Too vague",
        "comment": "Needs more depth",
    }


def test_supabase_feedback_post_returns_200(supabase_feedback_client):
    client, _ = supabase_feedback_client

    r = client.post("/feedback", json=_supabase_feedback_payload())

    assert r.status_code == 200


def test_supabase_feedback_posts_query(supabase_feedback_client):
    client, fake = supabase_feedback_client

    client.post("/feedback", json=_supabase_feedback_payload())

    [row] = fake.get("feedback")
    assert row["query"] == "What is nibbana?"


def test_supabase_feedback_posts_rating(supabase_feedback_client):
    client, fake = supabase_feedback_client

    client.post("/feedback", json=_supabase_feedback_payload())

    [row] = fake.get("feedback")
    assert row["rating"] == "down"


def test_supabase_feedback_posts_category(supabase_feedback_client):
    client, fake = supabase_feedback_client

    client.post("/feedback", json=_supabase_feedback_payload())

    [row] = fake.get("feedback")
    assert row["category"] == "Too vague"


def test_supabase_feedback_posts_comment(supabase_feedback_client):
    client, fake = supabase_feedback_client

    client.post("/feedback", json=_supabase_feedback_payload())

    [row] = fake.get("feedback")
    assert row["comment"] == "Needs more depth"
