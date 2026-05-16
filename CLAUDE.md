# PCAIsearch — Claude Context

## Commands
`PYTHONPATH=. python3 -m pytest tests/backend/ -q` — run backend tests
`PYTHONPATH=. NVIDIA_API_KEY=... uvicorn backend.app.main:app --reload` — backend dev server
`PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants` — recall@10 benchmark (currently 93%)

## Architecture vocabulary
- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`search_pipeline.py`)
- **Retriever** — Qdrant vector retrieval; injectable seam (`retriever.py`)
- **BM25Retriever** — sparse keyword retrieval fused with dense via RRF (`bm25_retriever.py`)
- **Reranker** — cross-encoder reranking; `rerank_multi` scores against multiple queries and takes max (`search_pipeline.py`)
- **ExpansionPrompt** — versioned LLM query expansion prompts, currently v6 (`search_pipeline.py`)
- **pali_dictionary** — keyword-matched lookup returning Pāḷi terms + verbatim English passage hints for reranking (`pali_dictionary.py`)
- **Guardrail** — post-generation citation verifier/redactor (`guardrail.py`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`citation_oracle.py`)
- **SuttaRelations** — answers "what is related to sutta X?" (`sutta_relations.py`)
- **Registry** — `Dict[str, Set[int]]` sutta ID → verse numbers, loaded from local dumps

## Reranking design
The cross-encoder (ms-marco-MiniLM-L-6-v2) is English-only — Pāḷi terms are opaque to it. `rerank_multi` is called with `[original_query, english_hint]` where `english_hint` is verbatim passage text from `lookup_english()`. This bridges vocabulary gaps (e.g. "one precept" → "deliberate lie / bad deed") without introducing Pāḷi noise.

## Test seam
Access pipeline internals via `pipeline.retriever.client` / `pipeline.retriever.embedding_mgr` — not `pipeline.client` directly (aliases removed).

## Known gap
`_SYSTEM_PROMPT` in `search_pipeline.py` is a module-level constant — untestable in isolation. Extract a `PromptBuilder` only if prompt variants need testing.
