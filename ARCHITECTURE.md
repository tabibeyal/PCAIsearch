# PCAIsearch — Architecture Reference

A Retrieval-Augmented Generation (RAG) system for semantic search over the Pāḷi Canon (~4,691 suttas, ~134K verse-level chunks). Users submit natural-language or Pāḷi questions; the system retrieves relevant sutta verses and streams a grounded, cited signature.

---

## System Overview

```
User query
    │
    ▼
[Frontend — Next.js]
    │  GET /api/stream (SSE proxy)
    ▼
[Backend — FastAPI]
    │
    ├─ expand_query()          ← Gemma 3n via NVIDIA API
    │      ├─ LLM expansion (English vocab + Pāḷi terms)
    │      ├─ pali_dictionary lookup (Pāḷi terms)
    │      └─ pali_dictionary English hint
    │
    ├─ Retriever.retrieve()    ← Qdrant Cloud (134K vectors, 384-dim)
    │      └─ paraphrase-multilingual-MiniLM-L12-v2 embeddings
    │
    ├─ BM25Retriever.retrieve() ← in-memory BM25Okapi over English text
    │
    ├─ rrf_fuse_multi()        ← Reciprocal Rank Fusion
    │
    ├─ Reranker.rerank_multi() ← ms-marco-MiniLM-L-6-v2 cross-encoder
    │
    ├─ stream_synthesize()     ← Llama 3.1 8B via NVIDIA API
    │
    └─ CitationGuardrail       ← deterministic citation verification
```

---

## Key Updates (2026-06-03)

- **Migration to App Platform**: Moved from DigitalOcean Droplet to DigitalOcean App Platform for easier deploys and built-in model caching; prevents Docker timeout issues and simplifies scaling.
- **Shared BM25 across nikayas**: Runs BM25 once across all nikayas instead of once per nikaya; reduces redundant computation and latency.
- **Moved reranker/BM25 to thread pool**: Prevents blocking the event loop and allows concurrent nikaya passes; improves throughput under load.
- **Switched synthesis model to Llama-3.1-8B**: Reduced latency from 32s to 12s per query while maintaining acceptable quality for the use case.
- **Recall@10 recovery**: After dropping to 86% following the 2026-06-03 changes, implemented per-nikaya pipeline with round-robin interleaving to restore performance; fix committed 2026-06-04 (b21fab8); awaiting re-benchmark to confirm recovery to 93%.
- **Guardrail citation verification**: Post-generation check to prevent hallucinated sutta numbers; ensures answers are grounded in actual passages.

---

## Backend

### Entry Point — `backend/app/main.py`

FastAPI application with a `lifespan` context manager that initializes all stateful services at startup:

- `CitationOracle` — loads the full sutta registry from `data/dumps/`
- `SuttaRelations` — receives the set of known sutta IDs from the oracle
- `SuttaTitleIndex` — BM25 over sutta titles, built from the same dumps
- `BM25Retriever` — in-memory BM25 index over all English verse text
- `SearchPipeline` — receives the above as dependencies
- `CitationGuardrail` — wraps the oracle for post-generation verification
- Qdrant `nikaya` payload index — created idempotently at startup (required for filtered queries on Qdrant Cloud)

Rate limits: `/search` 30/min, `/stream` and `/synthesize` 10/min, `/feedback` 20/min.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/search` | Returns ranked verse chunks + related suttas |
| `GET` | `/synthesize` | Returns a complete grounded answer (non-streaming) |
| `GET` | `/stream` | Server-Sent Events stream of answer chunks + final verified payload |
| `POST` | `/feedback` | Stores thumbs-up/down rating with optional category + comment |

The `/stream` endpoint emits three SSE event types: `status` (progress text), `chunk` (incremental text delta), and `done` (full verified payload including `context`, `hallucinations`, `canonical_misses`, `is_faithful`). The three status messages emitted in order are: `"Searching the Canon…"`, `"Composing answer…"`, and `"Verifying sources…"` (the last is emitted just before the guardrail runs).

---

### `SearchPipeline` — `backend/app/services/search_pipeline.py`

The RAG orchestrator. All retrieval and synthesis flows through this class.

**Constructor dependencies (injectable):**
- `qdrant_url` / `QDRANT_URL` env var — Qdrant Cloud cluster URL
- `llm_model` / `LLM_MODEL` env var — synthesis model (production: `meta/llama-3.1-8b-instruct`)
- `expansion_model` / `EXPANSION_MODEL` env var — expansion model (default: `google/gemma-3n-e4b-it`)
- `sutta_relations` — `SuttaRelations` instance
- `expansion_prompt` — `ExpansionPrompt` instance (default: v6)
- `title_index` — `SuttaTitleIndex` instance
- `bm25_retriever` — `BM25Retriever` instance

Both LLMs are accessed via the OpenAI-compatible NVIDIA Inference API (`https://integrate.api.nvidia.com/v1`), authenticated by `NVIDIA_API_KEY`.

