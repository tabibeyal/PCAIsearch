import re
from typing import Dict, List, Set

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

_SUTTA_ID_RE = re.compile(r"^([A-Z]+) (\d+)$")


class SuttaRelations:
    """
    Returns canonically related sutta IDs for cross-reference expansion.
    Combines hardcoded doctrinal pairs with structural adjacency (±2 within nikaya).
    """

    def __init__(self, known_suttas: Set[str]):
        self._known = frozenset(known_suttas)

    def get_related(self, sutta_id: str) -> List[str]:
        related: Set[str] = set()

        for ref in _DOCTRINAL_PAIRS.get(sutta_id, []):
            if ref in self._known:
                related.add(ref)

        m = _SUTTA_ID_RE.match(sutta_id)
        if m:
            nikaya, num = m.group(1), int(m.group(2))
            for delta in (-2, -1, 1, 2):
                neighbor = f"{nikaya} {num + delta}"
                if neighbor in self._known:
                    related.add(neighbor)

        related.discard(sutta_id)
        return sorted(related)
