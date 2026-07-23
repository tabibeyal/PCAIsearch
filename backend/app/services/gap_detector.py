from dataclasses import dataclass
from typing import Any, Protocol

# Categories that describe a wrong or missing sutta selection. The other feedback
# categories ("Doctrinally inaccurate", "Sources don't support the answer", "Too
# vague") more often point at synthesis or guardrail problems than at retrieval,
# and would make this a noisy false-positive generator if included.
QUALIFYING_CATEGORIES = frozenset({
    "Not relevant to my question",
    "Missing important nuance",
})


@dataclass(frozen=True)
class FeedbackCandidate:
    id: Any
    query: str
    answer: str
    category: str | None
    comment: str | None


class FeedbackStore(Protocol):
    def fetch_down_votes(self) -> list[FeedbackCandidate]:
        """Rows with rating='down' and gap_issue_url IS NULL, most recent first."""
        ...

    def mark_handled(self, feedback_id: Any, issue_url: str) -> None:
        ...


class RetrievalPipeline(Protocol):
    async def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        ...


class IssueTracker(Protocol):
    def create_issue(self, title: str, body: str) -> str:
        """Files a new issue and returns its URL."""
        ...

    def find_open_issue(self, query: str) -> str | None:
        """Returns the URL of an open gap-detector issue already filed for this
        query text, or None if none exists."""
        ...

    def comment(self, issue_url: str, body: str) -> None:
        ...


class GapDetector:
    """Scans down-voted feedback for likely retrieval gaps and files GitHub issues
    a human can triage. See ADR-0004 and CONTEXT.md § Gap detection."""

    def __init__(
        self,
        feedback_store: FeedbackStore,
        pipeline: RetrievalPipeline,
        issue_tracker: IssueTracker,
        *,
        max_issues_per_run: int = 5,
        candidate_top_k: int = 10,
    ) -> None:
        self._feedback_store = feedback_store
        self._pipeline = pipeline
        self._issue_tracker = issue_tracker
        self._max_issues_per_run = max_issues_per_run
        self._candidate_top_k = candidate_top_k

    async def run(self) -> list[str]:
        """Files an issue for each qualifying candidate, up to the per-run cap.
        Returns the URLs of issues filed this run."""
        filed: list[str] = []
        for candidate in self._qualifying_candidates():
            if len(filed) >= self._max_issues_per_run:
                break
            existing_url = self._issue_tracker.find_open_issue(candidate.query)
            if existing_url:
                self._issue_tracker.comment(existing_url, _followup_comment(candidate))
                issue_url = existing_url
            else:
                retrieved = await self._pipeline.search(candidate.query, top_k=self._candidate_top_k)
                issue_url = self._issue_tracker.create_issue(
                    _issue_title(candidate.query), _issue_body(candidate, retrieved)
                )
            self._feedback_store.mark_handled(candidate.id, issue_url)
            filed.append(issue_url)
        return filed

    def _qualifying_candidates(self) -> list[FeedbackCandidate]:
        return [c for c in self._feedback_store.fetch_down_votes() if c.category in QUALIFYING_CATEGORIES]


def _issue_title(query: str) -> str:
    truncated = query if len(query) <= 80 else query[:77] + "..."
    return f"Possible retrieval gap: {truncated}"


def _followup_comment(candidate: FeedbackCandidate) -> str:
    return (
        "Down-voted again for the same query.\n\n"
        f"- **Category:** {candidate.category}\n"
        f"- **Comment:** {candidate.comment or '(none)'}\n\n"
        "_Filed automatically by the Gap Detector — see ADR-0004 and CONTEXT.md § Gap detection._"
    )


def _issue_body(candidate: FeedbackCandidate, retrieved: list[dict[str, Any]]) -> str:
    candidates_lines = "\n".join(
        f"{i}. `{r.get('id')}` — rerank score {r.get('rerank_score', float('-inf')):.3f}"
        for i, r in enumerate(retrieved, start=1)
    ) or "(no candidates retrieved)"
    return (
        "## Feedback\n\n"
        f"- **Query:** {candidate.query}\n"
        f"- **Category:** {candidate.category}\n"
        f"- **Comment:** {candidate.comment or '(none)'}\n\n"
        "## Original answer\n\n"
        f"{candidate.answer}\n\n"
        "## Live retrieval candidates (re-run at detection time)\n\n"
        f"{candidates_lines}\n\n"
        "_Filed automatically by the Gap Detector — see ADR-0004 and CONTEXT.md § Gap detection._"
    )
