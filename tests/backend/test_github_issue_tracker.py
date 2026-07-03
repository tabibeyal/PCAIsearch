import json
from unittest.mock import MagicMock, patch
from backend.app.services.github_issue_tracker import GhIssueTracker


@patch("subprocess.run")
def test_find_open_issue_matches_on_query_line_in_body(mock_run):
    mock_run.return_value = MagicMock(stdout=json.dumps([
        {"url": "https://github.com/x/y/issues/9", "body": "## Feedback\n\n- **Query:** what is dukkha?\n"},
        {"url": "https://github.com/x/y/issues/10", "body": "## Feedback\n\n- **Query:** what is anatta?\n"},
    ]))
    tracker = GhIssueTracker()

    found = tracker.find_open_issue("what is anatta?")

    assert found == "https://github.com/x/y/issues/10"


@patch("subprocess.run")
def test_find_open_issue_returns_none_when_no_match(mock_run):
    mock_run.return_value = MagicMock(stdout=json.dumps([
        {"url": "https://github.com/x/y/issues/9", "body": "- **Query:** what is dukkha?\n"},
    ]))
    tracker = GhIssueTracker()

    found = tracker.find_open_issue("what is nibbana?")

    assert found is None


@patch("subprocess.run")
def test_find_open_issue_only_searches_needs_triage_label(mock_run):
    mock_run.return_value = MagicMock(stdout="[]")
    tracker = GhIssueTracker()

    tracker.find_open_issue("what is dukkha?")

    args = mock_run.call_args[0][0]
    assert "--label" in args
    assert args[args.index("--label") + 1] == "needs-triage"


@patch("subprocess.run")
def test_comment_targets_the_given_issue_url(mock_run):
    tracker = GhIssueTracker()

    tracker.comment("https://github.com/x/y/issues/9", "down-voted again")

    args = mock_run.call_args[0][0]
    assert args == ["gh", "issue", "comment", "https://github.com/x/y/issues/9", "--body", "down-voted again"]
