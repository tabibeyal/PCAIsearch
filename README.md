# Ask the Pali Canon

Semantic search and AI-synthesized answers over the Pali Canon (DN, MN, AN, SN, Dhammapada, Itivuttaka, Udāna, Sutta Nipāta, Theragāthā, Therīgāthā, Khuddakapāṭha), grounded in Thanissaro Bhikkhu's English translations from dhammatalks.org.

## Features

- **Semantic search** — multilingual embeddings (paraphrase-multilingual-MiniLM-L12-v2) retrieve relevant verses in English or Pali
- **Hybrid retrieval** — dense vector search fused with BM25 sparse retrieval via Reciprocal Rank Fusion; canonical suttas matched by title are surfaced even when vector search misses
- **Query expansion** — LLM generates alternative phrasings to improve recall
- **Cross-encoder reranking** — results reordered by relevance before display
- **AI Synthesis** — LLM answers your question using only retrieved context, with inline citations (`[DN 1:1]`, `[SN 46.20:14]`)
- **Citation guardrail** — distinguishes true hallucinations (non-existent sutta) from canonical misses (real sutta not in retrieved context)
- **Citation support check** (optional, off by default) — asks Jev (TypeSafe System One) whether each cited passage actually backs its sentence; unsupported citations are shown in amber
- **Scope guard** (optional, off by default) — asks Jev whether a question is about the Pali Canon before searching, and politely declines off-topic ones
- **Nikaya filter** — filter search and synthesis by collection (DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP); click to switch, ⌘/Ctrl-click to combine
- **Resume-capable indexing** — indexing can be interrupted and resumed without re-embedding

## Architecture

```
frontend/          Next.js 16 (App Router)
backend/           FastAPI + asyncio
  app/
    main.py        API endpoints (/synthesize, /stream), rate limiting
    core/
      indexing.py  SuttaParser, EmbeddingManager (fastembed / ONNX Runtime)
    services/
      search_pipeline.py   Query expansion → retrieval → reranking
      retriever.py         Dense vector retrieval (Qdrant)
      bm25_retriever.py    Sparse BM25 retrieval, fused via RRF
      sutta_title_index.py Sutta title BM25 boost
      fusion.py            Reciprocal Rank Fusion for hybrid retrieval
      guardrail.py         Citation verification (hallucination vs canonical miss)
      citation_oracle.py   Validates sutta IDs and verse numbers
      pali_dictionary.py   Pāḷi term → English passage hints for reranking
      answer_composer.py   Runs scope guard → search → synthesis → citation checks
      scope_guard.py       Optional Jev off-topic question filter
      citation_support_check.py  Optional Jev check that citations back their claims
data/
  fetch_thanissaro.py  Download Thanissaro Bhikkhu epub from dhammatalks.org → local JSON
  process_dumps.py Embed & upsert into Qdrant
scripts/
  jev_decide.py    Asks Jev the fixed wayfinder decision questions (dev tooling, used by the jev-decisions skill)
docs/adr/          Architecture decision records
docs/research/     Probe and benchmark write-ups
tests/             pytest suites (backend)
```

**Stack:** FastAPI · Qdrant Cloud · fastembed (ONNX Runtime) · BM25 sparse retrieval · cross-encoder/ms-marco-MiniLM-L-6-v2 · `qwen/qwen3.8-27b` for query expansion and synthesis (via Groq's OpenAI-compatible API; override with the `EXPANSION_MODEL` and `LLM_MODEL` env vars) · Jev / TypeSafe System One for the optional scope guard and citation support check · Next.js · Tailwind CSS

## Configuration

Vectors are stored in Qdrant (local Docker or **Qdrant Cloud**). LLM calls go to **Groq**. At startup the backend makes one test call per model and logs a warning if a model has been retired or `GROQ_API_KEY` is missing, instead of failing silently later. User feedback is stored in local SQLite, or in **Supabase** when `SUPABASE_URL` and `SUPABASE_KEY` are set.

Optional Jev features are turned on with env vars and need `TYPESAFE_API_KEY`; if the key is missing they stay off. If Jev is down, the app answers without the check rather than failing:

| Env var | Turns on |
|---|---|
| `SCOPE_GUARD_ENABLED=true` | Scope guard |
| `CITATION_SUPPORT_CHECK_ENABLED=true` | Citation support check |

CI runs the full backend test suite on every pull request.

## Prerequisites

- Docker (for Qdrant)
- Python 3.10+
- Node.js 20+
- A [Groq API key](https://console.groq.com/keys)
- Optional: a TypeSafe API key (`TYPESAFE_API_KEY`) for the Jev features

## Setup

### 1. Start Qdrant

**Option A — local Docker:**
```bash
docker run -d -p 6333:6333 -v ~/qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Option B — Qdrant Cloud:** create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io), then set `QDRANT_URL` and `QDRANT_API_KEY` in your environment before running the backend or indexing scripts.

### 2. Index the Pali Canon

```bash
# Download all 11 nikayas from the dhammatalks.org epub (Thanissaro Bhikkhu translations)
python3 data/fetch_thanissaro.py

# Embed and index into Qdrant (takes several minutes)
PYTHONPATH=. python3 data/process_dumps.py
```

Indexing can be interrupted and resumed — already-indexed suttas are skipped automatically.

### 3. Install frontend dependencies

```bash
cd frontend && npm install
```

### 4. Configure environment

```bash
cp frontend/.env.local.example frontend/.env.local
# Edit frontend/.env.local and set NEXT_PUBLIC_API_URL if needed
```

## Running

**Terminal 1 — Backend:**
```bash
PYTHONPATH=. GROQ_API_KEY=your_key uvicorn backend.app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## API

| Endpoint | Description |
|---|---|
| `GET /synthesize?q=…&top_k=10` | AI answer with citations, `hallucinations`, `canonical_misses`, and `is_faithful` flag |
| `GET /stream?q=…&top_k=10&nikayas=DN` | Streaming synthesis (SSE); same `nikayas` filter supported |
| `POST /feedback` | Submit thumbs-up/down feedback on a synthesis answer, with optional category and notes; stored in Supabase if configured, otherwise local SQLite |

Rate limits: 10 req/min for synthesis and streaming.

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q
```

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE).

Sutta texts © Thanissaro Bhikkhu, sourced from [dhammatalks.org](https://www.dhammatalks.org).