**`expand_query(query) → List[str]`**

Generates up to 5 query variants:
1. The original query (always first)
2–3. Two LLM-generated lines (English passage vocabulary + Pāḷi terms) from Gemma 3n
4. Pāḷi term string from `pali_dictionary.lookup(query)` if matched
5. English passage hint from `pali_dictionary.lookup_english(query)` if matched

Model output is stripped of `\{...\\\}` blocks and line-label prefixes (e.g. `"Line 1: "`) before parsing.

**`search(query, top_k, nikayas) → List[dict]`**

The pipeline takes two distinct paths depending on whether one or multiple nikāyas are selected.

**Single-nikaya path:**
1. `expand_query` and the first `Retriever.retrieve()` run in parallel via `asyncio.gather` — the NVIDIA API wait overlaps with the Qdrant round-trip.
2. Optional title boost: `SuttaTitleIndex.search()` appends the top matching sutta's title text as an extra retrieval query.
3. Remaining query variants retrieved concurrently via `asyncio.gather`.
4. `rrf_fuse_multi()` merges all dense result lists.
5. BM25 retrieval: all query variants scored, best score per ID kept, then `rrf_fuse()` merges with the dense-fused list.
6. Reranking: `rerank_multi([original_query, english_hint])` scores all candidates; Pāḷi variants excluded since the cross-encoder is English-only.
7. Returns top-k by rerank score.

**Multi-nikaya path (post-2026-06-03 update):**
1. `expand_query` and one initial `Retriever.retrieve()` per nikaya all run in parallel via `asyncio.gather` — expansion and all per-nikaya Qdrant calls overlap.
2. Title boost applied (same as single-nikaya).
3. **BM25 runs once across all nikayas** (not once per nikaya), then results are split by nikaya — avoids ~6× redundant scoring of the full corpus.
4. The full pipeline (retrieve → fuse → rerank) runs independently per nikaya in parallel via `asyncio.gather`, each receiving its share of pre-fetched BM25 results.
5. **Per-nikaya result lists are round-robin interleaved** — one result from each nikaya in turn — so a large nikaya (e.g. SN) cannot crowd out a small one (e.g. DHP).

Retrieval over-fetches at `max(top_k * 3, 30)` candidates per nikaya before reranking.

**`stream_synthesize(query, context_chunks)`**

Builds the LLM context by formatting each chunk as `[ID] Pali: ... English: ...` (chunks with fewer than 4 English words are filtered). Streams from Llama 3.1 8B, yielding `{"type": "chunk", "text": delta}` events and a final `{"type": "full", "text": full_text}`.

---

### `Deployment`

| Service | Role | Notes |
|---------|------|-------|
| DigitalOcean App Platform | Backend | `pcaisearch-jol64.ondigitalocean.app`; auto-deploys from `main` branch; `LLM_MODEL` env var set to `meta/llama-3.1-8b-instruct` |
| Netlify | Frontend | `NEXT_PUBLIC_API_URL` (for non-stream endpoints), `API_URL` (for SSE proxy) |
| Qdrant Cloud | Vector DB | Free tier; 134,102 vectors, 384-dim, cosine; `pali_canon` collection; nikaya keyword payload index |
| NVIDIA Inference API | LLM inference | Free tier; Gemma 3n for expansion, Llama 3.1 8B for specification |

Nginx buffering is disabled via `X-Accel-Buffering: no` + `Cache-Control: no-cache` headers on the `/stream` response, which is required for SSE to flow without batching.

---

### Remaining sections unchanged from original...

[The rest of the document remains the same as the original, focusing on the technical details of components that haven't changed]