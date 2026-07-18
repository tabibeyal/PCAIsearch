import json
from pathlib import Path
from backend.app.services.citation_oracle import CitationOracle

DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"


def _oracle() -> CitationOracle:
    return CitationOracle(DUMPS_DIR)


def _write_mixed_sutta(tmp_path) -> Path:
    """One sutta carrying a commentary verse and a canon verse, so a
    commentary citation can be told apart from a canon citation in the
    same sutta (#101 section marker, #103 registry exclusion)."""
    verses = [
        {"number": 1, "english": "intro paragraph", "section": "commentary"},
        {"number": 2, "english": "Thus have I heard the Blessed One was dwelling"},
    ]
    (tmp_path / "mn99.json").write_text(
        json.dumps({"sutta_id": "mn99", "verses": verses}), encoding="utf-8"
    )
    return tmp_path


def test_known_suttas_loaded():
    o = _oracle()
    assert len(o.known_suttas) > 0
    assert "DN 15" in o.known_suttas
    assert "MN 10" in o.known_suttas
    assert "AN 10.101" in o.known_suttas  # dotted ID — previously missed by old regex


def test_citation_in_canon():
    o = _oracle()
    assert o.citation_in_canon("DN 15:1")
    assert not o.citation_in_canon("DN 999:1")
    assert not o.citation_in_canon("DN 15:999999")


def test_registry_rejects_commentary_verse(tmp_path):
    # A commentary verse is never citable as canon, even though it shares the
    # sutta's numbering (#103).
    o = CitationOracle(_write_mixed_sutta(tmp_path))
    assert not o.citation_in_canon("MN 99:1")


def test_registry_keeps_canon_verse_alongside_commentary(tmp_path):
    # Canon verses from the same sutta stay valid — commentary is excluded,
    # not the whole sutta (#103).
    o = CitationOracle(_write_mixed_sutta(tmp_path))
    assert o.citation_in_canon("MN 99:2")
