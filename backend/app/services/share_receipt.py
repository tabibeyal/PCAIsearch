from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


_STORAGE_FIELDS = ("id", "english", "title", "title_pali", "title_english", "passage")
_HASH_FIELDS = ("id", "english", "title", "title_pali", "title_english", "passage")


def sanitize_context(context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip context entries down to the known SearchResult shape, so nothing outside
    the signed payload can be smuggled into permanent storage."""
    return [{field: c.get(field) for field in _STORAGE_FIELDS} for c in context]


def _canonical_payload(query: str, answer: str, context: list[dict[str, Any]]) -> bytes:
    """Hash only the fields rendered on the share page, via a list kept separate
    from `_STORAGE_FIELDS` so a future stored-but-unrendered field doesn't change
    existing receipts."""
    canonical_context = [{field: c.get(field, "") for field in _HASH_FIELDS} for c in context]
    return json.dumps(
        {"query": query, "answer": answer, "context": canonical_context},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


def generate_receipt(query: str, answer: str, context: list[dict[str, Any]], secret: str) -> str:
    payload = _canonical_payload(query, answer, context)
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_receipt(
    query: str, answer: str, context: list[dict[str, Any]], receipt: str, secret: str
) -> bool:
    expected = generate_receipt(query, answer, context, secret)
    return hmac.compare_digest(expected, receipt)
