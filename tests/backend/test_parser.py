import pytest
from backend.app.core.indexing import SuttaParser

def test_parser_canonical_id_generation():
    # Mock raw data based on SuttaCentral style
    raw_data = {
        "sutta_id": "DN1",
        "verses": [
            {"number": 1, "pali": "evam me sutaṃ", "english": "Thus have I heard"},
            {"number": 2, "pali": "tada", "english": "Then"}
        ]
    }
    parser = SuttaParser()
    result = parser.parse(raw_data)

    assert len(result) == 2
    assert result[0]['id'] == "DN 1:1"
    assert result[1]['id'] == "DN 1:2"
    assert result[0]['pali'] == "evam me sutaṃ"
    assert result[0]['english'] == "Thus have I heard"

def test_parser_handles_empty_verses():
    raw_data = {"sutta_id": "DN1", "verses": []}
    parser = SuttaParser()
    result = parser.parse(raw_data)
    assert result == []


def test_parser_propagates_commentary_marker():
    raw_data = {
        "sutta_id": "DN1",
        "verses": [
            {"number": 3, "pali": "", "english": "This sutta introduces the Buddha.", "section": "commentary"},
        ],
    }
    parser = SuttaParser()
    result = parser.parse(raw_data)

    assert result[0]["section"] == "commentary"


def test_parser_canon_verse_has_no_marker():
    # Absence of the marker means canon — a canon verse carries no section key (#101).
    raw_data = {
        "sutta_id": "DN1",
        "verses": [
            {"number": 3, "pali": "", "english": "This sutta introduces the Buddha.", "section": "commentary"},
            {"number": 4, "pali": "evam", "english": "Thus have I heard"},
        ],
    }
    parser = SuttaParser()
    result = parser.parse(raw_data)

    assert "section" not in result[1]


def test_parser_canon_when_marker_absent():
    # Pre-marker dumps stay valid: verses without the key parse as all-canon.
    raw_data = {
        "sutta_id": "DN1",
        "verses": [{"number": 1, "pali": "evam", "english": "Thus have I heard"}],
    }
    parser = SuttaParser()
    result = parser.parse(raw_data)
    assert "section" not in result[0]
