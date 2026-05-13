from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

from rank_bm25 import BM25Okapi


_CHAPTER_HEADER_RE = re.compile(r"^\d+\.\s")


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z]+", text.lower())


class SuttaTitleIndex:
    """BM25 index over sutta titles for canonical-source retrieval."""

    def __init__(self, entries: List[dict]):
        self._sutta_ids = [e["sutta_id"] for e in entries]
        self._title_texts = {
            e["sutta_id"]: self._build_title_text(e)
            for e in entries
        }
        corpus = [
            _tokenize(f"{e['title_pali']} {e['title_english']} {e.get('body_text', '')}")
            for e in entries
        ]
        self._bm25 = BM25Okapi(corpus)

    @staticmethod
    def _build_title_text(entry: dict) -> str:
        pali = entry["title_pali"]
        english = entry["title_english"]
        v3 = entry.get("v3_english", "")
        if _CHAPTER_HEADER_RE.match(english) and v3:
            return f"{pali} {v3}"
        return f"{pali} {english}"

    def get_title_text(self, sutta_id: str) -> str:
        return self._title_texts.get(sutta_id, "")

    def search(self, query: str, top_n: int = 5) -> List[Tuple[str, float]]:
        tokens = _tokenize(query)
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
