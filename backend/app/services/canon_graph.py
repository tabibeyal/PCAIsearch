import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Well-known doctrinal cross-references in the Pali Canon
_DOCTRINAL_PAIRS: Dict[str, List[str]] = {
    "DN 15": ["MN 38"],          # Mahānidāna ↔ Mahātaṇhāsankhaya (Dependent Origination)
    "MN 38": ["DN 15"],
    "DN 22": ["MN 10"],          # Mahāsatipaṭṭhāna ↔ Satipaṭṭhāna
    "MN 10": ["DN 22"],
    "MN 22": ["MN 44"],          # Alagaddūpama ↔ Cūḷavedalla (clinging / vedanā)
    "MN 44": ["MN 22", "MN 109"],
    "MN 109": ["MN 44"],
    "MN 36": ["MN 85", "MN 100"],  # Three accounts of the Bodhisatta's awakening
    "MN 85": ["MN 36", "MN 100"],
    "MN 100": ["MN 36", "MN 85"],
    "MN 63": ["MN 72"],          # Cūḷamāluṅkya ↔ Aggivacchagotta (unanswered questions)
    "MN 72": ["MN 63"],
    "MN 117": ["MN 44"],         # Mahācattārīsaka (right concentration) ↔ vedanā
    "DN 2": ["MN 51", "MN 76"],  # Sāmaññaphala ↔ Kandaraka ↔ Sandaka (fruits of recluseship)
    "MN 51": ["DN 2"],
    "MN 76": ["DN 2"],
}


class CanonGraph:
    """
    Canonical sutta index built from local SuttaCentral dump files.

    Two services:
    - Citation oracle: verify that a citation refers to a real sutta+verse
    - Cross-reference expansion: given a sutta ID, return canonically related ones
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
        """True if the citation refers to a sutta+verse that exists in our index."""
        parsed = self.parse_citation(citation)
        if parsed is None:
            return False
        sutta_id, verse = parsed
        return self.verse_exists(sutta_id, verse)

    def get_related(self, sutta_id: str) -> List[str]:
        """
        Return related sutta IDs for cross-reference expansion.
        Combines hardcoded doctrinal pairs with structural adjacency (±2 within nikaya).
        """
        related: Set[str] = set()

        for ref in _DOCTRINAL_PAIRS.get(sutta_id, []):
            if ref in self.registry:
                related.add(ref)

        m = re.match(r"^([A-Z]+) (\d+)$", sutta_id)
        if m:
            nikaya, num = m.group(1), int(m.group(2))
            for delta in (-2, -1, 1, 2):
                neighbor = f"{nikaya} {num + delta}"
                if neighbor in self.registry:
                    related.add(neighbor)

        related.discard(sutta_id)
        return sorted(related)

    @property
    def known_suttas(self) -> Set[str]:
        return set(self.registry.keys())
