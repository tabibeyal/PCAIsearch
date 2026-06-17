import re


def tokenize(text: str) -> list[str]:
    """Lower-case, alphabetic tokenization for BM25 and title indices."""
    return re.findall(r"[a-z]+", text.lower())
