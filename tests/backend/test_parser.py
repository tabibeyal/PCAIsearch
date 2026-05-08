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
