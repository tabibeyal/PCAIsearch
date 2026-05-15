import pytest

from analysis.parallels.tokenise import tokenise_sutta


# Each verse is {"number": int, "pali": str}
def _verses(*pali_strings):
    return [{"number": i + 1, "pali": s} for i, s in enumerate(pali_strings)]


def test_single_verse_tokens():
    verses = _verses("evaṃ me sutaṃ")
    tokens, offsets = tokenise_sutta(verses)
    assert tokens == ["evaṃ", "me", "sutaṃ"]


def test_multi_verse_tokens_concatenated():
    verses = _verses("evaṃ me", "sutaṃ ekaṃ")
    tokens, offsets = tokenise_sutta(verses)
    assert tokens == ["evaṃ", "me", "sutaṃ", "ekaṃ"]


def test_offset_table_length_matches_tokens():
    verses = _verses("evaṃ me sutaṃ")
    tokens, offsets = tokenise_sutta(verses)
    assert len(offsets) == len(tokens)


def test_offset_verse_number():
    verses = _verses("evaṃ me", "sutaṃ ekaṃ")
    tokens, offsets = tokenise_sutta(verses)
    # first two tokens come from verse 1
    assert offsets[0][0] == 1
    assert offsets[1][0] == 1
    # last two from verse 2
    assert offsets[2][0] == 2
    assert offsets[3][0] == 2


def test_offset_char_offset_first_token():
    verses = _verses("evaṃ me sutaṃ")
    tokens, offsets = tokenise_sutta(verses)
    # "evaṃ" starts at char 0 in verse 1
    assert offsets[0] == (1, 0)


def test_offset_char_offset_second_token():
    verses = _verses("evaṃ me sutaṃ")
    tokens, offsets = tokenise_sutta(verses)
    # "me" starts after "evaṃ " — evaṃ is 4 chars + 1 space = 5
    assert offsets[1] == (1, 5)


def test_empty_verse_skipped():
    verses = _verses("evaṃ", "", "sutaṃ")
    tokens, offsets = tokenise_sutta(verses)
    assert tokens == ["evaṃ", "sutaṃ"]


def test_punctuation_stripped_in_tokens():
    verses = _verses("evaṃ, me sutaṃ.")
    tokens, offsets = tokenise_sutta(verses)
    assert tokens == ["evaṃ", "me", "sutaṃ"]


def test_empty_corpus():
    tokens, offsets = tokenise_sutta([])
    assert tokens == []
    assert offsets == []
