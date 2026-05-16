# Handoff — Session 2026-05-16 (expansion recall fix)

## What happened this session

Four sub-sessions of work:

**Sub-session 1 — BM25 hybrid retrieval (previous):** Built BM25 retrieval fused with dense results via RRF.

**Sub-session 2 — nikayas filter parity:** Fixed `BM25Retriever.retrieve()` ignoring the `nikayas` restriction.

**Sub-session 3 — benchmark investigation:** Loosened benchmark gold standard; diagnosed expansion underperformance; fixed BM25 to run on all expanded variants.

**Sub-session 4 — expansion recall fix (this session):**
- Diagnosed two bugs: (1) first-seen dedup of dense results destroyed meaningful ranking; (2) benchmark's `--with-expansion` path never injected BM25 — it was testing dense-only the whole time.
- Added `rrf_fuse_multi` — proper multi-list RRF over N ranked lists.
- Replaced first-seen dense dedup with `rrf_fuse_multi(per_query)` in `SearchPipeline.search()`.
- Added `ExpansionPrompt` v2: strict two-line contract (Line 1 = English passage vocab, Line 2 = Pāḷi doctrinal term cluster). Switched pipeline default to v2.
- Fixed benchmark to inject `BM25Retriever` into the `--with-expansion` path.
- Added `--log-variants` flag to benchmark for variant inspection.

---

## Recall@10 scoreboard

| Mode | Hard | Medium | Easy | Total |
|------|------|--------|------|-------|
| Dense only | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| BM25 + dense (no expansion) | 4/5 | 2/5 | 1/5 | 7/15 (46%) |
| Expansion + BM25 (previous, dense-only bug) | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| Expansion + BM25 (fixed) | 3/5 | 3/5 | 2/5 | 8/15 (53%) |
| **Expansion + BM25 + Pāḷi dict** | **3/5** | **3/5** | **2/5** | **8/15 (53%)** |

Expansion + BM25 + Pāḷi dictionary holds at 53% — no regression, no new hits from the dictionary in this run.

### What the fix gained

New hits: SN 45.2 (spiritual friend), SN 56.11 ×2 (middle way, deepest origin of suffering), MN 10 (four foundations of mindfulness), MN 117 (noble eightfold path).

One regression: MN 61 dropped out — the LLM generated the first precept text (pāṇātipātā) instead of the lying precept text, flooding BM25 with irrelevant matches.

### Five persistent misses

None reachable by tuning alone — absent from both dense and BM25 top 50:
- **MN 21** — "should a monk feel anger if attacked with a saw" (saw simile; too idiomatic)
- **SN 12.1** — "how does ignorance cause suffering step by step" (LLM generates garbled paṭicca-samuppāda terms)
- **AN 3.65** — "how do you know whether a religious teaching is worth following" (LLM generates wrong Pāḷi cluster; should be kālāmā / anussava)
- **DN 31** — "how should one treat parents family and friends" (garbled Pāḷi)
- **SN 22.59** — "are the five aggregates permanent or do they lack a self" (dense cannot locate it)

### LLM expansion quality

The Gemma expansion model produces structurally correct two-line output but frequently hallucinated or garbled Pāḷi. Examples from the run:
- "pāṇātipātā veramaṇī sikkhāpadaṃ samādiyāmi" for a sutta about lying (wrong precept)
- "kāva matta-paññā saṅgha-samūha anāgati-dhammā" for "spiritual friend" (invented compounds)
- "sīla samādhi paññā niścaya" for Kālāma sutta (generic, misses the actual terms)

The model cannot reliably generate correct Pāḷi terminology. A curated doctrinal term dictionary or fine-tuning would be needed to fix the remaining misses.

---

## Commits this session

- `d407e93` — `feat: add rrf_fuse_multi for multi-list reciprocal rank fusion`
- `f9877b7` — `fix: document first-seen payload policy in rrf_fuse_multi, add tests`
- `2ebea5b` — `fix: replace first-seen dense dedup with rrf_fuse_multi for proper ranking`
- `909e4a7` — `style: use module-level patch import in test`
- `d9b6d38` — `feat: add ExpansionPrompt v2 with structured Pali term cluster line, switch pipeline default`
- `11cb4bc` — `fix: ExpansionPrompt defaults to v2, raises ValueError on unknown version`
- `5eef4a0` — `feat: add --log-variants flag to retrieval benchmark`
- `72ad9a5` — `fix: warn when --log-variants used without --with-expansion`
- `5af0680` — `docs: note --with-bm25 benchmark uses single query, not comparable to --with-expansion`
- `7fff85f` — `fix: inject BM25Retriever into expansion benchmark path (was dense-only)`

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
                                    CrossEncoder rerank
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

### DONE — Curated Pāḷi term dictionary

`backend/app/services/pali_dictionary.py` — 51 entries, keyword → Pāḷi cluster. `lookup(original_query)` called in `expand_query()` after LLM variants; appends deterministic 3rd variant when matched. 130 tests pass (10 new unit + 2 integration).

### MN 61 regression — unresolved

Dictionary has the right musāvādā entry, but the LLM still generates pāṇātipātā variants which drown out the correct BM25 signal. The dictionary hit alone is not strong enough to overcome this. Next option: fine-tune or swap the expansion model.

### Remaining hard misses (5 cases — unchanged)

MN 21, SN 12.1, AN 3.65, DN 31, SN 22.59 still not retrieved. Dictionary entries exist for all five but didn't move the needle in this run — the LLM variants are still generating enough noise to suppress them. The ceiling appears to be the expansion model quality. Next option: a model with stronger Pāḷi/Buddhist training (e.g. a fine-tuned Mistral or dedicated Buddhist NLP model).

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
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks fused candidate pool; has zero effect on recall@10 (reorders, doesn't recover)
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
- **PaliDictionary / lookup** — `pali_dictionary.py`; ~55 `DictionaryEntry` objects (label, keywords, pali); `lookup(query)` lowercases and keyword-matches, returns Pāḷi cluster string or `None`; called in `expand_query()` to append a deterministic 3rd variant
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
