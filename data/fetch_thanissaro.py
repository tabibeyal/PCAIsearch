"""
Downloads Thanissaro Bhikkhu's translations from the dhammatalks.org epub
and converts them to the format expected by process_dumps.py:
  { "sutta_id": "MN1", "verses": [{"number": 1, "pali": "", "english": "..."}, ...] }

Clears all existing .json files in data/dumps/ before writing new ones.

Run: python3 data/fetch_thanissaro.py
"""
import io
import json
import re
import zipfile
from pathlib import Path

import requests
from bs4 import BeautifulSoup

EPUB_URL = "https://www.dhammatalks.org/Archive/Writings/Ebooks/SuttaPitaka_251113.epub"
DUMP_DIR = Path(__file__).parent / "dumps"

# Each entry: epub_subdir -> (nikaya_prefix, filename_pattern, header_template)
# header_template uses {num} for single-number IDs and {chap}/{num} for compound IDs.
_NIKAYA_CONFIG = [
    ("DN",      "DN",   re.compile(r"^DN0*(\d+)$"),                           "Long Discourses {num}"),
    ("MN",      "MN",   re.compile(r"^MN(\d+)$"),                             "Middle Length Discourses {num}"),
    ("SN",      "SN",   re.compile(r"^SN(\d+)_(\d+)$"),                       "Linked Discourses {chap}.{num}"),
    ("AN",      "AN",   re.compile(r"^AN(\d+)_(\d+)$"),                       "Numerical Discourses {chap}.{num}"),
    ("KN/Dhp",  "DHP",  re.compile(r"^Ch0*(\d+)$"),                           "Dhammapada {num}"),
    ("KN/Iti",  "ITI",  re.compile(r"^iti(\d+)$", re.IGNORECASE),             "Itivuttaka {num}"),
    ("KN/Ud",   "UD",   re.compile(r"^ud(\d+)_(\d+)$", re.IGNORECASE),        "Udana {chap}.{num}"),
    ("KN/StNp", "STNP", re.compile(r"^StNp(\d+)_(\d+)$", re.IGNORECASE),     "Sutta Nipata {chap}.{num}"),
    ("KN/Thag", "THAG", re.compile(r"^thag(\d+)(?:_(\d+))?$", re.IGNORECASE),"Theragatha {num}"),
    ("KN/Thig", "THIG", re.compile(r"^thig(\d+)(?:_(\d+))?$", re.IGNORECASE),"Therigatha {num}"),
    ("KN/Khp",  "KHP",  re.compile(r"^khp(\d+)$", re.IGNORECASE),            "Khuddakapatha {num}"),
]

_SKIP_CLASSES = {"note", "seealso", "stars", "suttaCite", "notetitle", "chap"}

# Collections where body is made of verse stanzas rather than prose paragraphs
_VERSE_NIKAYAS = {"DHP", "THAG", "THIG", "STNP"}


def _make_sutta_id(prefix: str, match: re.Match) -> str:
    groups = [g for g in match.groups() if g is not None]
    if len(groups) == 2:
        return f"{prefix}{groups[0]}.{groups[1]}"
    return f"{prefix}{groups[0]}"


def _make_header(template: str, match: re.Match) -> str:
    groups = [g for g in match.groups() if g is not None]
    if len(groups) == 2:
        if "{chap}" in template:
            return template.format(chap=int(groups[0]), num=int(groups[1]))
        # Template has only {num} (e.g. Thag/Thig): use "chap.num" as the number
        return template.format(num=f"{int(groups[0])}.{int(groups[1])}")
    return template.format(num=int(groups[0]))


