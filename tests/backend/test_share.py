import sqlite3

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

import backend.app.main as m
from backend.app.main import app
from backend.app.services.share_receipt import generate_receipt
from backend.app.services.share_store import SQLiteShareStore, SupabaseShareStore
from tests.backend.fakes import FakeSupabaseRestClient

SIGNING_KEY = "fake-signing-value-for-tests"


def _valid_payload() -> dict:
    query = "What is dukkha?"
    answer = "Dukkha means suffering [MN 10:1]."
    context = [{"id": "MN 10:1", "english": "Suffering is...", "title": "Mindfulness Meditation"}]
    receipt = generate_receipt(query, answer, context, SIGNING_KEY)
    return {"query": query, "answer": answer, "context": context, "receipt": receipt}


def _sanitized(context: list[dict]) -> list[dict]:
    fields = ("id", "pali", "english", "score", "title", "passage")
    return [{field: c.get(field) for field in fields} for c in context]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(m, "_SHARE_RECEIPT_SECRET", SIGNING_KEY)
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def share_client(client, tmp_path):
    db = tmp_path / "feedback.db"
    client.app.state.share_store = SQLiteShareStore(db)
    return client, db


@pytest.fixture
def share_supabase_client(client):
    fake = FakeSupabaseRestClient()
    client.app.state.share_store = SupabaseShareStore(fake)
    return client, fake


def test_share_valid_receipt_creates_shareable_answer(share_client):
    client, _ = share_client
    r = client.post("/share", json=_valid_payload())
    assert r.status_code == 200
    assert "id" in r.json()


def test_share_stored_answer_retrievable_by_id(share_client):
    client, _ = share_client
    payload = _valid_payload()
    share_id = client.post("/share", json=payload).json()["id"]

    r = client.get(f"/share/{share_id}")

    assert r.status_code == 200


def test_share_stored_answer_preserves_query(share_client):
    client, _ = share_client
    payload = _valid_payload()
    share_id = client.post("/share", json=payload).json()["id"]

    body = client.get(f"/share/{share_id}").json()

    assert body["query"] == payload["query"]


def test_share_stored_answer_preserves_answer(share_client):
    client, _ = share_client
    payload = _valid_payload()
    share_id = client.post("/share", json=payload).json()["id"]

    body = client.get(f"/share/{share_id}").json()

    assert body["answer"] == payload["answer"]


def test_share_stored_answer_preserves_context(share_client):
    client, _ = share_client
    payload = _valid_payload()
    share_id = client.post("/share", json=payload).json()["id"]

    body = client.get(f"/share/{share_id}").json()

    assert body["context"] == _sanitized(payload["context"])


def test_share_unknown_id_returns_404(share_client):
    client, _ = share_client
    r = client.get("/share/does-not-exist")
    assert r.status_code == 404


def test_share_tampered_receipt_rejected_with_no_db_write(share_client):
    client, db = share_client
    payload = _valid_payload()
    payload["answer"] = "Something completely different."

    r = client.post("/share", json=payload)

    assert r.status_code == 400
    con = sqlite3.connect(db)
    count = con.execute("SELECT COUNT(*) FROM shared_answers").fetchone()[0]
    con.close()
    assert count == 0


def test_supabase_share_posts_correct_query(share_supabase_client):
    client, fake = share_supabase_client
    payload = _valid_payload()

    client.post("/share", json=payload)

    [row] = fake.get("shared_answers", "")
    assert row["query"] == payload["query"]


def test_supabase_share_posts_correct_answer(share_supabase_client):
    client, fake = share_supabase_client
    payload = _valid_payload()

    client.post("/share", json=payload)

    [row] = fake.get("shared_answers", "")
    assert row["answer"] == payload["answer"]


def test_supabase_share_posts_sanitized_context(share_supabase_client):
    client, fake = share_supabase_client
    payload = _valid_payload()

    client.post("/share", json=payload)

    [row] = fake.get("shared_answers", "")
    assert row["context"] == _sanitized(payload["context"])


def test_supabase_share_posts_generated_id(share_supabase_client):
    client, fake = share_supabase_client
    payload = _valid_payload()

    r = client.post("/share", json=payload)

    [row] = fake.get("shared_answers", "")
    assert row["id"] == r.json()["id"]


def test_supabase_share_get_returns_stored_answer(share_supabase_client):
    client, fake = share_supabase_client
    payload = _valid_payload()
    share_id = client.post("/share", json=payload).json()["id"]

    r = client.get(f"/share/{share_id}")

    assert r.status_code == 200
    assert r.json() == {
        "query": payload["query"],
        "answer": payload["answer"],
        "context": _sanitized(payload["context"]),
    }
