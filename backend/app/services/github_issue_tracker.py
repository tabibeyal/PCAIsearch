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
