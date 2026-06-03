# PCAIsearch — Architecture Reference

A Retrieval-Augmented Generation (RAG) system for semantic search over the Pāḷi Canon (~4,691 suttas, ~134K verse-level chunks). Users submit natural-language or Pāḷi questions; the system retrieves relevant sutta verses and streams a grounded, cited synthesis.

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
    ├─ stream_synthesize()     ← Llama 3.3 70B via NVIDIA API
    │
    └─ CitationGuardrail       ← deterministic citation verification
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

The `/stream` endpoint emits three SSE event types: `status` (progress text), `chunk` (incremental text delta), and `done` (full verified payload including `context`, `hallucinations`, `canonical_misses`, `is_faithful`). The three status messages emitted in order are: `"Searching the Canon…"`, `"Composing answer…"`, and `"Verifying sources…"` (the last is emitted just before the guardrail runs).

---

### `SearchPipeline` — `backend/app/services/search_pipeline.py`

The RAG orchestrator. All retrieval and synthesis flows through this class.

**Constructor dependencies (injectable):**
- `qdrant_url` / `QDRANT_URL` env var — Qdrant Cloud cluster URL
- `llm_model` / `LLM_MODEL` env var — synthesis model (default: `meta/llama-3.3-70b-instruct`; production override: `meta/llama-3.1-8b-instruct`)
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

Model output is stripped of `<think>...</think>` blocks and line-label prefixes (e.g. `"Line 1: "`) before parsing.

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

**Multi-nikaya path:**
1. `expand_query` and one initial `Retriever.retrieve()` per nikaya all run in parallel via `asyncio.gather` — expansion and all per-nikaya Qdrant calls overlap.
2. Title boost applied (same as single-nikaya).
3. BM25 runs once across all nikāyas (not once per nikaya), then results are split by nikaya — avoids ~6× redundant scoring of the full corpus.
4. The full pipeline (retrieve → fuse → rerank) runs independently per nikaya in parallel via `asyncio.gather`, each receiving its share of pre-fetched BM25 results.
5. Per-nikaya result lists are round-robin interleaved — one result from each nikaya in turn — so a large nikaya (e.g. SN) cannot crowd out a small one (e.g. DHP).

Retrieval over-fetches at `max(top_k * 3, 30)` candidates per nikaya before reranking.

**`stream_synthesize(query, context_chunks)`**

Builds the LLM context by formatting each chunk as `[ID] Pali: ... English: ...` (chunks with fewer than 4 English words are filtered). Streams from Llama 3.3 70B, yielding `{"type": "chunk", "text": delta}` events and a final `{"type": "full", "text": full_text}`.

---

### `ExpansionPrompt` — `backend/app/services/search_pipeline.py`

Versioned query expansion prompts (v1–v7). The current default is **v7**, which instructs the model to output exactly two unlabeled lines: English passage vocabulary and Pāḷi terminology. v7 hardens the system prompt and adds 24 named canonical simile entries (raft simile, blind men, arrow simile, etc.) so simile queries expand correctly. It also includes a reference table mapping doctrinal topics to both English hint words (drawn from the actual sutta text) and Pāḷi terms, and instructs the model to use the hint words even when they seem unrelated to the query's surface form.

---

### `Retriever` — `backend/app/services/retriever.py`

Dense vector retrieval against the Qdrant `pali_canon` collection.

- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim, multilingual — handles both English queries and Pāḷi terms)
- Embedding is computed in a `ThreadPoolExecutor` (CPU-bound) and awaited via `run_in_executor`
- Optional `nikayas` filter uses a Qdrant `MatchAny` condition on the `nikaya` payload field (requires the keyword payload index created at startup)
- Returns dicts with keys: `id`, `pali`, `english`, `score`

---

### `BM25Retriever` — `backend/app/services/bm25_retriever.py`

Sparse keyword retrieval using `BM25Okapi` over lowercase alphabetic tokens from English verse text.

- Built at startup from all JSON dumps via `SuttaParser`
- Holds all verses in memory (~38MB of JSON → in-memory corpus)
- `retrieve()` applies post-hoc nikaya filtering after scoring (no index-level filter)
- Only results with `score > 0` are returned
- Built via `BM25Retriever.from_directory(dumps_dir)`

---

### `fusion.py` — RRF Implementation

`rrf_fuse(dense, sparse, k=60)` — merges two ranked lists using Reciprocal Rank Fusion: score = Σ 1/(k + rank). Payload from the first list wins on collision.

`rrf_fuse_multi(lists, k=60)` — generalizes to N lists; same scoring formula applied per list.

---

### `Reranker` — `backend/app/services/search_pipeline.py`

Cross-encoder reranking using `cross-encoder/ms-marco-MiniLM-L-6-v2`.

