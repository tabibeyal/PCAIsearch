import json
import subprocess

_LABEL = "needs-triage"


class GhIssueTracker:
    """IssueTracker backed by the `gh` CLI, run inside a clone of the repo so `gh`
    infers the target repo from `git remote -v` (see docs/agents/issue-tracker.md)."""

    def create_issue(self, title: str, body: str) -> str:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body, "--label", _LABEL],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def find_open_issue(self, query: str) -> str | None:
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--label", _LABEL, "--json", "url,body", "--limit", "200"],
            capture_output=True,
            text=True,
            check=True,
        )
        needle = f"**Query:** {query}\n"
        for issue in json.loads(result.stdout):
            if needle in issue["body"]:
                return issue["url"]
        return None

    def comment(self, issue_url: str, body: str) -> None:
        subprocess.run(
            ["gh", "issue", "comment", issue_url, "--body", body],
            capture_output=True,
            text=True,
            check=True,
        )
