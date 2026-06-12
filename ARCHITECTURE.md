# PCAIsearch — Architecture Reference

A Retrieval-Augmented Generation (RAG) system for semantic search over the Pāḷi Canon. Users submit natural-language or Pāḷi questions; the system retrieves relevant sutta verses and streams a grounded, cited answer.

**Corpus:** 11 nikāyas (DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP) translated by Thanissaro Bhikkhu, sourced from the dhammatalks.org epub. ~134K verse-level chunks stored in Qdrant Cloud.

---

## System Overview

```
User query
    │
    ▼
[Frontend — Next.js]
    │  GET /api/stream (SSE proxy route)
    ▼
[Backend — FastAPI]
    │
    ├─ expand_query()            ← Gemma 3n via NVIDIA API
    │      ├─ LLM expansion (English vocab + Pāḷi terms)
    │      ├─ pali_dictionary lookup (Pāḷi terms)
    │      └─ pali_dictionary English hint
    │
    ├─ Retriever.retrieve()      ← Qdrant Cloud (134K vectors, 384-dim)
    │      └─ paraphrase-multilingual-MiniLM-L12-v2 embeddings
    │
    ├─ BM25Retriever.retrieve()  ← in-memory BM25Okapi over English text
    │
    ├─ rrf_fuse_multi()          ← Reciprocal Rank Fusion
    │
    ├─ Reranker.rerank_multi()   ← ms-marco-MiniLM-L-6-v2 cross-encoder
    │
    ├─ stream_synthesize()       ← Llama 3.1 8B via NVIDIA API
    │
    └─ CitationGuardrail         ← deterministic citation verification
```

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

The `/stream` endpoint emits three SSE event types: `status` (progress text), `chunk` (incremental text delta), and `done` (full verified payload including `context`, `hallucinations`, `canonical_misses`, `is_faithful`). The three status messages in order are: `"Searching the Canon…"`, `"Composing answer…"`, `"Verifying sources…"`.

Nginx SSE buffering is disabled via `X-Accel-Buffering: no` + `Cache-Control: no-cache` headers on `/stream` responses.

---

### `SearchPipeline` — `backend/app/services/search_pipeline.py`

The RAG orchestrator. All retrieval and synthesis flows through this class.

**Constructor dependencies (injectable):**
- `qdrant_url` / `QDRANT_URL` env var
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

**`search(query, top_k, nikayas) → List[dict]`**

Takes two paths depending on whether one or multiple nikāyas are selected.

**Single-nikaya path:**
1. `expand_query` and the first `Retriever.retrieve()` run in parallel via `asyncio.gather`.
2. Optional title boost: `SuttaTitleIndex.search()` appends the top matching sutta's title text as an extra retrieval query.
3. Remaining query variants retrieved concurrently.
4. `rrf_fuse_multi()` merges all dense result lists.
5. BM25 retrieval: all query variants scored, best score per ID kept, then `rrf_fuse()` merges with the dense-fused list.
6. Reranking: `rerank_multi([original_query, english_hint])` scores all candidates; Pāḷi variants excluded (cross-encoder is English-only).

**Multi-nikaya path:**
1. `expand_query` and one initial `Retriever.retrieve()` per nikaya all run in parallel.
2. Title boost applied.
3. BM25 runs once across all nikayas, then results are split by nikaya — avoids ~11× redundant scoring.
4. The full pipeline (retrieve → fuse → rerank) runs independently per nikaya in parallel.
5. Per-nikaya result lists are **round-robin interleaved** — one result from each nikaya in turn — so a large nikaya (SN) cannot crowd out a small one (KHP).

Retrieval over-fetches at `max(top_k * 3, 30)` candidates per nikaya before reranking.

**`stream_synthesize(query, context_chunks)`**

Builds the LLM context by formatting each chunk as `[ID] Pali: ... English: ...` (chunks with fewer than 4 English words are filtered). Streams from Llama 3.1 8B, yielding `{"type": "chunk", "text": delta}` events and a final `{"type": "full", "text": full_text}`.