`rerank_multi(queries, chunks)` scores each candidate against every query and takes the maximum score. The text fed to the cross-encoder is `"{pali} {english}"` concatenated. This model is trained on English MS MARCO passages — Pāḷi text is opaque to it, so only `[original_query, english_hint]` are passed as reranking queries. The English hint (verbatim passage text from `pali_dictionary.lookup_english`) bridges vocabulary gaps the model can exploit (e.g. the dictionary entry for "one precept" maps to `"deliberate lie"`, the actual sutta phrasing).

---

### `pali_dictionary` — `backend/app/services/pali_dictionary.py`

Keyword-matched lookup table with ~77 `DictionaryEntry` records covering major doctrinal lists. Each entry has:
- `keywords` — trigger strings (plain text, diacritics, abbreviations)
- `pali` — space-separated Pāḷi term cluster for retrieval
- `english_hint` — verbatim passage-level English text for reranking

`lookup(query)` — returns the `pali` string of the first matching entry using word-boundary regex matching.  
`lookup_english(query)` — same matching, returns `english_hint`.

Both functions use `re.search` with `\b`-bounded patterns to avoid spurious substring matches.

---

### `CitationOracle` — `backend/app/services/citation_oracle.py`

Loads the sutta registry at startup by parsing all JSON dumps. Builds `registry: Dict[str, Set[int]]` mapping canonical sutta IDs (e.g. `"MN 27"`) to their set of verse numbers.

`citation_in_canon(citation)` — parses `"MN 27:14"` format and checks both the sutta and verse number exist in the registry.

`known_suttas` property — the full set of indexed sutta IDs; used to seed `SuttaRelations`.

---

### `CitationGuardrail` — `backend/app/services/guardrail.py`

Post-generation citation verification. Scans LLM output for `[ID:Verse]` patterns and classifies each:
- **in retrieved context** → kept as-is
- **in canon, not in context** → replaced with `[Unverified]` (`canonical_misses`)
- **not in canon at all** → replaced with `[Hallucinated]` (`hallucinations`)

`is_faithful` is `True` only if `hallucinations` is empty.

---

### `SuttaRelations` — `backend/app/services/sutta_relations.py`

Returns related sutta IDs for the "see also" feature. Two sources:
1. Hardcoded doctrinal pairs (e.g. DN 22 ↔ MN 10 for Satipaṭṭhāna)
2. Structural adjacency: ±2 numeric neighbors within the same nikāya

Only IDs present in `known_suttas` are returned.

---

### `SuttaTitleIndex` — `backend/app/services/sutta_title_index.py`

BM25 index over sutta titles and body text (verses 3–15). Used to boost retrieval when a query matches a canonical sutta name. If the English title is a chapter header (matches `^\d+\. `), falls back to the v3 (section title) verse.

`search(query, top_n)` — returns `(sutta_id, score)` pairs; only scores > 0 returned.

---

### `EmbeddingManager` / `SuttaParser` — `backend/app/core/indexing.py`

`EmbeddingManager` — wraps `fastembed.TextEmbedding` (ONNX Runtime backend for CPU compatibility). The multilingual MiniLM model outputs 384-dimensional cosine-distance vectors. `encode()` returns a Python list suitable for Qdrant.

`SuttaParser` — converts raw SuttaCentral JSON (keyed `sutta_id`, `verses` array) into canonical chunks with keys `id`, `nikaya`, `pali`, `english`. IDs are formatted as `"{NIKAYA} {number}:{verse}"`.

---

### Corpus Data — `data/dumps/`

38MB of JSON files (one per sutta, ~4,691 files) committed to the repo. Format per file:
```json
{
  "sutta_id": "mn27",
  "verses": [
    {"number": 1, "pali": "...", "english": "..."},
    ...
  ]
}
```
Loaded at startup by `BM25Retriever`, `CitationOracle`, and `SuttaTitleIndex`. The Qdrant collection (134,102 vectors) is pre-built and hosted on Qdrant Cloud — it is not rebuilt on each deploy.

---

### Feedback Storage — `feedback.db`

SQLite file at `backend/feedback.db`. Schema:
```sql
CREATE TABLE feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    query      TEXT NOT NULL,
    answer     TEXT NOT NULL,
    rating     TEXT NOT NULL,      -- 'up' | 'down'
    category   TEXT,               -- one of 5 downvote categories
    comment    TEXT,
    created_at TEXT NOT NULL       -- ISO 8601 UTC
)
```
Written via `run_in_executor` to avoid blocking the async event loop. No admin UI; inspect via `sqlite3 feedback.db`.

---

## Frontend

Next.js (App Router) application deployed on Netlify.

### Routing

