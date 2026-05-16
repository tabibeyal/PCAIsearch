# Handoff — Session 2026-05-16 (retrieval benchmark investigation)

## What happened this session

Three sub-sessions of work:

**Sub-session 1 — BM25 hybrid retrieval (previous):** Built BM25 retrieval fused with dense results via RRF.

**Sub-session 2 — nikayas filter parity:** Fixed `BM25Retriever.retrieve()` ignoring the `nikayas` restriction.

**Sub-session 3 — benchmark investigation (this session):**
- Loosened the benchmark gold standard to accept multiple valid suttas per query (many doctrinal topics live in several suttas simultaneously).
- Diagnosed why the expansion pipeline underperforms BM25+dense.
- Fixed BM25 to run on all expanded query variants (not just original).
- Measured all pipeline modes end-to-end.

---

## Recall@10 scoreboard

| Mode | Hard | Medium | Easy | Total |
|------|------|--------|------|-------|
| Dense only | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| **BM25 + dense** | **4/5** | **2/5** | **1/5** | **7/15 (46%)** |
| Expansion + rerank | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| Expansion + no rerank | 3/5 | 1/5 | 0/5 | 4/15 (26%) |

BM25+dense (no expansion) is the current recall ceiling.

### Why expansion hurts recall

Expansion generates 3 query variants → 3 × 30 = 90 dense candidates before dedup. BM25 contributes ~30 candidates. Dense dominates the RRF pool 3:1. BM25 hits that rank well (e.g. SN 45.2 at BM25 rank 1) get buried by dense cluster accumulation.

The reranker (CrossEncoder) has **zero effect** on recall@10 — it reorders within the pool but doesn't recover missed items.

### Three queries both retrievers miss entirely (top 50)

These cannot be fixed by fusion tuning:
- **MN 21** — "should a monk feel anger if attacked with a saw" (saw simile)
- **SN 12.1** — "how does ignorance cause suffering step by step"
- **AN 3.65** — "how do you know whether a religious teaching is worth following" (Kālāma)

They need either better embeddings or a domain-specific term index (Pāḷi doctrinal cluster lookup).

---

## Commits this session

- `7aee672` — `fix: apply nikayas filter to BM25Retriever to match dense retrieval`
- `90498e1` — `test: loosen benchmark gold standard to accept multiple valid suttas`
- `8bf88e2` — `feat: run BM25 on all expanded query variants, add --no-rerank benchmark flag`

---

## What was built (cumulative)

### Files

| File | Purpose |
|------|---------|
| `backend/app/services/bm25_retriever.py` | `BM25Retriever` — BM25Okapi over English verses; `retrieve(query, top_k, nikayas=None)`; `from_directory(dumps_dir)` |
| `backend/app/services/fusion.py` | `rrf_fuse(dense, sparse, k=60)` — Reciprocal Rank Fusion |
| `tests/backend/test_bm25_retriever.py` | 13 unit tests |
| `tests/backend/test_fusion.py` | 11 unit tests |
| `tests/backend/retrieval_benchmark.py` | Recall@10 benchmark; `--with-bm25`, `--with-expansion`, `--no-rerank`, `--k` flags |

### Modified files

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | BM25 injected + fused; nikayas passed through; BM25 now runs on all expanded variants (best score per verse kept) |
| `backend/app/main.py` | Builds `BM25Retriever` at startup and injects into `SearchPipeline` |
| `tests/backend/test_search_pipeline.py` | 6 tests total including nikaya filter E2E and BM25-on-variants test |

---

## Search flow (current)

```
query
  └─► expand_query → [q1, q2, q3]
        ├─► dense retrieve (Qdrant, nikayas filter) × 3 queries  ─┐
        └─► BM25 retrieve (nikayas filter) × 3 queries            ─┤
            (best bm25_score per verse kept across variants)       ▼
                                                    rrf_fuse(dense_deduped, bm25_merged)
                                                                   ▼
                                                    CrossEncoder rerank
                                                                   ▼
                                                    top_k results
```

---

## Test suite

**100 passed**, 6 pre-existing errors in `test_api.py` (missing `NVIDIA_API_KEY` in test env — unchanged).

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

---

## Open issues / next steps

### Retrieval ceiling — the 3 hard misses

MN 21, SN 12.1, AN 3.65 are absent from both dense and BM25 top 50. Candidate approaches:
- **Pāḷi doctrinal term clusters** (Phase 1.5) — inverted index of key terms (e.g. "kālāma", "dependent origination") → sutta occurrences. Would directly fix the Kālāma and dependent-origination cases.
- **Better expansion prompting** — steer the LLM to generate Pāḷi transliteration or canonical term variants.

### Expansion pipeline recall gap

Expansion + rerank = 26% vs BM25+dense = 46%. Expansion is designed for answer quality, not recall — but the gap is large enough to investigate. Next lever: log what query variants the LLM generates for the failing cases and evaluate whether they are steering retrieval correctly.

### Phase 2.5 — Public read-only API + explorer UI

`/parallels` route backed by 4–5 read-only endpoints over `data/parallels.sqlite`. Schema already shaped; ~20 LOC HTTP layer.

### Phase 2 — Vinaya ingestion (deferred)

Parser regex `r"([a-zA-Z]+)([\d.]+)"` won't match `pli-tv-bu-vb-pj1` IDs — needs extension before Vinaya can be ingested.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — dense vector retrieval against Qdrant; injectable seam (`Retriever`)
- **BM25Retriever** — in-memory BM25 over English verses; loaded from `data/dumps/` at startup; injected into `SearchPipeline`; accepts optional `nikayas` filter (post-score, full-corpus IDF); runs on all expanded query variants
- **rrf_fuse** — Reciprocal Rank Fusion of dense + BM25 results; pure function in `fusion.py`; `k=60` default
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks fused candidate pool; has zero effect on recall@10 (reorders, doesn't recover)
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
- **retrieval_k** — internal candidate pool = `max(top_k * 3, 30)`; used for dense and BM25 per query
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
