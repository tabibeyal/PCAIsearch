"""
Corpus chunk-length analysis for issue #135.

Quantifies how many per-verse chunks in data/dumps/*.json fall below a
"readable on its own" length threshold, and characterizes what those
short chunks are (poem lines, numbered-list items, titles/headers).

Pure data analysis -- no models, no network, no API keys. Safe to run
with Firefox open.

Run:
    PYTHONPATH=. python3 analysis/chunk_length_corpus.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DUMPS_DIR = Path(__file__).parent.parent / "data" / "dumps"

# A chunk is "context-free / single-line" if its english text is shorter
# than this many words. The three observed weak-pool fragments anchor the
# threshold: AN 4.50:21 ("unwise, consent to gold & silver,") = 6 words,
# UD 2.9:6 ~ one short verse line, DN 33:309 ~ one numbered-list item.
# 12 words sits above these fragments but below a normal sentence, so it
# separates "broken-looking snippet" from "readable prose".
WORD_FLOOR = 12

# Verse lines this short, with no terminal punctuation, read as a single
# verse line rather than a sentence. Used only inside classify_short.
VERSE_LINE_CHAR_MAX = 60

# Per-dump verses 1 and 2 hold the series title and sutta title (e.g.
# "Numerical Discourses 1.50", "–53 Luminous"). Treating these as titles
# by *position* avoids mistaking a short verse line for a title.
TITLE_VERSE_NUMBERS = {1, 2}


def word_count(text: str) -> int:
    return len(text.split())


def char_count(text: str) -> int:
    return len(text.strip())


TITLE_PATTERNS = [
    re.compile(r"^(Numerical Discourses|Linked Discourses|Middle-Length Discourses|"
               r"Long Discourses|Gradual Sayings|The Discourses|Udāna|Dhammapada|"
               r"Itivuttaka|Sutta Nipāta|Theragāthā|Therīgāthā|Khuddakapāṭha)\b", re.I),
    # Range continuations like "–141 For the Benefit of Many People"
    re.compile(r"^[–-]\d"),
]


def is_title(text: str, verse_num: int | None = None) -> bool:
    """A title/header chunk: the series/sutta title at the head of a dump,
    or an explicit heading pattern. Position-based (verse 1 or 2) so a short
    verse line elsewhere isn't mistaken for a title."""
    t = text.strip()
    if not t:
        return False
    if any(p.search(t) for p in TITLE_PATTERNS):
        return True
    if verse_num is not None and verse_num in TITLE_VERSE_NUMBERS:
        return True
    return False


def classify_short(text: str, verse_num: int | None = None) -> str:
    """Best-effort label for why a short chunk reads as context-free."""
    t = text.strip()
    if not t:
        return "empty"
    if is_title(t, verse_num):
        return "title-or-header"
    # Numbered list item: starts with a number/letter enumerator
    if re.match(r"^(\d+[.)]|[—-]|[a-z][.)]|[ivxlc]+[.)])\s", t, re.I):
        return "numbered-list-item"
    # Verse / poem line: short and ends with comma or no terminal punctuation
    if len(t) < VERSE_LINE_CHAR_MAX and not t.endswith((".", "!", "?")):
        return "verse-or-fragment"
    return "other-prose"