| Route | File | Description |
|-------|------|-------------|
| `/` | `app/page.tsx` | Landing page with `SearchBar` |
| `/search/[query]` | `app/search/[query]/page.tsx` | Results page: source cards + streaming synthesis |
| `/api/stream` | `app/api/stream/route.ts` | SSE proxy to backend `/stream` (required in production; avoids CORS on streaming) |

### API Layer — `lib/api.ts`

`API_BASE` resolves to `/api` in the browser (routes through the Next.js proxy) or `http://localhost:8000` on the server side. In production, `NEXT_PUBLIC_API_URL` overrides this.

- `searchVerses(query, topK, nikayas)` — `GET /search`
- `streamSynthesis(query, nikayas)` — async generator over SSE frames from `GET /api/stream`
- `submitFeedback(payload)` — `POST /feedback`

### Component Tree (Search Results Page)

```
app/search/[query]/page.tsx
  └─ DualPaneContainer
       ├─ left pane: SearchResultsView (source cards, NikayaFilter)
       │    └─ NikayaFilter (DN/MN/SN/AN/DHP/ITI checkboxes)
       ├─ DividerToggle (collapse/expand left pane)
       └─ right pane: SynthesisLoader → SynthesisView
            ├─ StepList (live pipeline step progress — pending/active/done states driven by SSE status events)
            ├─ streams answer text via streamSynthesis()
            ├─ FeedbackBar (thumbs up/down, 5-category downvote)
            └─ SourceViewer (cited chunk cards with SuttaCentral links)
```

`StepList` — replaces the pre-streaming spinner. Displays the three pipeline steps ("Searching the Canon…", "Composing answer…", "Verifying sources…") as a step-by-step progress indicator. Each step transitions through pending → active → done states as SSE `status` events arrive. Renders horizontally on desktop and vertically on mobile; persists as a sidebar/topbar widget while the answer streams.

`DividerToggle` — draggable/clickable divider that collapses the source pane to reveal the full synthesis pane.

`FeedbackBar` — three-state UI (idle → voted → submitted). Downvote expands a category picker and optional comment field. Submits via `submitFeedback()`.

### SSE Proxy — `app/api/stream/route.ts`

Forces `dynamic = 'force-dynamic'` to prevent Next.js from caching. Proxies the response body stream directly to the client with `no-cache, no-transform` and `X-Accel-Buffering: no` headers. Backend URL configured via `API_URL` env var (server-side only).

---

## Deployment

| Service | Role | Notes |
|---------|------|-------|
| DigitalOcean 2GB Droplet | Backend (Docker) | `NVIDIA_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `CORS_ORIGINS` set as secrets |
| Netlify | Frontend | `NEXT_PUBLIC_API_URL` (for non-stream endpoints), `API_URL` (for SSE proxy) |
| Qdrant Cloud | Vector DB | 134,102 vectors, 384-dim, cosine; `pali_canon` collection; nikaya keyword payload index |
| NVIDIA Inference API | LLM inference | Free tier, 40 rpm; Gemma 3n for expansion, Llama 3.1 8B for synthesis (set via `LLM_MODEL` env var) |

Nginx buffering is disabled on the DigitalOcean Droplet via `X-Accel-Buffering: no` + `Cache-Control: no-cache` headers on the `/stream` response, which is required for SSE to flow without batching.

---

## Test Suite

Located in `tests/backend/`. Run with:
```
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Key test modules:
- `test_search_pipeline.py` — pipeline integration using in-memory Qdrant
- `test_guardrail.py` — citation classification logic
- `test_pali_dictionary.py` — keyword matching and word-boundary correctness
- `test_fusion.py` — RRF score computation
- `test_bm25_retriever.py` — BM25 retrieval and nikaya filtering
- `test_citation_oracle.py` — registry loading and verse existence checks
- `test_sutta_relations.py` — doctrinal pairs and adjacency
- `retrieval_benchmark.py` — recall@10 benchmark (93% on 15-query set); run with `--with-expansion --log-variants`

Pipeline internals are accessed in tests via `pipeline.retriever.client` and `pipeline.retriever.embedding_mgr` (not through pipeline-level aliases, which were removed).

---

## Known Architectural Constraints

- `_SYSTEM_PROMPT` in `search_pipeline.py` is a module-level constant — not injectable for testing. Extract a `PromptBuilder` only if prompt variant testing becomes necessary.
- BM25 nikaya filtering is post-scoring (no inverted-index-level filter). For large nikaya exclusions this is wasteful but acceptable at current corpus size.
- The cross-encoder (`ms-marco-MiniLM-L-6-v2`) is English-only. Pāḷi variants from query expansion are used for dense + BM25 retrieval only; they are never passed to the reranker.
- The Qdrant collection is not rebuilt on deploy — corpus updates require a separate migration run.
