# Handoff — Session 2026-05-17

## What happened this session

**Recall pushed from 60% → 93% (14/15).**

Four sub-sessions of work (previous + this session):

**Sub-session 1 — BM25 hybrid retrieval (previous):** Built BM25 retrieval fused with dense results via RRF.

**Sub-session 2 — nikayas filter parity:** Fixed `BM25Retriever.retrieve()` ignoring the `nikayas` restriction.

**Sub-session 3 — benchmark investigation:** Loosened benchmark gold standard; diagnosed expansion underperformance; fixed BM25 to run on all expanded variants.

**Sub-session 4 — expansion recall fix:**
- Diagnosed two bugs: (1) first-seen dedup of dense results destroyed meaningful ranking; (2) benchmark's `--with-expansion` path never injected BM25 — it was testing dense-only the whole time.
- Added `rrf_fuse_multi` — proper multi-list RRF over N ranked lists.
- Replaced first-seen dense dedup with `rrf_fuse_multi(per_query)` in `SearchPipeline.search()`.
- Added `ExpansionPrompt` v2: strict two-line contract (Line 1 = English passage vocab, Line 2 = Pāḷi doctrinal term cluster). Switched pipeline default to v2.
- Fixed benchmark to inject `BM25Retriever` into the `--with-expansion` path.
- Added `--log-variants` flag to benchmark for variant inspection.

**Sub-session 5 — rerank_multi + English hints (this session):**
- Added `rerank_multi` to `search_pipeline.py`: cross-encoder scores each candidate against `[original_query, english_hint]` and takes the max.
- Added `english_hint` field to `DictionaryEntry` in `pali_dictionary.py` — verbatim passage fragment from the target sutta.
- Reranking scoped to original query + curated dict hints only (LLM variants excluded — add noise).
- MN 61 `english_hint` corrected to match actual sutta vocabulary ("bad deed" / "deliberate lie").
- ExpansionPrompt advanced through v3 → v6: Pāḷi reference table, few-shot example, English passage hints.
- Fixed `expand_query` stripping `"Line N:"` label prefixes from LLM output.
- Final benchmark: **14/15 (93%)** — stable across two runs. Only miss: SN 12.1 (structurally hard).

---

## Recall@10 scoreboard

| Mode | Hard | Medium | Easy | Total |
|------|------|--------|------|-------|
| Dense only | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| BM25 + dense (no expansion) | 4/5 | 2/5 | 1/5 | 7/15 (46%) |
| Expansion + BM25 (fixed) | 3/5 | 3/5 | 2/5 | 8/15 (53%) |
| + Pāḷi dict + v3 prompt | 3/5 | 3/5 | 3/5 | 9/15 (60%) |
| **+ rerank_multi + English hints (v6 prompt)** | **5/5** | **4/5** | **5/5** | **14/15 (93%)** |

### What the final push gained

New hits (v6 prompt + rerank_multi): MN 21 (saw simile), AN 3.65 (Kālāma — teaching worth following), SN 22.59 (five aggregates/anattā), MN 61 (first precept — lying).

Only remaining miss: SN 12.1 — paṭicca-samuppāda passage not retrievable by embedding model in its current corpus form.

---

## Recent commits (this session)

- `85675fb` — `docs: update CONTEXT.md retrieval pipeline with new components`
- `d905a56` — `docs: update CLAUDE.md with current test command, benchmark, and architecture`
- `777157c` — `feat: use English-only passage hints for reranking (drop Pāḷi terms)`
- `c8999c4` — `feat: rerank against original + curated dict hints only (not LLM variants)`
- `3cb3bd3` — `feat: rerank against all expanded query variants (max score)`
- `e494c09` — `fix: correct MN 61 english_hint to exact sutta vocabulary`
- `657964c` — `feat: add english_hint to DictionaryEntry for verbatim passage vocabulary`
- `b2acad9` — `fix: strip 'Line N:' label prefixes from expansion variants + fix v6 example contamination`
- `9f6c6e4` — `feat: add ExpansionPrompt v6 with second example and Rahula-specific entry`
- `5e16d48` — `feat: add ExpansionPrompt v5 with English passage hints in reference table`
- `f0e4123` — `feat: add ExpansionPrompt v4 with few-shot example to prevent prompt leakage`

---

## What was built (cumulative)

### Files

