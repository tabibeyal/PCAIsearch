import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from backend.app.services.supabase_client import SupabaseRestClient


class ShareStore(Protocol):
    def save(self, share_id: str, query: str, answer: str, context: list[dict]) -> None:
        ...

    def fetch(self, share_id: str) -> dict | None:
        ...


class SupabaseShareStore:
    """Shared-answer snapshot storage backed by Supabase's `shared_answers`
    table (ADR-0005)."""

    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    def save(self, share_id: str, query: str, answer: str, context: list[dict]) -> None:
        payload = {"id": share_id, "query": query, "answer": answer, "context": context}
        self._client.post("shared_answers", payload, error_label="share")

    def fetch(self, share_id: str) -> dict | None:
        rows = self._client.get(
            "shared_answers", eq={"id": share_id}, select=["query", "answer", "context"]
        )
        if not rows:
            return None
        row = rows[0]
        return {"query": row["query"], "answer": row["answer"], "context": row["context"]}


class SQLiteShareStore:
    """Shared-answer snapshot storage backed by a local SQLite file.
    Local-dev fallback for when Supabase credentials aren't configured."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        con = sqlite3.connect(self._db_path)
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS shared_answers (
                    id         TEXT PRIMARY KEY,
                    query      TEXT NOT NULL,
                    answer     TEXT NOT NULL,
                    context    TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            con.commit()
        finally:
            con.close()

    def save(self, share_id: str, query: str, answer: str, context: list[dict]) -> None:
        con = sqlite3.connect(self._db_path)
        try:
            con.execute(
                "INSERT INTO shared_answers (id, query, answer, context, created_at) VALUES (?, ?, ?, ?, ?)",
                (share_id, query, answer, json.dumps(context), datetime.now(timezone.utc).isoformat()),
            )
            con.commit()
        finally:
            con.close()

    def fetch(self, share_id: str) -> dict | None:
        con = sqlite3.connect(self._db_path)
        try:
            row = con.execute(
                "SELECT query, answer, context FROM shared_answers WHERE id = ?", (share_id,)
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        query, answer, context_json = row
        return {"query": query, "answer": answer, "context": json.loads(context_json)}
