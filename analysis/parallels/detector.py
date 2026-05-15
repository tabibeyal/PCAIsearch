import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from analysis.parallels.tokenise import tokenise_sutta, Offset

DETECTOR_VERSION = "v1-k7-light"


def _span_id(normalised_text: str) -> str:
    return hashlib.sha256(normalised_text.encode()).hexdigest()[:12]


def build_parallels(
    suttas: List[dict],
    conn: sqlite3.Connection,
    k: int = 7,
) -> None:
    """
    Detect maximal recurring Pāḷi spans across suttas and write to conn.
    Idempotent: re-running with the same input produces the same rows (INSERT OR IGNORE).
    """
    # Step 1: tokenise each sutta, build shingle -> [(sutta_id, token_index)] index
    sutta_tokens: Dict[str, Tuple[List[str], List[Offset]]] = {}
    for sutta in suttas:
        sid = sutta["sutta_id"]
        tokens, offsets = tokenise_sutta(sutta.get("verses", []))
        sutta_tokens[sid] = (tokens, offsets)

    # shingle (tuple of k tokens) -> list of (sutta_id, start_token_index)
    shingle_index: Dict[tuple, List[Tuple[str, int]]] = defaultdict(list)
    for sid, (tokens, _offsets) in sutta_tokens.items():
        for i in range(len(tokens) - k + 1):
            shingle = tuple(tokens[i : i + k])
            shingle_index[shingle].append((sid, i))

    # Step 2: filter to shingles with >= 2 hits
    repeated = {sh: hits for sh, hits in shingle_index.items() if len(hits) >= 2}

    # Step 3: for each repeated shingle, extend to maximal span across ALL hits
    # Track already-emitted spans by ID to avoid duplicates
    seen_span_ids: set = set()
    span_rows: List[tuple] = []
    occurrence_rows: List[tuple] = []

    # Sort shingles so that earlier positions are visited first; skip sub-spans
    # Strategy: for each shingle, attempt extension; emit only maximal spans.
    # A span is not maximal if it is a substring (sub-token-sequence) of a longer emitted span
    # at the same occurrence positions. We track (sutta_id, start_idx) -> max span length emitted.
    covered: Dict[Tuple[str, int], int] = {}  # (sutta_id, start_idx) -> token_count of emitted span

    for shingle, hits in repeated.items():
        # Extend left and right while all hits agree
        # Collect (sutta_id, start_token_idx) for all hits
        positions = hits  # list of (sid, idx)

        # Extend right
        ext_len = k
        while True:
            nexts = []
            for sid, idx in positions:
                tokens = sutta_tokens[sid][0]
                next_pos = idx + ext_len
                if next_pos < len(tokens):
                    nexts.append(tokens[next_pos])
                else:
                    nexts.append(None)
            if len(set(nexts)) == 1 and nexts[0] is not None:
                ext_len += 1
            else:
                break

        # Extend left
        left_ext = 0
        while True:
            prevs = []
            for sid, idx in positions:
                tokens = sutta_tokens[sid][0]
                prev_pos = idx - left_ext - 1
                if prev_pos >= 0:
                    prevs.append(tokens[prev_pos])
                else:
                    prevs.append(None)
            if len(set(prevs)) == 1 and prevs[0] is not None:
                left_ext += 1
            else:
                break

        # Adjust positions to maximal start
        max_positions = [(sid, idx - left_ext) for sid, idx in positions]
        total_len = ext_len + left_ext

        # Get normalised text from first hit
        first_sid, first_idx = max_positions[0]
        first_tokens = sutta_tokens[first_sid][0]
        span_tokens = first_tokens[first_idx : first_idx + total_len]
        normalised_text = " ".join(span_tokens)
        span_id = _span_id(normalised_text)

        if span_id in seen_span_ids:
            continue

        # Check if all positions are already covered by a longer span
        all_covered = all(
            covered.get((sid, idx), 0) >= total_len
            for sid, idx in max_positions
        )
        if all_covered:
            continue

        seen_span_ids.add(span_id)
        for sid, idx in max_positions:
            if covered.get((sid, idx), 0) < total_len:
                covered[(sid, idx)] = total_len

        span_rows.append((span_id, normalised_text, total_len, len(max_positions), DETECTOR_VERSION))

        for sid, idx in max_positions:
            tokens_list, offsets_list = sutta_tokens[sid]
            verse_num, char_off = offsets_list[idx]
            # char_length: from start of span token to end of last span token in raw pali
            end_idx = idx + total_len - 1
            _, end_char_off = offsets_list[end_idx]
            last_raw_token = tokens_list[end_idx]
            char_len = (end_char_off + len(last_raw_token)) - char_off
            occurrence_rows.append((span_id, sid, verse_num, char_off, char_len))

    # Write to DB
    conn.executemany(
        "INSERT OR IGNORE INTO span(id, normalised_pali, token_count, occurrence_count, detector_version) "
        "VALUES (?, ?, ?, ?, ?)",
        span_rows,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO occurrence(span_id, sutta_id, verse_number, char_offset, char_length) "
        "VALUES (?, ?, ?, ?, ?)",
        occurrence_rows,
    )
    conn.commit()
