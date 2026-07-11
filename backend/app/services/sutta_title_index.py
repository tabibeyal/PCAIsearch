from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from backend.app.core.tokenizer import tokenize


_CHAPTER_HEADER_RE = re.compile(r"^\d+\.\s")


class SuttaTitleIndex:
    """BM25 index over sutta titles for canonical-source retrieval."""

    def __init__(self, entries: list[dict]):
        self._sutta_ids = [e["sutta_id"] for e in entries]
        self._entries = {e["sutta_id"]: e for e in entries}
        corpus = [
            tokenize(f"{e['title_pali']} {e['title_english']} {e.get('body_text', '')}")
            for e in entries
        ]
        self._bm25 = BM25Okapi(corpus)

    def get_title_parts(self, sutta_id: str) -> tuple[str, str] | None:
        entry = self._entries.get(sutta_id)
        if entry is None:
            return None
        pali = entry["title_pali"]
        english = entry["title_english"]
        v3 = entry.get("v3_english", "")
        if _CHAPTER_HEADER_RE.match(english) and v3:
            english = v3
        return pali, english

    def get_title_text(self, sutta_id: str) -> str:
        parts = self.get_title_parts(sutta_id)
        if parts is None:
            return ""
        pali, english = parts
        return f"{pali} {english}"

    def search(self, query: str, top_n: int = 5) -> list[tuple[str, float]]:
        tokens = tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self._sutta_ids, scores.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(sutta_id, score) for sutta_id, score in ranked[:top_n] if score > 0]

    @classmethod
    def from_directory(cls, dumps_dir: Path) -> "SuttaTitleIndex":
        entries = []
        for path in sorted(Path(dumps_dir).glob("*.json")):
            try:
                data = json.loads(path.read_text())
                verses = data.get("verses", [])
                title_verse = next((v for v in verses if v.get("number") == 2), None)
                if title_verse:
                    v3_verse = next((v for v in verses if v.get("number") == 3), None)
                    body_text = " ".join(
                        v.get("english", "")
                        for v in verses
                        if 3 <= v.get("number", 0) <= 15
                    )
                    entries.append({
                        "sutta_id": data["sutta_id"],
                        "title_pali": title_verse.get("pali", ""),
                        "title_english": title_verse.get("english", ""),
                        "v3_english": v3_verse.get("english", "") if v3_verse else "",
                        "body_text": body_text,
                    })
            except Exception:
                continue
        return cls(entries)