---

### `Retriever` — `backend/app/services/retriever.py`

Wraps the Qdrant async client for dense vector retrieval.

- Encodes the query string into a 384-dim vector using `EmbeddingManager` (run in a thread pool executor to avoid blocking the event loop).
- Applies an optional `nikaya` keyword filter on the Qdrant `nikaya` payload field.
- Returns a list of `{id, pali, english, score}` dicts, filtering out chunks with empty English text.

The collection name is `pali_canon`. The embedding model is `paraphrase-multilingual-MiniLM-L12-v2` (via fastembed / ONNX Runtime, loaded once at startup into `EmbeddingManager`).

---

### `BM25Retriever` — `backend/app/services/bm25_retriever.py`

In-memory BM25 (Okapi BM25) over all English verse text, loaded from `data/dumps/` at startup.

- Runs in a thread pool executor (CPU-bound scoring).
- In the multi-nikaya path, BM25 runs once across the full corpus and results are split by nikaya tag — avoids redundant scoring per nikaya.
- Scores are fused with dense results via `rrf_fuse()` (Reciprocal Rank Fusion).

---

### `SuttaTitleIndex` — `backend/app/services/sutta_title_index.py`

BM25 over sutta titles and their opening verses (verses 3–15). When the user's query matches a canonical title (e.g. "Satipatthana Sutta"), the matched sutta's title text is appended as an extra retrieval query to boost its verses to the top.

---

### `CitationOracle` — `backend/app/services/citation_oracle.py`

Answers "does this `[ID:Verse]` citation exist in the canon?" by building a registry of all known sutta IDs and verse numbers from `data/dumps/` at startup. Used by `CitationGuardrail` to distinguish true hallucinations from canonical misses.

---

### `CitationGuardrail` — `backend/app/services/guardrail.py`

Post-generation verification layer. After synthesis, scans the generated text for `[ID:Verse]` citations and classifies each:

- **In retrieved context** → left as-is.
- **In the canon but not retrieved** → relabelled `[Unverified]` (`canonical_miss`).
- **Not in the canon at all** → relabelled `[Hallucinated]` (`hallucination`).

Returns `{text, hallucinations, canonical_misses, is_faithful}`. `is_faithful` is `True` only when there are zero hallucinations.

---

### `SuttaRelations` — `backend/app/services/sutta_relations.py`

Returns canonically related sutta IDs for the "see also" list returned by `/search`. Combines:
- A hardcoded table of ~15 doctrinal pairs (e.g. DN 22 ↔ MN 10, MN 63 ↔ MN 72).
- Structural adjacency: the ±2 numeric neighbors within the same nikāya.

Only returns IDs that exist in the known sutta set (from `CitationOracle`).

---

### `PaliDictionary` — `backend/app/services/pali_dictionary.py`

Keyword-matched lookup table with ~84 entries covering major doctrinal lists (e.g. eightfold path, five aggregates, dependent origination). Given a query, returns:
- `lookup(query)` → Pāḷi terms string, used as a 4th search variant.
- `lookup_english(query)` → verbatim English passage hint (Thanissaro-style), used as a 5th search variant and as the second reranking query.

This bridges vocabulary gaps for the cross-encoder, which is English-only and would otherwise score Pāḷi terms as noise.

---

## Deployment

| Service | Role | Notes |
|---------|------|-------|
| DigitalOcean App Platform | Backend | `pcaisearch-jol64.ondigitalocean.app`; auto-deploys from `main` branch; `LLM_MODEL` env var set to `meta/llama-3.1-8b-instruct` |
| Netlify | Frontend | `illustrious-biscotti-f60464.netlify.app`; `NEXT_PUBLIC_API_URL` (for non-stream endpoints), `API_URL` (for SSE proxy) |
| Qdrant Cloud | Vector DB | Free tier; 134,102 vectors, 384-dim, cosine; `pali_canon` collection; nikaya keyword payload index |
| NVIDIA Inference API | LLM inference | Free tier; Gemma 3n for expansion, Llama 3.1 8B for synthesis |
| Supabase | Feedback store | Free tier; stores user feedback (query, answer, rating, category, comment); RLS enabled, service_role key only; read via Supabase dashboard |

