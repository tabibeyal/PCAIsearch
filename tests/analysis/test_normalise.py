import unicodedata

import pytest

from analysis.parallels.normalise import normalise


def test_nfc_normalisation():
    # NFD form of ā (a + combining macron) should equal NFC ā
    nfd = unicodedata.normalize("NFD", "ānāpānasati")
    assert normalise(nfd) == normalise("ānāpānasati")


def test_lowercase():
    assert normalise("Evaṃ Me Sutaṃ") == normalise("evaṃ me sutaṃ")


def test_punctuation_stripped():
    assert normalise("evaṃ, me sutaṃ.") == normalise("evaṃ me sutaṃ")


def test_whitespace_collapsed():
    assert normalise("evaṃ  me\tsutaṃ") == "evaṃ me sutaṃ"


def test_niggahita_canonical_m_with_dot_below():
    # ṃ (U+1E43) and ṁ (U+1E41) should normalise to same form
    assert normalise("evaṃ") == normalise("evaṁ")


def test_niggahita_canonical_form_is_dot_below():
    # ṁ (overdot) -> ṃ (underdot)
    assert normalise("evaṁ") == "evaṃ"


def test_empty_string():
    assert normalise("") == ""


def test_already_normalised():
    s = "evaṃ me sutaṃ"
    assert normalise(s) == s
