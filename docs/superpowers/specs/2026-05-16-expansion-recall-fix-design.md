# Expansion Recall Fix — Design Spec
Date: 2026-05-16

## Problem

The expansion pipeline (LLM query expansion + dense + BM25 + RRF + rerank) scores 26% recall@10,
while BM25+dense with no expansion scores 46%. Two distinct bugs cause this regression.

**Bug 1 — First-seen dedup destroys dense ranking.**
`search_pipeline.py` builds `dense_deduped` by iterating query results in order and keeping the
first occurrence of each verse ID. An item retrieved at rank 2 by the second expanded query lands
at position 32 in the deduplicated list. Its RRF contribution is 1/(60+32+1) ≈ 0.011 instead of
the 1/(60+2+1) ≈ 0.016 it earned. BM25 champions get buried because the dense list's ordering
is arbitrary (first-seen), not relevance-based.

**Bug 2 — Expansion prompt v1 generates redundant paraphrases.**
The v1 prompt asks for "2 keyword-focused search strings" with Pāḷi terms loosely encouraged.
In practice the LLM produces near-paraphrases of the original question. Canonical Pāḷi
vocabulary (avijjā, paṭicca-samuppāda, kālāmā) that would match the actual verse text is absent.
This prevents SN 12.1 and AN 3.65 from being found even when the BM25 index would otherwise
surface them on the right terms.

## Goals

- Expansion pipeline recall@10 ≥ 47% (beats BM25+dense baseline of 46%).
- Retain expansion for answer quality (synthesis still uses expanded context).
- Make generated query variants inspectable via the benchmark CLI.

## Design

### 1. Multi-list RRF for dense results (`fusion.py`)

Add `rrf_fuse_multi(lists, k=60)`:

```
rrf_fuse_multi(lists: List[List[Dict]], k: int = 60) -> List[Dict]
```

Each list in `lists` independently contributes `1 / (k + rank + 1)` for every item it contains.
Items appearing in multiple lists accumulate score from each. This is standard multi-list RRF —
no list has structural priority over another.

This replaces the current first-seen dedup loop in `search_pipeline.py`. The two-step fusion
becomes:

```
dense_fused  = rrf_fuse_multi(per_query)        # N dense lists → one ranked list
all_results  = rrf_fuse(dense_fused, bm25_merged)  # balanced 1:1 with BM25
```

The second `rrf_fuse` call is unchanged — dense and BM25 contribute equally in the final step
regardless of how many expansion queries fed the dense side.

### 2. Expansion prompt v2 (`search_pipeline.py → ExpansionPrompt`)

Add `"v2"` to `ExpansionPrompt.VERSIONS`. The v2 prompt enforces a strict two-line contract:

- **Line 1 — English passage vocabulary**: concrete words likely to appear verbatim in a sutta
  verse (not a rephrasing of the question; passage-level vocabulary, not question-level).
- **Line 2 — Pāḷi doctrinal term cluster**: canonical Pāḷi terminology for the concept,
  space-separated, transliterated (e.g. `avijjā saṅkhārā viññāṇa paṭicca-samuppāda`).

The two lines must be maximally distinct from each other and from the original query.
Sutta numbers remain forbidden; proper names of communities or persons (e.g. "kālāmā") are
allowed because they appear in the text.

`SearchPipeline` default switches from `"v1"` to `"v2"`.

**Example — "how does ignorance cause suffering step by step":**
```
ignorance conditions formations consciousness name form contact feeling craving clinging birth aging death sorrow
avijjā saṅkhārā viññāṇa nāmarūpa phassa vedanā taṇhā upādāna bhava jāti paṭicca-samuppāda
```

**Example — "how do you know whether a religious teaching is worth following":**
```
don't believe tradition report scripture reasoning logic fit premises teacher respect verify yourself
kālāmā tradition paramparā anussava vitakka naya ākāra diṭṭhi kusala dhamma
```

### 3. Benchmark visibility (`retrieval_benchmark.py`)

Add `--log-variants` flag. When used with `--with-expansion`, prints the generated query
variants for each case before the hit/miss result:

```
[MN 21] Variants:
  0: should a monk feel anger even if attacked with a saw
  1: even if bandits sawed limb from limb no ill will malevolence patient endurance
  2: kakacūpama khanti mettā adosa abyāpāda
✗  0.412
```

Implementation: `retrieve()` in the expansion branch returns `(chunks, variants)` when
`log_variants=True`; the benchmark prints them inline.

### 4. Tests

| File | New tests |
|---|---|
| `tests/backend/test_fusion.py` | `rrf_fuse_multi`: correct scoring for N lists; items in multiple lists accumulate score; items only in later lists not penalized vs first-seen; single-list case equals `rrf_fuse` one-side behaviour |
| `tests/backend/test_search_pipeline.py` | Pipeline uses `rrf_fuse_multi` on per-query dense results (mock verifies call); existing BM25+dense tests pass unchanged |
| `tests/backend/test_search_pipeline.py` | `ExpansionPrompt("v2").get_prompt()` returns a string containing "line 1" / "line 2" structural instruction; default pipeline uses v2 |

All 100 existing tests must continue to pass.

## Files changed

| File | Change |
|---|---|
| `backend/app/services/fusion.py` | Add `rrf_fuse_multi` |
| `backend/app/services/search_pipeline.py` | Replace first-seen dedup with `rrf_fuse_multi`; add `ExpansionPrompt` v2; default to v2 |
| `tests/backend/test_fusion.py` | Tests for `rrf_fuse_multi` |
| `tests/backend/test_search_pipeline.py` | Tests for hierarchical RRF call and v2 prompt |
| `tests/backend/retrieval_benchmark.py` | Add `--log-variants` flag |

## Success criterion

`PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion`
reports overall recall@10 ≥ 47%.
