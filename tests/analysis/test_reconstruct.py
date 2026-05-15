import pytest

from analysis.parallels.reconstruct import reconstruct_raw


SUTTA_DATA = {
    "sutta_id": "MN 1",
    "verses": [
        {"number": 1, "pali": "evaṃ me sutaṃ ekaṃ samayaṃ"},
        {"number": 2, "pali": "bhagavā viharati"},
    ],
}


def test_reconstruct_single_verse_span():
    # "evaṃ me sutaṃ" = 13 codepoints (e,v,a,ṃ, ,m,e, ,s,u,t,a,ṃ)
    raw = reconstruct_raw(SUTTA_DATA, verse_number=1, char_offset=0, char_length=13)
    assert raw == "evaṃ me sutaṃ"


def test_reconstruct_from_middle_of_verse():
    # "me" starts at char 5 (after "evaṃ "); "me sutaṃ ekaṃ" = 13 codepoints
    raw = reconstruct_raw(SUTTA_DATA, verse_number=1, char_offset=5, char_length=13)
    assert raw == "me sutaṃ ekaṃ"


def test_reconstruct_full_verse():
    raw = reconstruct_raw(SUTTA_DATA, verse_number=2, char_offset=0, char_length=16)
    assert raw == "bhagavā viharati"


def test_reconstruct_invalid_verse_returns_empty():
    raw = reconstruct_raw(SUTTA_DATA, verse_number=99, char_offset=0, char_length=5)
    assert raw == ""
