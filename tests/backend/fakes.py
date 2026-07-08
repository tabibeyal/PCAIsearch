from datetime import datetime, timezone
from typing import Any


class FakeSupabaseRestClient:
    """Behaves like the real Supabase PostgREST API against an in-memory
    table, instead of just recording calls — so tests can assert on actual
    behavior rather than on the shape of the request made.

    Mirrors SupabaseRestClient's structured-filter signature: callers pass
    `eq`/`is_null`/`select`/`order` kwargs, never a pre-assembled filter
    string, so the fake filters in-memory the same way the real client
    builds an encoded query string.
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}

    def post(self, table: str, payload: dict[str, Any]) -> None:
        rows = self._tables.setdefault(table, [])
        row = dict(payload)
        row.setdefault("id", len(rows) + 1)
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        rows.append(row)

    def get(
        self,
        table: str,
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
        select: list[str] | None = None,
        order: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        rows = [r for r in self._tables.get(table, []) if _matches(r, eq, is_null)]
        if order:
            field, direction = order
            rows.sort(key=lambda r: r.get(field), reverse=direction == "desc")
        if select:
            rows = [{f: r.get(f) for f in select} for r in rows]
        return rows

    def patch(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
    ) -> None:
        for row in self._tables.get(table, []):
            if _matches(row, eq, is_null):
                row.update(payload)


def _matches(
    row: dict[str, Any], eq: dict[str, Any] | None, is_null: list[str] | None
) -> bool:
    if eq:
        if any(str(row.get(col)) != str(val) for col, val in eq.items()):
            return False
    if is_null:
        if any(row.get(col) is not None for col in is_null):
            return False
    return True