# PCAIsearch — Claude Context

## Commands
`PYTHONPATH=. python -m pytest tests/backend/ -q` — run backend tests (19 tests)
`PYTHONPATH=. NVIDIA_API_KEY=... uvicorn backend.app.main:app --reload` — backend dev server

## Architecture vocabulary
- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`search_pipeline.py`)
- **Retriever** — Qdrant vector retrieval; injectable seam (`retriever.py`)
- **Guardrail** — post-generation citation verifier/redactor (`guardrail.py`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`citation_oracle.py`)
- **SuttaRelations** — answers "what is related to sutta X?" (`sutta_relations.py`)
- **Registry** — `Dict[str, Set[int]]` sutta ID → verse numbers, loaded from local dumps

## Test seam
Access pipeline internals via `pipeline.retriever.client` / `pipeline.retriever.embedding_mgr` — not `pipeline.client` directly (aliases removed).

## Known gap
`_SYSTEM_PROMPT` in `search_pipeline.py` is a module-level constant — untestable in isolation. Extract a `PromptBuilder` only if prompt variants need testing.
