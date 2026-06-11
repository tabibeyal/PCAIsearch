from pathlib import Path
from backend.app.services.citation_oracle import CitationOracle

DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"


def _oracle() -> CitationOracle:
    return CitationOracle(DUMPS_DIR)


def test_known_suttas_loaded():
    o = _oracle()
    assert len(o.known_suttas) > 0
    assert "DN 15" in o.known_suttas
    assert "MN 10" in o.known_suttas
    assert "AN 10.101" in o.known_suttas  # dotted ID — previously missed by old regex


def test_sutta_exists():
    o = _oracle()
    assert o.sutta_exists("DN 15")
    assert not o.sutta_exists("DN 999")
    assert not o.sutta_exists("XN 1")


def test_verse_exists():
    o = _oracle()
    assert o.verse_exists("DN 15", 1)
    assert not o.verse_exists("DN 15", 999999)
    assert not o.verse_exists("DN 999", 1)


def test_parse_citation_valid():
    o = _oracle()
    assert o.parse_citation("DN 15:3") == ("DN 15", 3)
    assert o.parse_citation("MN 109:1") == ("MN 109", 1)
    assert o.parse_citation("AN 10.101:3") == ("AN 10.101", 3)  # dotted ID


def test_parse_citation_invalid():
    o = _oracle()
    assert o.parse_citation("not a citation") is None
    assert o.parse_citation("DN15:3") is None  # missing space
    assert o.parse_citation("") is None


def test_citation_in_canon():
    o = _oracle()
    assert o.citation_in_canon("DN 15:1")
    assert not o.citation_in_canon("DN 999:1")
    assert not o.citation_in_canon("DN 15:999999")
