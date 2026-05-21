import os
import sqlite3
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import backend.app.main as m
from backend.app.main import app


@pytest.fixture
def feedback_client(tmp_path, monkeypatch):
    db = tmp_path / "feedback.db"
    monkeypatch.setattr(m, "_FEEDBACK_DB", db)
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("qdrant_client.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c, db


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
