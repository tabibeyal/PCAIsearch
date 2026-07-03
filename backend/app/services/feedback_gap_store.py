from typing import Any

from backend.app.services.gap_detector import FeedbackCandidate
from backend.app.services.supabase_client import SupabaseRestClient


class SupabaseFeedbackStore:
    """FeedbackStore backed by the Supabase `feedback` table. Only filters the
    mechanical criteria (down-voted, not yet handled) — GapDetector decides which
    categories qualify as retrieval gaps."""

    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    def fetch_down_votes(self) -> list[FeedbackCandidate]:
        rows: list[dict[str, Any]] = self._client.get(
            "feedback", "rating=eq.down&gap_issue_url=is.null&order=created_at.desc"
        )
        return [
            FeedbackCandidate(
                id=row["id"],
                query=row["query"],
                answer=row["answer"],
                category=row.get("category"),
                comment=row.get("comment"),
            )
            for row in rows
        ]

    def mark_handled(self, feedback_id: Any, issue_url: str) -> None:
        self._client.patch("feedback", f"id=eq.{feedback_id}", {"gap_issue_url": issue_url})
