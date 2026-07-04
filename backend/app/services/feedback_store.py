import logging
import sqlite3
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from backend.app.services.gap_detector import FeedbackCandidate
from backend.app.services.supabase_client import SupabaseRestClient

logger = logging.getLogger(__name__)


class FeedbackWriter(Protocol):
    def insert(self, query: str, answer: str, rating: str, category: str | None, comment: str | None) -> None:
        ...


class SupabaseFeedbackStore:
    """Feedback storage backed by Supabase's `feedback` table. Serves both the
    live write path (`insert`) and the Gap Detector's scan/mark path
    (`fetch_down_votes`/`mark_handled`, see gap_detector.FeedbackStore)."""

    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    def insert(self, query: str, answer: str, rating: str, category: str | None, comment: str | None) -> None:
        # created_at is filled by the DB default (now()), so it is omitted here.
        payload = {"query": query, "answer": answer, "rating": rating, "category": category, "comment": comment}
        try:
            self._client.post("feedback", payload)
        except urllib.error.HTTPError as exc:
            logger.error(
                "Supabase feedback insert failed: %s — response body: %s",
                exc,
                exc.read().decode(errors="replace"),
            )
            raise
        except urllib.error.URLError as exc:
            logger.error("Supabase feedback insert failed (network): %s", exc)
            raise

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


class SQLiteFeedbackStore:
    """Feedback storage backed by a local SQLite file. Local-dev fallback for
    when Supabase credentials aren't configured. Only implements the live
    write path — nothing (including scripts/run_gap_detector.py) ever asks
    SQLite to do the Gap Detector's scan/mark work."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        con = sqlite3.connect(self._db_path)
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    query      TEXT NOT NULL,
                    answer     TEXT NOT NULL,
                    rating     TEXT NOT NULL,
                    category   TEXT,
                    comment    TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            con.commit()
        finally:
            con.close()

    def insert(self, query: str, answer: str, rating: str, category: str | None, comment: str | None) -> None:
        con = sqlite3.connect(self._db_path)
        try:
            con.execute(
                "INSERT INTO feedback (query, answer, rating, category, comment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (query, answer, rating, category, comment, datetime.now(timezone.utc).isoformat()),
            )
            con.commit()
        finally:
            con.close()
