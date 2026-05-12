from pathlib import Path
from backend.app.services.citation_oracle import CitationOracle
from backend.app.services.sutta_relations import SuttaRelations

DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"


def _relations() -> SuttaRelations:
    oracle = CitationOracle(DUMPS_DIR)
    return SuttaRelations(oracle.known_suttas)


def test_get_related_doctrinal_pair():
    r = _relations()
    related = r.get_related("DN 15")
    # DN 15 ↔ MN 38 is a hardcoded doctrinal pair
    assert "MN 38" in related


def test_get_related_structural_adjacency():
    r = _relations()
    related = r.get_related("DN 15")
    neighbors = {f"DN {n}" for n in range(13, 18)} - {"DN 15"}
    assert any(n in related for n in neighbors)


def test_get_related_excludes_self():
    r = _relations()
    assert "DN 15" not in r.get_related("DN 15")


def test_get_related_unknown_sutta():
    r = _relations()
    assert r.get_related("DN 999") == []


def test_get_related_only_returns_known_suttas():
    # All returned IDs must be in the known_suttas set
    oracle = CitationOracle(DUMPS_DIR)
    r = SuttaRelations(oracle.known_suttas)
    for ref in r.get_related("DN 15"):
        assert ref in oracle.known_suttas