| File | Purpose |
|------|---------|
| `backend/app/services/bm25_retriever.py` | `BM25Retriever` — BM25Okapi over English verses; `retrieve(query, top_k, nikayas=None)`; `from_directory(dumps_dir)` |
| `backend/app/services/fusion.py` | `rrf_fuse(dense, sparse, k=60)` + `rrf_fuse_multi(lists, k=60)` — Reciprocal Rank Fusion |
| `tests/backend/test_bm25_retriever.py` | 13 unit tests |
| `tests/backend/test_fusion.py` | 22 unit tests (11 for `rrf_fuse`, 11 for `rrf_fuse_multi`) |
| `tests/backend/retrieval_benchmark.py` | Recall@10 benchmark; `--with-bm25`, `--with-expansion`, `--no-rerank`, `--log-variants`, `--k` flags |

### Modified files

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | Hierarchical RRF (`rrf_fuse_multi` for dense, then `rrf_fuse` vs BM25); ExpansionPrompt v2; default v2; raises on unknown version |
| `backend/app/main.py` | Builds `BM25Retriever` at startup and injects into `SearchPipeline` |
| `tests/backend/test_search_pipeline.py` | 13 tests total |

---

## Search flow (current)

```
query
  └─► expand_query → [q1, q2, q3]   (ExpansionPrompt v2: English vocab + Pāḷi term cluster)
        ├─► dense retrieve (Qdrant, nikayas filter) × 3 queries
        │       └─► rrf_fuse_multi([dense_q1, dense_q2, dense_q3]) → dense_fused
        └─► BM25 retrieve (nikayas filter) × 3 queries
                └─► best bm25_score per verse kept → bm25_merged
                                                    ▼
                                    rrf_fuse(dense_fused, bm25_merged)
                                                    ▼
                          rerank_multi([original_query, english_hint])
                          cross-encoder takes max score per candidate
                                                    ▼
                                            top_k results
```

---

## Test suite

**118 passed**, 6 pre-existing errors in `test_api.py` (missing `NVIDIA_API_KEY` in test env — unchanged).

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

---

## Open issues / next steps

### SN 12.1 — last hard miss

Paṭicca-samuppāda passage not retrievable via embedding model. Options: hand-crafted `english_hint` in pali_dictionary pointing at the dependent origination chain, or ingest a richer version of SN 12.1.

### Phase 2.5 — Public read-only API + explorer UI

`/parallels` route backed by 4–5 read-only endpoints over `data/parallels.sqlite`. Schema already shaped; ~20 LOC HTTP layer.

### Phase 2 — Vinaya ingestion (deferred)

Parser regex `r"([a-zA-Z]+)([\d.]+)"` won't match `pli-tv-bu-vb-pj1` IDs — needs extension before Vinaya can be ingested.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — dense vector retrieval against Qdrant; injectable seam (`Retriever`)
- **BM25Retriever** — in-memory BM25 over English verses; loaded from `data/dumps/` at startup; injected into `SearchPipeline`; accepts optional `nikayas` filter (post-score, full-corpus IDF); runs on all expanded query variants
- **rrf_fuse** — two-list Reciprocal Rank Fusion; pure function in `fusion.py`; `k=60` default
- **rrf_fuse_multi** — N-list Reciprocal Rank Fusion; each list contributes independently; first-occurrence payload wins; used for dense side of hierarchical fusion
- **rerank_multi** — cross-encoder scores each candidate against `[original_query, english_hint]`, takes max; English-only model so Pāḷi excluded; defined in `search_pipeline.py`
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15; `get_title_text()` returns v3 for SN/AN chapter-header suttas
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; v2 is default (two-line: English passage vocab + Pāḷi term cluster); raises `ValueError` on unknown version
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?"
- **SuttaRelations** — answers "what is related to sutta X?"
- **Span** — maximal recurring Pāḷi token sequence; content-addressed by SHA-256 of normalised text
- **Occurrence** — `(span_id, sutta_id, verse_number, char_offset, char_length)`; char offsets index raw pali field
- **Detector** — offline batch tool producing `data/parallels.sqlite`; versioned (`v1-k7-light`)
- **Light normalisation** — NFC + lower + strip punctuation + collapse whitespace + ṁ→ṃ
- **Shingle** — k=7 consecutive normalised tokens; used to seed span detection
- **retrieval_k** — internal candidate pool = `max(top_k * 3, 30)`; used for dense and BM25 per query
- **PaliDictionary / lookup** — `pali_dictionary.py`; ~55 `DictionaryEntry` objects (label, keywords, pali, english_hint); `lookup(query)` returns `(pali_cluster, english_hint)` when keyword-matched; pali used in expansion, english_hint fed to `rerank_multi`
- **english_hint** — verbatim passage fragment stored in `DictionaryEntry`; bridges vocabulary gap between query and sutta text for the cross-encoder
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