---

## Frontend — `frontend/`

Next.js (App Router). Two routes:

- `/` — home page with `SearchBar`; submitting navigates to `/search/[query]`.
- `/search/[query]` — results page. Fetches search results and streams synthesis in parallel.

**Key components:**

| Component | File | Role |
|-----------|------|------|
| `SearchBar` | `components/search/SearchBar.tsx` | Home search input |
| `NavSearchBox` | `components/search/NavSearchBox.tsx` | In-page search box on the results page |
| `NikayaFilter` | `components/search/NikayaFilter.tsx` | Nikaya selector; click = single, ⌘/Ctrl-click = multi |
| `SearchResultsLoader` | `components/search/SearchResultsLoader.tsx` | Fetches `/search`, renders `SearchResultsView` |
| `SearchResultsView` | `components/search/SearchResultsView.tsx` | Displays ranked verse cards |
| `DualPaneContainer` | `components/deep-dive/DualPaneContainer.tsx` | Side-by-side synthesis + sources layout |
| `SynthesisLoader` | `components/deep-dive/SynthesisLoader.tsx` | Manages SSE stream state, streams to `SynthesisView` |
| `SynthesisView` | `components/deep-dive/SynthesisView.tsx` | Renders streamed answer text with citations |
| `SourceViewer` | `components/deep-dive/SourceViewer.tsx` | Renders retrieved verse context cards |
| `FeedbackBar` | `components/deep-dive/FeedbackBar.tsx` | Thumbs up/down; POSTs to `/feedback` |
| `SupportBanner` | `components/SupportBanner.tsx` | Dismissable info banner; state in React context |
| `ContactModal` | `components/ContactModal.tsx` | Modal for contacting the developer |

The SSE stream (`GET /api/stream`) is proxied through a Next.js API route to avoid CORS issues. The frontend uses Tailwind CSS.

---

## Data Pipeline

### 1. Download — `data/fetch_thanissaro.py`

Downloads Thanissaro Bhikkhu's translations from the dhammatalks.org epub and writes one JSON file per sutta to `data/dumps/`. Clears existing dumps before writing. Output format:

```json
{
  "sutta_id": "MN1",
  "verses": [
    {"number": 1, "pali": "Middle Length Discourses 1", "english": "Middle Length Discourses 1"},
    {"number": 2, "pali": "", "english": "The Root of All Things"},
    {"number": 3, "pali": "", "english": "First prose paragraph..."},
    ...
  ]
}
```

Body verses have empty `pali` fields — only English text is available from this source.

### 2. Index — `data/process_dumps.py`

Reads `data/dumps/*.json`, embeds verse-level chunks with `EmbeddingManager`, and upserts into the `pali_canon` Qdrant collection. Resume-capable: already-indexed sutta IDs are detected via a full scroll of the collection and skipped. Run with `--wipe` to drop and rebuild from scratch.

Point IDs are deterministic `uuid5` hashes of the chunk's `id` field, so re-running is idempotent.

### 3. Chunk format

Each Qdrant point payload is a dict with:
- `id` — verse-level identifier, e.g. `"MN 1:3"` (nikāya, sutta number, verse number)
- `pali` — Pāḷi text (empty for Thanissaro-sourced data)
- `english` — English text
- `nikaya` — nikāya tag (e.g. `"MN"`), used for filtered queries

---

## Testing

Backend tests live in `tests/backend/`. Run a single test file with:

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_foo.py -q
```

The recall benchmark (`tests/backend/retrieval_benchmark.py`) runs 15 representative queries through the full pipeline and reports recall@10. It requires live Qdrant and NVIDIA API access:

```bash
PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants
```
