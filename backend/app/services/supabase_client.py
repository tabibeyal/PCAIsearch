import json
import logging
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


class SupabaseRestClient:
    """Thin wrapper around the Supabase PostgREST API (`/rest/v1/<table>`).

    Query filters are passed as structured kwargs, not a pre-assembled string,
    so the client controls the PostgREST operators/separators and URL-encodes
    every caller-supplied value. A value containing `&` or `=` can never inject
    an extra filter — it is encoded as part of the existing filter's value.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def post(self, table: str, payload: dict[str, Any], *, error_label: str) -> None:
        req = urllib.request.Request(
            f"{self._base_url}/rest/v1/{table}",
            data=json.dumps(payload).encode(),
            headers=self._headers(prefer="return=minimal"),
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as exc:
            logger.error(
                "Supabase %s insert failed: %s — response body: %s",
                error_label,
                exc,
                exc.read().decode(errors="replace"),
            )
            raise
        except urllib.error.URLError as exc:
            logger.error("Supabase %s insert failed (network): %s", error_label, exc)
            raise

    def get(
        self,
        table: str,
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
        select: list[str] | None = None,
        order: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        query = self._build_query(eq=eq, is_null=is_null, select=select, order=order)
        url = f"{self._base_url}/rest/v1/{table}?{query}" if query else f"{self._base_url}/rest/v1/{table}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def patch(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        eq: dict[str, Any] | None = None,
        is_null: list[str] | None = None,
    ) -> None:
        query = self._build_query(eq=eq, is_null=is_null)
        req = urllib.request.Request(
            f"{self._base_url}/rest/v1/{table}?{query}",
            data=json.dumps(payload).encode(),
            headers=self._headers(prefer="return=minimal"),
            method="PATCH",
        )
        urllib.request.urlopen(req)

    def _build_query(
        self,
        *,
        eq: dict[str, Any] | None,
        is_null: list[str] | None,
        select: list[str] | None = None,
        order: tuple[str, str] | None = None,
    ) -> str:
        parts: list[str] = []
        if select:
            parts.append("select=" + ",".join(quote(f, safe="") for f in select))
        if eq:
            for col, val in eq.items():
                parts.append(f"{quote(col, safe='')}=eq.{quote(str(val), safe='')}")
        if is_null:
            for col in is_null:
                parts.append(f"{quote(col, safe='')}=is.null")
        if order:
            field, direction = order
            parts.append(f"order={quote(field, safe='')}.{quote(direction, safe='')}")
        return "&".join(parts)