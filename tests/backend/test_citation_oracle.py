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


def test_citation_in_canon():
    o = _oracle()
    assert o.citation_in_canon("DN 15:1")
    assert not o.citation_in_canon("DN 999:1")
    assert not o.citation_in_canon("DN 15:999999")
