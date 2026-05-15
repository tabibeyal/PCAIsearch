import re
from typing import List, Tuple

from analysis.parallels.normalise import normalise

# (verse_number, char_offset_in_raw_verse)
Offset = Tuple[int, int]


def tokenise_sutta(verses: List[dict]) -> Tuple[List[str], List[Offset]]:
    """
    Tokenise all verses in a sutta, returning (tokens, offsets).
    offsets[i] = (verse_number, char_offset_in_raw_pali) for tokens[i].
    Spans may cross verse boundaries. Offsets index into the raw pali field.
    """
    tokens: List[str] = []
    offsets: List[Offset] = []

    for verse in verses:
        verse_num = verse["number"]
        raw = verse.get("pali", "")
        if not raw.strip():
            continue

        for m in re.finditer(r"\S+", raw):
            word_raw = m.group()
            word_norm = normalise(word_raw)
            if word_norm:
                tokens.append(word_norm)
                offsets.append((verse_num, m.start()))

    return tokens, offsets
