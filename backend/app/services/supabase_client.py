import json
import urllib.error
import urllib.request
from typing import Any


class SupabaseRestClient:
    """Thin wrapper around the Supabase PostgREST API (`/rest/v1/<table>`)."""

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

    def post(self, table: str, payload: dict[str, Any]) -> None:
        req = urllib.request.Request(
            f"{self._base_url}/rest/v1/{table}",
            data=json.dumps(payload).encode(),
            headers=self._headers(prefer="return=minimal"),
            method="POST",
        )
        urllib.request.urlopen(req)

    def get(self, table: str, query: str) -> list[dict[str, Any]]:
        req = urllib.request.Request(
            f"{self._base_url}/rest/v1/{table}?{query}",
            headers=self._headers(),
            method="GET",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def patch(self, table: str, query: str, payload: dict[str, Any]) -> None:
        req = urllib.request.Request(
            f"{self._base_url}/rest/v1/{table}?{query}",
            data=json.dumps(payload).encode(),
            headers=self._headers(prefer="return=minimal"),
            method="PATCH",
        )
        urllib.request.urlopen(req)
