# Ask the Pali Canon

**Live:** https://pcaisearch.netlify.app

Semantic search and AI-synthesized answers over the Pali Canon (DN, MN, AN, SN, Dhammapada, Itivuttaka, Udāna, Sutta Nipāta, Theragāthā, Therīgāthā, Khuddakapāṭha), grounded in Thanissaro Bhikkhu's English translations from dhammatalks.org.

## Features

- **Semantic search** — multilingual embeddings (paraphrase-multilingual-MiniLM-L12-v2) retrieve relevant verses in English or Pali
- **Hybrid retrieval** — dense vector search fused with BM25 sparse retrieval via Reciprocal Rank Fusion; canonical suttas matched by title are surfaced even when vector search misses
- **Query expansion** — LLM generates alternative phrasings to improve recall
- **Cross-encoder reranking** — results reordered by relevance before display
- **AI Synthesis** — LLM answers your question using only retrieved context, with inline citations (`[DN 1:1]`, `[SN 46.20:14]`)
- **Citation guardrail** — distinguishes true hallucinations (non-existent sutta) from canonical misses (real sutta not in retrieved context)
- **Nikaya filter** — filter search and synthesis by collection (DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP); click to switch, ⌘/Ctrl-click to combine
- **Canon cross-references** — `/search` returns `related_suttas`: doctrinally paired suttas and structural neighbors from the canon index
- **Resume-capable indexing** — indexing can be interrupted and resumed without re-embedding

## Architecture

```
frontend/          Next.js 16 (App Router)
backend/           FastAPI + asyncio
  app/
    main.py        API endpoints (/search, /synthesize), rate limiting
    core/
      indexing.py  SuttaParser, EmbeddingManager (fastembed / ONNX Runtime)
    services/
      search_pipeline.py   Query expansion → retrieval → reranking → related suttas
      retriever.py         Dense vector retrieval (Qdrant)
      bm25_retriever.py    Sparse BM25 retrieval, fused via RRF
      sutta_title_index.py Sutta title BM25 boost
      fusion.py            Reciprocal Rank Fusion for hybrid retrieval
      guardrail.py         Citation verification (hallucination vs canonical miss)
      citation_oracle.py   Validates sutta IDs and verse numbers
      sutta_relations.py   Doctrinal cross-references between suttas
      pali_dictionary.py   Pāḷi term → English passage hints for reranking
data/
  fetch_thanissaro.py  Download Thanissaro Bhikkhu epub from dhammatalks.org → local JSON
  process_dumps.py Embed & upsert into Qdrant
docs/adr/          Architecture decision records
tests/             pytest suites (backend)
```

**Stack:** FastAPI · Qdrant Cloud · fastembed (ONNX Runtime) · BM25 sparse retrieval · cross-encoder/ms-marco-MiniLM-L-6-v2 · Gemma 3N for query expansion · Llama for synthesis (via NVIDIA API; model set via `LLM_MODEL` env var, defaults to `meta/llama-3.3-70b-instruct`) · Next.js · Tailwind CSS

## Deployment

The frontend is on **Netlify** (`pcaisearch.netlify.app`). The backend runs on **DigitalOcean App Platform** (paid, ~$7–12/month), auto-deploying from the `master` branch on push. Vectors are stored in **Qdrant Cloud** (free tier). LLM calls go to the **NVIDIA API** (free tier). User feedback is stored durably in **Supabase** (free tier) — survives redeploys. The `LLM_MODEL`, `SUPABASE_URL`, and `SUPABASE_KEY` env vars are set in the App Platform dashboard.

## Prerequisites

- Docker (for Qdrant)
- Python 3.10+
- Node.js 20+
- An [NVIDIA API key](https://build.nvidia.com/)

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
PYTHONPATH=. NVIDIA_API_KEY=your_key uvicorn backend.app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## API

| Endpoint | Description |
|---|---|
| `GET /search?q=…&top_k=10&nikayas=MN&nikayas=SN` | Semantic search; returns ranked verses + `related_suttas`. `nikayas` is optional, repeatable. |
| `GET /synthesize?q=…&top_k=10` | AI answer with citations, `hallucinations`, `canonical_misses`, and `is_faithful` flag |
| `GET /stream?q=…&top_k=10&nikayas=DN` | Streaming synthesis (SSE); same `nikayas` filter supported |
| `POST /feedback` | Submit thumbs-up/down feedback on a synthesis answer, with optional category and notes; stored in Supabase (production) or local SQLite (dev) |

Rate limits: 30 req/min for search, 10 req/min for synthesis.

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q
```

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE).

Sutta texts © Thanissaro Bhikkhu, sourced from [dhammatalks.org](https://www.dhammatalks.org).