def load_chunks():
    chunks = []
    for path in sorted(DUMPS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        sutta_id = data.get("sutta_id", path.stem)
        for verse in data.get("verses", []):
            english = verse.get("english", "") or ""
            pali = verse.get("pali", "") or ""
            chunks.append({
                "id": f"{sutta_id}:{verse.get('number')}",
                "sutta_id": sutta_id,
                "number": verse.get("number"),
                "english": english,
                "pali": pali,
                "words": word_count(english),
                "chars": char_count(english),
            })
    return chunks


def nikaya_of(sutta_id: str) -> str:
    m = re.match(r"([a-zA-Z]+)", sutta_id)
    return m.group(1).upper() if m else "?"


def main():
    chunks = load_chunks()
    total = len(chunks)
    print(f"Total chunks across corpus: {total}")
    print(f"Dump files: {len(list(DUMPS_DIR.glob('*.json')))}")
    print()

    # Overall length distribution
    words = sorted(c["words"] for c in chunks)
    chars = sorted(c["chars"] for c in chunks)

    def pct(thresh):
        n = sum(1 for w in words if w <= thresh)
        return n, 100.0 * n / total

    print("=== Word-count distribution (english) ===")
    for w in [0, 3, 5, 8, 10, 12, 15, 20, 25]:
        n, p = pct(w)
        print(f"  <= {w:>2} words: {n:>5} chunks  ({p:5.2f}%)")
    print(f"  median words: {words[len(words)//2]}")
    print(f"  mean words:   {sum(words)/total:.1f}")
    print()

    print("=== Char-count distribution (english) ===")
    for c_thresh in [0, 40, 60, 80, 100, 120, 150, 200]:
        n = sum(1 for c in chars if c <= c_thresh)
        print(f"  <= {c_thresh:>3} chars: {n:>5} chunks  ({100.0*n/total:5.2f}%)")
    print()

    # Breakdown by nikaya
    print(f"=== Short chunks (<= {WORD_FLOOR} words) by nikaya ===")
    by_nik = defaultdict(lambda: [0, 0])  # [short, total]
    for c in chunks:
        n = nikaya_of(c["sutta_id"])
        by_nik[n][1] += 1
        if c["words"] <= WORD_FLOOR:
            by_nik[n][0] += 1
    print(f"  {'nikaya':<8} {'short':>6} {'total':>6} {'pct':>7}")
    for n in sorted(by_nik, key=lambda k: -by_nik[k][0]):
        short, tot = by_nik[n]
        print(f"  {n:<8} {short:>6} {tot:>6} {100.0*short/tot:>6.2f}%")
    print()

    # Characterize short chunks, separating titles from content fragments
    print(f"=== What the <= {WORD_FLOOR}-word chunks are ===")
    labels = Counter()
    for c in chunks:
        if c["words"] <= WORD_FLOOR:
            labels[classify_short(c["english"], c.get("number"))] += 1
    for label, n in labels.most_common():
        print(f"  {label:<22} {n:>5}  ({100.0*n/sum(labels.values()):5.2f}%)")
    print()

    # Content-only view: exclude title/header chunks to see how many actual
    # content fragments (poem lines, list items, prose snippets) are short.
    content_chunks = [c for c in chunks if not is_title(c["english"], c.get("number"))]
    content_total = len(content_chunks)
    content_short = [c for c in content_chunks if c["words"] <= WORD_FLOOR]
    print(f"=== Content chunks only (titles excluded) ===")
    print(f"  content chunks: {content_total} / {total} total")
    print(f"  <= {WORD_FLOOR} words: {len(content_short)} "
          f"({100.0*len(content_short)/content_total:.2f}% of content)")
    content_labels = Counter(classify_short(c["english"], c.get("number")) for c in content_short)
    for label, n in content_labels.most_common():
        print(f"    {label:<22} {n:>5}  ({100.0*n/len(content_short):5.2f}%)")
    print()

    # Sample content fragments (exclude titles)
    print(f"=== Sample content fragments (<= {WORD_FLOOR} words, titles excluded), first 25 ===")
    for c in content_short[:25]:
        print(f"  {c['id']:<14} [{c['words']:>2}w] {c['english'][:70]}")
    print()

    # The three observed weak-pool fragments
    print("=== Observed weak-pool fragments from issue #133 ===")
    for cid in ["AN4.50:21", "UD2.9:6", "DN33:309"]:
        match = next((c for c in chunks if c["id"].replace(" ", "") == cid), None)
        if match:
            print(f"  {match['id']:<12} [{match['words']:>2}w, {match['chars']:>3}c] {match['english'][:70]}")
    print()

    # How many short content chunks have a non-empty pali field (real verse
    # lines with a Pāḷi original vs. pure english prose fragments)?
    short_with_pali = sum(1 for c in content_short if c["pali"].strip())
    print(f"Short content chunks with non-empty pali field: {short_with_pali}/{len(content_short)} "
          f"({100.0*short_with_pali/max(1,len(content_short)):.1f}%)")


if __name__ == "__main__":
    main()