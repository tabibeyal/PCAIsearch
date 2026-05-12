import json
import re
from pathlib import Path
from typing import Dict, Optional, Set, Tuple


class CitationOracle:
    """
    Verifies that LLM-generated citations refer to real suttas and verses
    in the local SuttaCentral dump index.
    """

    _ID_PARSE_RE = re.compile(r"^([A-Z]+)\s+(\d+):(\d+)$")
    _SUTTA_PARSE_RE = re.compile(r"^([A-Za-z]+)(\d+)$")

    def __init__(self, dumps_dir: Path):
        # registry["DN 15"] = {1, 2, 3, ...}
        self.registry: Dict[str, Set[int]] = {}
        self._load(dumps_dir)

    def _load(self, dumps_dir: Path) -> None:
        for path in sorted(dumps_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            raw_id = data.get("sutta_id", "")
            m = self._SUTTA_PARSE_RE.match(raw_id)
            if not m:
                continue
            sutta_id = f"{m.group(1).upper()} {m.group(2)}"

            verse_numbers = {
                v["number"]
                for v in data.get("verses", [])
                if isinstance(v.get("number"), int)
            }
            if verse_numbers:
                self.registry[sutta_id] = verse_numbers

    def sutta_exists(self, sutta_id: str) -> bool:
        return sutta_id in self.registry

    def verse_exists(self, sutta_id: str, verse: int) -> bool:
        return verse in self.registry.get(sutta_id, set())

    def parse_citation(self, citation: str) -> Optional[Tuple[str, int]]:
        """Parse 'DN 15:3' → ('DN 15', 3). Returns None if malformed."""
        m = self._ID_PARSE_RE.match(citation.strip())
        if not m:
            return None
        sutta_id = f"{m.group(1)} {m.group(2)}"
        return sutta_id, int(m.group(3))

    def citation_in_canon(self, citation: str) -> bool:
        """True if the citation refers to a sutta+verse that exists in the index."""
        parsed = self.parse_citation(citation)
        if parsed is None:
            return False
        sutta_id, verse = parsed
        return self.verse_exists(sutta_id, verse)

    @property
    def known_suttas(self) -> Set[str]:
        return set(self.registry.keys())
