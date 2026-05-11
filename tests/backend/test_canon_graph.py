from pathlib import Path
from backend.app.services.canon_graph import CanonGraph

DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"


def _graph() -> CanonGraph:
    return CanonGraph(DUMPS_DIR)


def test_known_suttas_loaded():
    g = _graph()
    assert len(g.known_suttas) > 0
    assert "DN 15" in g.known_suttas
    assert "MN 10" in g.known_suttas


def test_sutta_exists():
    g = _graph()
    assert g.sutta_exists("DN 15")
    assert not g.sutta_exists("DN 999")
    assert not g.sutta_exists("XN 1")


def test_verse_exists():
    g = _graph()
    assert g.verse_exists("DN 15", 1)
    assert not g.verse_exists("DN 15", 999999)
    assert not g.verse_exists("DN 999", 1)


def test_parse_citation_valid():
    g = _graph()
    assert g.parse_citation("DN 15:3") == ("DN 15", 3)
    assert g.parse_citation("MN 109:1") == ("MN 109", 1)


def test_parse_citation_invalid():
    g = _graph()
    assert g.parse_citation("not a citation") is None
    assert g.parse_citation("DN15:3") is None  # missing space
    assert g.parse_citation("") is None


def test_citation_in_canon():
    g = _graph()
    assert g.citation_in_canon("DN 15:1")
    assert not g.citation_in_canon("DN 999:1")
    assert not g.citation_in_canon("DN 15:999999")


def test_get_related_doctrinal_pair():
    g = _graph()
    related = g.get_related("DN 15")
    # DN 15 ↔ MN 38 is a hardcoded doctrinal pair
    assert "MN 38" in related


def test_get_related_structural_adjacency():
    g = _graph()
    related = g.get_related("DN 15")
    # Structural neighbours should appear if they're in the index
    neighbors = {f"DN {n}" for n in range(13, 18)} - {"DN 15"}
    assert any(n in related for n in neighbors)


def test_get_related_excludes_self():
    g = _graph()
    related = g.get_related("DN 15")
    assert "DN 15" not in related


def test_get_related_unknown_sutta():
    g = _graph()
    assert g.get_related("DN 999") == []