def _extract_title(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (english_title, pali_title) from the <title> tag."""
    title_elem = soup.find("title")
    if not title_elem:
        return "", ""

    raw = title_elem.get_text().strip()

    # Strip leading sutta reference: "MN 1 ", "SN 12:2 ", "Dhp I : ", "Thag 1:1 ", "1 " etc.
    cleaned = re.sub(
        r"^(?:[A-Za-z]+\s+[IVXLC\d][:\d.]*\s*:?\s*|\d+\s+)",
        "",
        raw,
    ).strip()

    if "|" in cleaned:
        parts = cleaned.split("|", 1)
        return parts[0].strip(), parts[1].strip()

    if "—" in cleaned:  # em dash: "PaliName — EnglishName"
        parts = cleaned.split("—", 1)
        return parts[1].strip(), parts[0].strip()

    return cleaned, ""


def _strip_noise(sutta_div: BeautifulSoup) -> None:
    """Remove footnote markers and page-break spans in-place."""
    for span in sutta_div.find_all("span", class_="fn"):
        span.decompose()
    for span in sutta_div.find_all("span", attrs={"epub:type": "pagebreak"}):
        span.decompose()


def _extract_prose_chunks(sutta_div: BeautifulSoup) -> list[str]:
    chunks = []
    for elem in sutta_div.find_all("p"):
        if elem.find_parent(
            class_=lambda c: c and any(sk in (c if isinstance(c, list) else [c]) for sk in _SKIP_CLASSES)
        ):
            continue
        if any(sk in (elem.get("class") or []) for sk in _SKIP_CLASSES):
            continue
        text = re.sub(r"\s+", " ", elem.get_text(separator=" ")).strip()
        if text:
            chunks.append(text)
    return chunks


def _extract_verse_chunks(sutta_div: BeautifulSoup) -> list[str]:
    chunks = []
    for elem in sutta_div.find_all("div", class_=re.compile(r"^verse(-add)?$")):
        text = re.sub(r"\s+", " ", elem.get_text(separator=" ")).strip()
        if text:
            chunks.append(text)
    return chunks


def convert_file(html_bytes: bytes, nikaya_prefix: str, sutta_id: str, header: str) -> dict | None:
    soup = BeautifulSoup(html_bytes, "html.parser")
    sutta_div = soup.find(id="sutta")
    if not sutta_div:
        return None

    _strip_noise(sutta_div)

    english_title, pali_title = _extract_title(soup)

    if nikaya_prefix in _VERSE_NIKAYAS:
        body_chunks = _extract_verse_chunks(sutta_div)
    else:
        body_chunks = _extract_prose_chunks(sutta_div)

    if not body_chunks:
        return None

    verses = [
        {"number": 1, "pali": header,      "english": header},
        {"number": 2, "pali": pali_title,   "english": english_title},
    ]
    for i, chunk in enumerate(body_chunks, start=3):
        verses.append({"number": i, "pali": "", "english": chunk})

    return {"sutta_id": sutta_id, "verses": verses}


def _dump_filename(sutta_id: str) -> str:
    return sutta_id.lower() + ".json"


def main() -> None:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)

    existing = list(DUMP_DIR.glob("*.json"))
    if existing:
        print(f"Clearing {len(existing)} existing dump files...")
        for f in existing:
            f.unlink()

    print(f"Downloading epub from {EPUB_URL}...")
    resp = requests.get(EPUB_URL, timeout=120)
    resp.raise_for_status()
    print(f"Downloaded {len(resp.content) // 1024} KB")

    epub = zipfile.ZipFile(io.BytesIO(resp.content))
    epub_names = set(epub.namelist())

    total = 0
    for subdir, nikaya_prefix, pattern, header_template in _NIKAYA_CONFIG:
        count = 0
        for epub_path in sorted(epub_names):
            if not epub_path.startswith(subdir + "/"):
                continue
            stem = Path(epub_path).stem
            match = pattern.match(stem)
            if not match:
                continue

            sutta_id = _make_sutta_id(nikaya_prefix, match)
            header = _make_header(header_template, match)
            result = convert_file(epub.read(epub_path), nikaya_prefix, sutta_id, header)
            if result is None:
                continue

            out_path = DUMP_DIR / _dump_filename(sutta_id)
            out_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            count += 1

        print(f"  {subdir:12s} ({nikaya_prefix:4s}): {count} suttas")
        total += count

    print(f"\nDone. {total} sutta files written to {DUMP_DIR}")
    print("Next: python3 data/process_dumps.py")


if __name__ == "__main__":
    main()
