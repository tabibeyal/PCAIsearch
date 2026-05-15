from typing import Optional


def reconstruct_raw(
    sutta_data: dict,
    verse_number: int,
    char_offset: int,
    char_length: int,
) -> str:
    """Slice raw Pāḷi text from a sutta dump given an occurrence's offset/length."""
    verse_map = {v["number"]: v.get("pali", "") for v in sutta_data.get("verses", [])}
    raw = verse_map.get(verse_number, "")
    if not raw:
        return ""
    return raw[char_offset : char_offset + char_length]
