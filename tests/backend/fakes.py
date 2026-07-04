from datetime import datetime, timezone
from typing import Any


class FakeSupabaseRestClient:
    """Behaves like the real Supabase PostgREST API against an in-memory
    table, instead of just recording calls — so tests can assert on actual
    behavior rather than on the shape of the request made."""

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}

    def post(self, table: str, payload: dict[str, Any]) -> None:
        rows = self._tables.setdefault(table, [])
        row = dict(payload)
        row.setdefault("id", len(rows) + 1)
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        rows.append(row)

    def get(self, table: str, query: str) -> list[dict[str, Any]]:
        rows = list(self._tables.get(table, []))
        if not query:
            return rows
        conditions: list[tuple[str, str | None]] = []
        order_field: str | None = None
        order_desc = False
        select_fields: list[str] | None = None
        for part in query.split("&"):
            key, _, value = part.partition("=")
            if key == "order":
                field, _, direction = value.partition(".")
                order_field, order_desc = field, direction == "desc"
            elif key == "select":
                select_fields = value.split(",")
            elif value == "is.null":
                conditions.append((key, None))
            elif value.startswith("eq."):
                conditions.append((key, value[len("eq."):]))
        rows = [r for r in rows if _matches(r, conditions)]
        if order_field:
            rows.sort(key=lambda r: r.get(order_field), reverse=order_desc)
        if select_fields:
            rows = [{f: r.get(f) for f in select_fields} for r in rows]
        return rows

    def patch(self, table: str, query: str, payload: dict[str, Any]) -> None:
        conditions = [
            (key, value[len("eq."):])
            for key, _, value in (part.partition("=") for part in query.split("&"))
            if value.startswith("eq.")
        ]
        for row in self._tables.get(table, []):
            if _matches(row, conditions):
                row.update(payload)


def _matches(row: dict[str, Any], conditions: list[tuple[str, str | None]]) -> bool:
    for field, expected in conditions:
        if expected is None:
            if row.get(field) is not None:
                return False
        elif str(row.get(field)) != expected:
            return False
    return True
