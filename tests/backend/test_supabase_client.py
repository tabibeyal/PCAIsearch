import json
from unittest.mock import MagicMock, patch
from backend.app.services.supabase_client import SupabaseRestClient


@patch("urllib.request.urlopen")
def test_get_builds_correct_url_and_query(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"[]"
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.get("feedback", "rating=eq.down&gap_issue_url=is.null")

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback?rating=eq.down&gap_issue_url=is.null"


@patch("urllib.request.urlopen")
def test_get_returns_parsed_json_rows(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
        [{"id": 1, "query": "what is dukkha?"}]
    ).encode()
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    rows = client.get("feedback", "rating=eq.down")

    assert rows == [{"id": 1, "query": "what is dukkha?"}]


@patch("urllib.request.urlopen")
def test_patch_sends_correct_body_and_query(mock_urlopen):
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.patch("feedback", "id=eq.42", {"gap_issue_url": "https://github.com/x/y/issues/1"})

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback?id=eq.42"
    assert json.loads(req.data) == {"gap_issue_url": "https://github.com/x/y/issues/1"}
    assert req.get_method() == "PATCH"
