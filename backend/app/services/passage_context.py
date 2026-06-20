import json
import re
from pathlib import Path

# A cited verse this long already reads as a full paragraph — showing neighbors
# would just bloat the source card.
_LONG_ENOUGH = 180
# Keep widening the window until the passage reaches this many characters...
_TARGET_CHARS = 280
# ...but never pull more than this many verses on each side.
# ponytail: fixed window cap, widen if readers still report missing context.
_MAX_EACH_SIDE = 2
# Verses 1 and 2 are the generated header and title, not prose — never neighbors.
_META_NUMBERS = {1, 2}

_ID_RE = re.compile(r"^([A-Z]+)\s+([\d.]+):(\d+)$")
_SUTTA_RE = re.compile(r"^([A-Za-z]+)([\d.]+)$")


class PassageStore:
    """
    Holds every sutta's verse text so a one-line citation can be shown together
    with the surrounding passage. Thanissaro's text is chunked one paragraph per
    verse, and many paragraphs (refrains, dialogue turns) are a single short line.
    """

    def __init__(self) -> None:
        # sutta_id -> ordered list of (verse_number, english)
        self._verses: dict[str, list[tuple[int, str]]] = {}

    @classmethod
    def from_directory(cls, dumps_dir: Path) -> "PassageStore":
        store = cls()
        for path in sorted(dumps_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            m = _SUTTA_RE.match(data.get("sutta_id", ""))
            if not m:
                continue
            sutta_id = f"{m.group(1).upper()} {m.group(2)}"
            verses = [
                (v["number"], (v.get("english") or "").strip())
                for v in data.get("verses", [])
                if isinstance(v.get("number"), int) and (v.get("english") or "").strip()
            ]
            if verses:
                store._verses[sutta_id] = verses
        return store

    def passage(self, chunk_id: str) -> list[dict] | None:
        """
        Cited verse plus enough neighbors to read as a passage, ordered by verse
        number as a list of {id, english, isMatch}. Returns None when the verse
        is unknown, already long enough to stand alone, or has no usable neighbors.
        """
        m = _ID_RE.match(chunk_id.strip())
        if not m:
            return None
        sutta_id = f"{m.group(1)} {m.group(2)}"
        number = int(m.group(3))
        verses = self._verses.get(sutta_id)
        if not verses:
            return None

        idx = next((i for i, (n, _) in enumerate(verses) if n == number), None)
        if idx is None or len(verses[idx][1]) >= _LONG_ENOUGH:
            return None

        chosen = {idx}
        total = len(verses[idx][1])
        for step in range(1, _MAX_EACH_SIDE + 1):
            for j in (idx - step, idx + step):
                if 0 <= j < len(verses) and verses[j][0] not in _META_NUMBERS:
                    chosen.add(j)
                    total += len(verses[j][1])
            if total >= _TARGET_CHARS:
                break
        if len(chosen) == 1:
            return None

        return [
            {
                "id": f"{sutta_id}:{verses[i][0]}",
                "english": verses[i][1],
                "isMatch": i == idx,
            }
            for i in sorted(chosen)
        ]
