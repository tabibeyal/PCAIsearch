# BM25 Hybrid Retrieval — Design Spec

**Date:** 2026-05-15  
**Status:** Approved

---

## Problem

The current retrieval pipeline uses dense vector (semantic similarity) search only. This causes vocabulary-mismatch failures: if a user's query contains exact words that appear in a passage, the passage may not surface because semantic similarity scores don't reward exact word overlap. This was diagnosed as the root cause of easy-tier 0/5 benchmark failures.

---

## Goal

Add a BM25 (exact word match) retrieval path that runs in parallel with the existing dense retrieval. Merge the two ranked result lists using Reciprocal Rank Fusion (RRF) before reranking. No change to the user-facing interface. BM25 is optional — if absent, the pipeline falls back to dense-only.

---

## Scope

- 116,187 English verses across 4,691 suttas in `data/dumps/`
- BM25 scores English text only (not Pāḷi)
- Client-side RRF fusion in Python (no Qdrant schema changes)
- Re-indexing Qdrant is not required

---

## Architecture

### New components

**`backend/app/services/bm25_retriever.py` — `BM25Retriever`**

Loads all English verses from `data/dumps/` at init time. Builds a `BM25Okapi` index (using `rank_bm25`, already installed). Exposes:

```
BM25Retriever.from_directory(dumps_dir: Path) -> BM25Retriever
BM25Retriever.retrieve(query: str, top_k: int) -> List[Dict]
```

Each result dict: `{id, pali, english, bm25_score}`. Stateless after init (~30–50 MB RAM, builds in a few seconds).

**`backend/app/services/fusion.py` — `rrf_fuse`**

Pure function. Standard Reciprocal Rank Fusion:

```
rrf_fuse(
    dense: List[Dict],
    sparse: List[Dict],
    k: int = 60,
) -> List[Dict]
```

Score per result = Σ `1 / (k + rank)` across lists. Merges by `id`; ties broken by dense rank. Returns merged list with `fusion_score` field, sorted descending.

### Modified component

**`backend/app/services/search_pipeline.py` — `SearchPipeline`**

Constructor gains optional param: `bm25_retriever: Optional[BM25Retriever] = None`.

In `search()`: if `bm25_retriever` is present, runs `bm25_retriever.retrieve(query, retrieval_k)` in parallel with the existing dense retrieval calls via `asyncio.gather`. Passes both result sets through `rrf_fuse`. The rest of the pipeline (dedup, CrossEncoder rerank) is unchanged.

**`backend/app/main.py`**

Wires `BM25Retriever.from_directory(Path("data/dumps"))` at startup and injects it into `SearchPipeline`.

---

## Data flow

```
query
  └─► expand_query → [q1, q2, q3]
        ├─► dense retrieve (Qdrant) × 3 queries   ─┐
        └─► BM25 retrieve (rank_bm25) × 1 query   ─┤
                                                    ▼
                                             rrf_fuse(dense_results, bm25_results)
                                                    ▼
                                             dedup by id
                                                    ▼
                                             CrossEncoder rerank
                                                    ▼
                                             top_k results
```

BM25 runs once against the original query (not the expanded variants), since BM25 rewards exact matches and expansion introduces paraphrase noise.

---

## Error handling

- `BM25Retriever` raises at init time if `dumps_dir` is missing or empty — fail-fast at startup.
- If `bm25_retriever` is `None` (e.g., in tests), `search()` skips fusion and uses dense results directly. No silent degradation.

---

## Testing

- `tests/backend/test_bm25_retriever.py` — unit tests: `from_directory` loads correctly, `retrieve` returns ranked results with expected fields, exact-match query ranks a known verse highly.
- `tests/backend/test_fusion.py` — unit tests for `rrf_fuse`: both lists contribute, ties go to dense, empty-list edge cases.
- `tests/backend/test_search_pipeline.py` — existing tests unaffected (BM25 injected as `None`). Add integration test: pipeline with BM25 injected surfaces a vocabulary-match result that dense-only misses.

---

## What is not changing

- Qdrant collection schema — no re-indexing needed
- `Retriever` class — untouched
- `SuttaTitleIndex` — untouched
- Synthesis, guardrail, citation oracle — untouched
- User-facing API contract — untouched
