# Handoff — Session 2026-05-16 (BM25 hybrid retrieval)

## What happened this session

Built the BM25 hybrid retrieval feature: a second retrieval path over all 116k English verses fused with dense vector results via Reciprocal Rank Fusion, fixing vocabulary-mismatch failures (easy-tier 0/5).

**Commits this session:**
- `f23a9e9` — `feat: add BM25Retriever for exact-match verse retrieval`
- `be6101a` — `fix: guard against empty verses and missing english key in BM25Retriever`
- `07e0462` — `feat: add rrf_fuse for Reciprocal Rank Fusion`
- `39e6d03` — `fix: add None id guard in rrf_fuse and add score regression test`
- `516a21a` — `feat: integrate BM25Retriever into SearchPipeline with RRF fusion`
- `dd300eb` — `fix: add nikayas TODO, fix import placement, add constructor test`
- `631ce29` — `feat: wire BM25Retriever into app startup`

---

## What was built

### New files

| File | Purpose |
|------|---------|
| `backend/app/services/bm25_retriever.py` | `BM25Retriever` — in-memory BM25Okapi index over English verses; `retrieve(query, top_k)` returns dicts with `bm25_score`; `from_directory(dumps_dir)` loads via `SuttaParser` |
| `backend/app/services/fusion.py` | `rrf_fuse(dense, sparse, k=60)` — pure Reciprocal Rank Fusion; dense payload wins for shared IDs; `None` ids skipped |
| `tests/backend/test_bm25_retriever.py` | 10 unit tests |
| `tests/backend/test_fusion.py` | 11 unit tests including concrete score regression |
| `docs/superpowers/specs/2026-05-15-bm25-hybrid-design.md` | Design spec |
| `docs/superpowers/plans/2026-05-15-bm25-hybrid.md` | Implementation plan |

### Modified files

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | `SearchPipeline` accepts `bm25_retriever: Optional[BM25Retriever] = None`; `search()` runs BM25 retrieve + `rrf_fuse` when present, falls back to dense-only |
| `backend/app/main.py` | `lifespan` builds `BM25Retriever.from_directory(_DUMPS_DIR)` and injects into `SearchPipeline` |
| `tests/backend/test_search_pipeline.py` | Added integration test + constructor test; 4 tests total |

---

## New search flow

```
query
  └─► expand_query → [q1, q2, q3]
        ├─► dense retrieve (Qdrant) × 3 queries  ─┐
        └─► BM25 retrieve (rank_bm25) × 1 query  ─┤
                                                   ▼
                                            rrf_fuse(dense_deduped, bm25_results)
                                                   ▼
                                            CrossEncoder rerank
                                                   ▼
                                            top_k results
```

BM25 runs once against the original query (not the expanded variants). Dense dedup happens before fusion.

---

## Test suite

**95 passed**, 21 new tests. 6 pre-existing errors in `test_api.py` (missing `NVIDIA_API_KEY` in test env — unchanged).

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

---

## Known gap / TODOd in code

**BM25 does not apply the `nikayas` filter.** `BM25Retriever.retrieve()` has no `nikayas` parameter — if a caller restricts to `nikayas=["MN"]`, dense results are filtered but BM25 results are not. This is TODOd in `search_pipeline.py:190`. Fix: add `nikayas: Optional[List[str]] = None` to `BM25Retriever.retrieve()` and filter the pre-built verse list.

---

## Open issues / next steps

### Phase 1.5 — Pāḷi word clusters

Inverted index: doctrinal term → all occurrences. Fits `analysis/` + same SQLite file (new tables). Reuses normalised token stream from the parallel-passage detector.

### Phase 2.5 — Public read-only API + explorer UI

`/parallels` route backed by 4–5 read-only endpoints over `data/parallels.sqlite`. Schema already shaped for this; ~20 LOC HTTP layer.

### Phase 2 — Vinaya ingestion (deferred)

Parser regex `r"([a-zA-Z]+)([\d.]+)"` won't match `pli-tv-bu-vb-pj1` IDs — needs extension before Vinaya can be ingested.

### BM25 nikayas filter

See TODOd gap above. Small, self-contained fix.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — dense vector retrieval against Qdrant; injectable seam (`Retriever`)
- **BM25Retriever** — in-memory BM25 over English verses; loaded from `data/dumps/` at startup; injected into `SearchPipeline`
- **rrf_fuse** — Reciprocal Rank Fusion of dense + BM25 results; pure function in `fusion.py`; `k=60` default
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks fused candidate pool
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15; `get_title_text()` returns v3 for SN/AN chapter-header suttas
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; currently v1 only
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?"
- **SuttaRelations** — answers "what is related to sutta X?"
- **Span** — maximal recurring Pāḷi token sequence; content-addressed by SHA-256 of normalised text
- **Occurrence** — `(span_id, sutta_id, verse_number, char_offset, char_length)`; char offsets index raw pali field
- **Detector** — offline batch tool producing `data/parallels.sqlite`; versioned (`v1-k7-light`)
- **Light normalisation** — NFC + lower + strip punctuation + collapse whitespace + ṁ→ṃ
- **Shingle** — k=7 consecutive normalised tokens; used to seed span detection
- **retrieval_k** — internal candidate pool = `max(top_k * 3, 30)`; used for both dense and BM25 retrieval
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
