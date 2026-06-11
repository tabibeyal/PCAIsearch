import sys
import types
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


# Inject a mock resend module before any import of backend.app.main so the
# local `import resend` inside the /contact handler resolves to our stub.
_mock_resend = types.ModuleType("resend")
_mock_resend.Emails = MagicMock()
_mock_resend.Emails.send = MagicMock(return_value={"id": "stub"})
sys.modules.setdefault("resend", _mock_resend)

from backend.app.main import app  # noqa: E402


@pytest.fixture
def contact_client(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_fake_key")
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c


def test_contact_sends_email(contact_client):
    mock_send = MagicMock(return_value={"id": "abc123"})
    # Patch on the stub module that is already in sys.modules["resend"]
    with patch.object(sys.modules["resend"].Emails, "send", mock_send):
        r = contact_client.post("/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message from a user.",
        })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    mock_send.assert_called_once()
    call_params = mock_send.call_args[0][0]
    assert call_params["to"] == ["pcaisearch@atomicmail.io"]
    assert call_params["reply_to"] == "test@example.com"
    assert "Test User" in call_params["subject"]
    assert "This is a test message" in call_params["text"]
    assert call_params["from"] == "PCAIsearch <onboarding@resend.dev>"


def test_contact_rejects_missing_fields(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "test@example.com",
    })
    assert r.status_code == 422


def test_contact_rejects_invalid_email(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "not-an-email",
        "message": "This is a test message from a user.",
    })
    assert r.status_code == 422


def test_contact_rejects_short_message(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "test@example.com",
        "message": "Too short",
    })
    assert r.status_code == 422
