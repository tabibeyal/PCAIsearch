import re
import unicodedata


def normalise(text: str) -> str:
    """Light Pāḷi normalisation: NFC, lower-case, strip punctuation, collapse whitespace, canonicalise niggahita."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("ṁ", "ṃ")  # ṁ (overdot) -> ṃ (underdot)
    return text
