import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from backend.app.core.indexing import SuttaParser


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z]+", text.lower())


class BM25Retriever:
    """In-memory BM25 index over English verse text for exact-match retrieval."""

    def __init__(self, verses: List[Dict[str, Any]]):
        if not verses:
            raise ValueError("BM25Retriever requires at least one verse")
        self._verses = verses
        corpus = [_tokenize(v.get("english", "")) for v in verses]
        self._bm25 = BM25Okapi(corpus)

    def retrieve(self, query: str, top_k: int, nikayas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        pairs = zip(self._verses, scores.tolist())
        if nikayas:
            allowed = set(nikayas)
            pairs = ((v, s) for v, s in pairs if v.get("nikaya") in allowed)
        ranked = sorted(pairs, key=lambda x: x[1], reverse=True)
        return [
            {**verse, "bm25_score": score}
            for verse, score in ranked[:top_k]
            if score > 0
        ]

    @classmethod
    def from_directory(cls, dumps_dir: Path) -> "BM25Retriever":
        parser = SuttaParser()
        verses: List[Dict[str, Any]] = []
        for path in sorted(Path(dumps_dir).glob("*.json")):
            try:
                data = json.loads(path.read_text())
                for chunk in parser.parse(data):
                    if chunk.get("english", "").strip():
                        verses.append(chunk)
            except Exception:
                continue
        if not verses:
            raise ValueError(f"No verses found in {dumps_dir}")
        return cls(verses)
