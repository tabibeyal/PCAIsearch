import io
import json
import logging
import urllib.error
from unittest.mock import patch

import pytest

from backend.app.services.supabase_client import SupabaseRestClient


@patch("urllib.request.urlopen")
def test_get_builds_correct_url_and_query(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"[]"
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.get("feedback", eq={"rating": "down"}, is_null=["gap_issue_url"])

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback?rating=eq.down&gap_issue_url=is.null"


@patch("urllib.request.urlopen")
def test_get_with_select_and_order_assembles_query(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"[]"
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.get(
        "shared_answers",
        eq={"id": "abc123def456abc123def456abc123de"},
        select=["query", "answer", "context"],
    )

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == (
        "https://test.supabase.co/rest/v1/shared_answers"
        "?select=query,answer,context&id=eq.abc123def456abc123def456abc123de"
    )


@patch("urllib.request.urlopen")
def test_get_returns_parsed_json_rows(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
        [{"id": 1, "query": "what is dukkha?"}]
    ).encode()
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    rows = client.get("feedback", eq={"rating": "down"})

    assert rows == [{"id": 1, "query": "what is dukkha?"}]


@patch("urllib.request.urlopen")
def test_get_with_no_filters_omits_query_string(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"[]"
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.get("feedback")

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback"


@patch("urllib.request.urlopen")
def test_get_encodes_value_containing_postgrest_operators(mock_urlopen):
    """An id carrying `&select=*` must be encoded within the eq value, not
    split into a second filter — otherwise a crafted id enumerates all rows."""
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"[]"
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.get("shared_answers", eq={"id": "abc&select=*"}, select=["query", "answer", "context"])

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == (
        "https://test.supabase.co/rest/v1/shared_answers"
        "?select=query,answer,context&id=eq.abc%26select%3D%2A"
    )


@patch("urllib.request.urlopen")
def test_patch_sends_correct_body_and_query(mock_urlopen):
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.patch("feedback", {"gap_issue_url": "https://github.com/x/y/issues/1"}, eq={"id": 42})

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback?id=eq.42"
    assert json.loads(req.data) == {"gap_issue_url": "https://github.com/x/y/issues/1"}
    assert req.get_method() == "PATCH"


@patch("urllib.request.urlopen")
def test_patch_encodes_value_containing_postgrest_operators(mock_urlopen):
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    client.patch("feedback", {"gap_issue_url": "u"}, eq={"id": "42&select=*"})

    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://test.supabase.co/rest/v1/feedback?id=eq.42%26select%3D%2A"


@patch("urllib.request.urlopen")
def test_post_reraises_http_error_after_logging_response_body(mock_urlopen, caplog):
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://test.supabase.co/rest/v1/feedback",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b"constraint violation"),
    )
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    with caplog.at_level(logging.ERROR), pytest.raises(urllib.error.HTTPError):
        client.post("feedback", {"query": "q"}, error_label="feedback")

    assert "Supabase feedback insert failed" in caplog.text


@patch("urllib.request.urlopen")
def test_post_reraises_url_error_after_logging(mock_urlopen, caplog):
    mock_urlopen.side_effect = urllib.error.URLError("connection refused")
    client = SupabaseRestClient("https://test.supabase.co", "fake-key")

    with caplog.at_level(logging.ERROR), pytest.raises(urllib.error.URLError):
        client.post("shared_answers", {"id": "abc"}, error_label="share")

    assert "Supabase share insert failed (network)" in caplog.text