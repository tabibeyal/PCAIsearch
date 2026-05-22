# PCAIsearch — Architecture Decisions and Environment

## Pipeline Architecture (current)
Expand → Retrieve (dense + BM25 via RRF) → Rerank → Synthesize. Recall@10: 93%.

Key components:
- **ExpansionPrompt v6** — versioned LLM query expansion (in `search_pipeline.py`)
- **Reranker** — ms-marco-MiniLM-L-6-v2 (English-only; Pāḷi bridged via `english_hint` from `pali_dictionary.py`)
- **BM25Retriever** — sparse keyword retrieval fused with dense vectors via RRF (`bm25_retriever.py`)
- **Guardrail** — post-generation citation verifier; strips any `[ID:Verse]` not in retrieved context (`guardrail.py`)
- **pali_dictionary** — keyword lookup returning Pāḷi term + verbatim English passage hint for reranking

## Key Decisions
- **ONNX embeddings** — local CPU, no API key. Chosen so indexing works offline.
- **Qdrant Cloud free tier** — vectors only; not self-hosted (2GB droplet too small).
- **NVIDIA API free** — LLM provider. Replaceable if rate limits hit.
- **Guardrail is non-negotiable** — accuracy guarantee, never disable.
- **Parallels module removed 2026-05-21** — extracted as standalone side project outside this repo.
- **ExpansionPrompt versioned** — bump the version number when changing the expansion prompt, so experiments are traceable.

## Test Seam
Access pipeline internals via `pipeline.retriever.client` / `pipeline.retriever.embedding_mgr` — not `pipeline.client` directly (aliases removed).

## Dev Commands
```bash
# Backend dev server
PYTHONPATH=. NVIDIA_API_KEY=... uvicorn backend.app.main:app --reload

# Run tests
PYTHONPATH=. python3 -m pytest tests/backend/ -q

# Recall@10 benchmark
PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants
```
