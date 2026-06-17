import json
import re
from pathlib import Path


class CitationOracle:
    """
    Verifies that LLM-generated citations refer to real suttas and verses
    in the local SuttaCentral dump index.
    """

    _ID_PARSE_RE = re.compile(r"^([A-Z]+)\s+([\d.]+):(\d+)$")
    _SUTTA_PARSE_RE = re.compile(r"^([A-Za-z]+)([\d.]+)$")

    def __init__(self, dumps_dir: Path):
        # registry["DN 15"] = {1, 2, 3, ...}
        self.registry: dict[str, set[int]] = {}
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

    def _parse_citation(self, citation: str) -> tuple[str, int] | None:
        """Parse 'DN 15:3' → ('DN 15', 3). Returns None if malformed."""
        m = self._ID_PARSE_RE.match(citation.strip())
        if not m:
            return None
        sutta_id = f"{m.group(1)} {m.group(2)}"
        return sutta_id, int(m.group(3))

    def citation_in_canon(self, citation: str) -> bool:
        """True if the citation refers to a sutta+verse that exists in the index."""
        parsed = self._parse_citation(citation)
        if parsed is None:
            return False
        sutta_id, verse = parsed
        return verse in self.registry.get(sutta_id, set())

    @property
    def known_suttas(self) -> set[str]:
        return set(self.registry.keys())
