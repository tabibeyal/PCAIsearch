# Ask the Pali Canon

Semantic search and AI-synthesized answers over the Pali Canon (DN, MN, AN, SN, Dhammapada, Itivuttaka), grounded in the original bilingual texts from SuttaCentral.

## Features

- **Semantic search** — multilingual embeddings (paraphrase-multilingual-MiniLM-L12-v2) retrieve relevant verses in English or Pali
- **Query expansion** — LLM generates alternative phrasings to improve recall
- **Cross-encoder reranking** — results reordered by relevance before display
- **AI Synthesis** — LLM answers your question using only retrieved context, with inline citations (`[DN 1:1]`, `[SN 46.20:14]`)
- **Citation guardrail** — distinguishes true hallucinations (non-existent sutta) from canonical misses (real sutta not in retrieved context)
- **Nikaya filter** — filter search and synthesis by collection (DN, MN, SN, AN, DHP, ITI); click to switch, ⌘/Ctrl-click to combine
- **Canon cross-references** — `/search` returns `related_suttas`: doctrinally paired suttas and structural neighbors from the canon index
- **Resume-capable indexing** — indexing can be interrupted and resumed without re-embedding

## Architecture

```
frontend/          Next.js 15 (App Router)
backend/           FastAPI + asyncio
  app/
    main.py        API endpoints (/search, /synthesize), rate limiting
    core/
      indexing.py  SuttaParser, EmbeddingManager (fastembed / ONNX Runtime)
    services/
      search_pipeline.py  Query expansion → retrieval → reranking → related suttas
      guardrail.py        Citation verification (hallucination vs canonical miss)
      canon_graph.py      Canon index: citation oracle + doctrinal cross-references
data/
  fetch_bilara.py  Sparse-clone SuttaCentral bilara-data → local JSON (DN/MN/AN/SN/DHP/ITI)
  process_dumps.py Embed & upsert into Qdrant
tests/backend/     pytest suite
```

**Stack:** FastAPI · Qdrant · fastembed (ONNX Runtime) · cross-encoder/ms-marco-MiniLM-L-6-v2 · Gemma 3N (NVIDIA API) · Next.js · Tailwind CSS

## Prerequisites

- Docker (for Qdrant)
- Python 3.10+
- Node.js 20+
- An [NVIDIA API key](https://build.nvidia.com/)

## Setup

### 1. Start Qdrant

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

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

Rate limits: 30 req/min for search, 10 req/min for synthesis.

## Running Tests

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Sutta texts sourced from [SuttaCentral](https://suttacentral.net) bilara-data, licensed under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
