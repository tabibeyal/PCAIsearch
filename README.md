# Ask the Pali Canon

**Live:** https://illustrious-biscotti-f60464.netlify.app

Semantic search and AI-synthesized answers over the Pali Canon (DN, MN, AN, SN, Dhammapada, Itivuttaka), grounded in the original bilingual texts from SuttaCentral.

## Features

- **Semantic search** — multilingual embeddings (paraphrase-multilingual-MiniLM-L12-v2) retrieve relevant verses in English or Pali
- **Hybrid retrieval** — dense vector search fused with BM25 sparse retrieval via Reciprocal Rank Fusion; canonical suttas matched by title are surfaced even when vector search misses
- **Query expansion** — LLM generates alternative phrasings to improve recall
- **Cross-encoder reranking** — results reordered by relevance before display
- **AI Synthesis** — LLM answers your question using only retrieved context, with inline citations (`[DN 1:1]`, `[SN 46.20:14]`)
- **Citation guardrail** — distinguishes true hallucinations (non-existent sutta) from canonical misses (real sutta not in retrieved context)
- **Nikaya filter** — filter search and synthesis by collection (DN, MN, SN, AN, DHP, ITI); click to switch, ⌘/Ctrl-click to combine
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
  fetch_bilara.py  Sparse-clone SuttaCentral bilara-data → local JSON (DN/MN/AN/SN/DHP/ITI)
  process_dumps.py Embed & upsert into Qdrant
docs/adr/          Architecture decision records
tests/             pytest suites (backend)
```

**Stack:** FastAPI · Qdrant Cloud · fastembed (ONNX Runtime) · BM25 sparse retrieval · cross-encoder/ms-marco-MiniLM-L-6-v2 · Gemma 3N for query expansion · Llama for synthesis (via NVIDIA API; model set via `LLM_MODEL` env var, defaults to `meta/llama-3.3-70b-instruct`) · Next.js · Tailwind CSS

## Deployment

The live app runs on **DigitalOcean App Platform** (`pcaisearch-jol64.ondigitalocean.app`), auto-deploying from the `master` branch on push. Vectors are stored in **Qdrant Cloud** (free tier). LLM calls go to the **NVIDIA API** (free tier). The `LLM_MODEL` env var is set in the App Platform dashboard.

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

### 2. Install Python dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Index the Pali Canon

```bash
# Download DN, MN, AN, SN, Dhammapada, Itivuttaka from SuttaCentral (sparse git clone, ~80 MB)
python3 data/fetch_bilara.py

# Embed and index into Qdrant (DN/MN/AN/SN/DHP/ITI, takes several minutes)
PYTHONPATH=. python3 data/process_dumps.py
```

Indexing can be interrupted and resumed — already-indexed suttas are skipped automatically.

### 4. Install frontend dependencies

```bash
cd frontend && npm install
```

### 5. Configure environment

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
| `POST /feedback` | Submit thumbs-up/down feedback on a synthesis answer, with optional category and notes |

Rate limits: 30 req/min for search, 10 req/min for synthesis.

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Sutta texts sourced from [SuttaCentral](https://suttacentral.net) bilara-data, licensed under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
