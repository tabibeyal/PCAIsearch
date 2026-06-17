import json
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import urllib.request
import backend.app.main as m
from backend.app.main import app


@pytest.fixture
def feedback_client(tmp_path, monkeypatch):
    db = tmp_path / "feedback.db"
    monkeypatch.setattr(m, "_FEEDBACK_DB", db)
    monkeypatch.setattr(m, "_SUPABASE_URL", None)
    monkeypatch.setattr(m, "_SUPABASE_KEY", None)
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c, db


@pytest.fixture
def supabase_client(monkeypatch):
    monkeypatch.setattr(m, "_SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr(m, "_SUPABASE_KEY", "fake-service-role-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c


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


@pytest.fixture
def patched_urlopen():
    fake_response = MagicMock()
    with patch("urllib.request.urlopen", return_value=fake_response) as p:
        yield p


def test_supabase_feedback_posts_correct_body(supabase_client, patched_urlopen):
    r = supabase_client.post("/feedback", json={
        "query": "What is nibbana?",
        "answer": "Nibbana is the cessation of craving.",
        "rating": "down",
        "category": "Too vague",
        "comment": "Needs more depth",
    })

    assert r.status_code == 200
    posted = patched_urlopen.call_args[0][0]
    posted_body = json.loads(posted.data)
    assert posted_body == {
        "query": "What is nibbana?",
        "answer": "Nibbana is the cessation of craving.",
        "rating": "down",
        "category": "Too vague",
        "comment": "Needs more depth",
    }


def test_supabase_feedback_uses_correct_url_and_headers(supabase_client, patched_urlopen):
    supabase_client.post("/feedback", json={
        "query": "q",
        "answer": "a",
        "rating": "up",
        "category": None,
        "comment": None,
    })

    req = patched_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback"
    assert req.headers["Apikey"] == "fake-service-role-key"
    assert req.headers["Authorization"] == "Bearer fake-service-role-key"
