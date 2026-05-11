import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_search_returns_results(client):
    mock_results = [
        {"id": "DN 1:1", "pali": "evam me sutaṃ", "english": "Thus have I heard", "score": 0.99}
    ]
    with patch.object(app.state.pipeline, "search", new=AsyncMock(return_value=mock_results)):
        response = client.get("/search?q=Thus+have+I+heard")

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Thus have I heard"
    assert len(body["results"]) == 1
    assert body["results"][0]["id"] == "DN 1:1"


def test_search_requires_q_param(client):
    response = client.get("/search")
    assert response.status_code == 422


def test_search_empty_string_rejected(client):
    response = client.get("/search?q=")
    assert response.status_code == 422


def test_synthesize_returns_structured_response(client):
    mock_results = [{"id": "MN 10:1", "pali": "...", "english": "Mindfulness", "score": 0.95}]
    mock_answer = "The teaching on mindfulness is found in [MN 10:1]."

    with patch.object(app.state.pipeline, "search", new=AsyncMock(return_value=mock_results)), \
         patch.object(app.state.pipeline, "synthesize", new=AsyncMock(return_value=mock_answer)):
        response = client.get("/synthesize?q=mindfulness")

    assert response.status_code == 200
    body = response.json()
    assert "query" in body
    assert "answer" in body
    assert "hallucinations" in body
    assert "is_faithful" in body
    assert "context" in body
    assert body["is_faithful"] is True
    assert "[MN 10:1]" in body["answer"]


def test_synthesize_guardrail_flags_hallucinations(client):
    mock_results = [{"id": "MN 10:1", "pali": "...", "english": "Mindfulness", "score": 0.95}]
    # LLM cites DN 999:1 — a sutta that doesn't exist in the canon at all.
    mock_answer = "See [MN 10:1] and [DN 999:1] for details."

    with patch.object(app.state.pipeline, "search", new=AsyncMock(return_value=mock_results)), \
         patch.object(app.state.pipeline, "synthesize", new=AsyncMock(return_value=mock_answer)):
        response = client.get("/synthesize?q=mindfulness")

    assert response.status_code == 200
    body = response.json()
    assert body["is_faithful"] is False
    assert "DN 999:1" in body["hallucinations"]
    assert "[DN 999:1]" not in body["answer"]
    assert "[Hallucinated]" in body["answer"]


def test_synthesize_requires_q_param(client):
    response = client.get("/synthesize")
    assert response.status_code == 422
