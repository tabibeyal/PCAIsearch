import sqlite3
from typing import Any, Dict, List, Optional


def list_spans(
    conn: sqlite3.Connection,
    min_occurrences: int = 1,
    min_tokens: int = 1,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM span WHERE occurrence_count >= ? AND token_count >= ? "
        "ORDER BY occurrence_count DESC, token_count DESC LIMIT ?",
        (min_occurrences, min_tokens, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def show_span(
    conn: sqlite3.Connection,
    span_id: str,
) -> Optional[Dict[str, Any]]:
    span = conn.execute("SELECT * FROM span WHERE id = ?", (span_id,)).fetchone()
    if span is None:
        return None
    occs = conn.execute(
        "SELECT * FROM occurrence WHERE span_id = ? ORDER BY sutta_id, verse_number",
        (span_id,),
    ).fetchall()
    return {"span": dict(span), "occurrences": [dict(o) for o in occs]}


def spans_in_sutta(
    conn: sqlite3.Connection,
    sutta_id: str,
    min_tokens: int = 1,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT s.* FROM span s "
        "JOIN occurrence o ON o.span_id = s.id "
        "WHERE o.sutta_id = ? AND s.token_count >= ? "
        "ORDER BY s.occurrence_count DESC",
        (sutta_id, min_tokens),
    ).fetchall()
    return [dict(r) for r in rows]


def top_formulas(
    conn: sqlite3.Connection,
    by: str = "occurrences",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    order = "occurrence_count DESC" if by == "occurrences" else "token_count DESC"
    rows = conn.execute(
        f"SELECT * FROM span ORDER BY {order} LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    total_spans = conn.execute("SELECT COUNT(*) FROM span").fetchone()[0]
    total_occs = conn.execute("SELECT COUNT(*) FROM occurrence").fetchone()[0]
    version_row = conn.execute(
        "SELECT detector_version FROM span LIMIT 1"
    ).fetchone()
    return {
        "total_spans": total_spans,
        "total_occurrences": total_occs,
        "detector_version": version_row[0] if version_row else None,
    }
