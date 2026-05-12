# Handoff — Session 2026-05-12 (alias cleanup)

## What happened this session

Single cleanup commit: dropped the `pipeline.client` / `pipeline.embedding_mgr` compatibility aliases that had been left on `SearchPipeline` after the Retriever extraction. Tests wired through `pipeline.retriever` directly.

---

## What was done

### Drop `SearchPipeline` compatibility aliases

**Commit:** `89614d0` — `refactor: drop pipeline.client/embedding_mgr aliases; wire tests through retriever`

**Files:** `backend/app/services/search_pipeline.py`, four test files

After the `Retriever` extraction (previous session), `SearchPipeline.__init__` retained:

```python
self.embedding_mgr = embedding_mgr  # kept for test compatibility
self.client = client                 # kept for test compatibility
```

Both removed. All four test fixtures that accessed these attributes now go through `pipeline.retriever.client` and `pipeline.retriever.embedding_mgr`. 19/19 tests pass.

---

## Architecture vocabulary (cumulative)

- **Citation oracle** — answers "does this `[ID:Verse]` exist in the canon?" (`CitationOracle`)
- **Sutta relations** — answers "what is related to sutta X?" (`SuttaRelations`)
- **Guardrail** — deterministic post-generation layer that verifies and redacts hallucinated citations (`CitationGuardrail`)
- **Pipeline** — the RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — vector retrieval against Qdrant; injectable seam between retrieval strategy and orchestration (`Retriever`)
- **Registry** — `Dict[str, Set[int]]` mapping sutta ID → set of verse numbers, loaded from local dump files

---

## Known issues / remaining work

Codebase is clean.

One remaining optional item (not yet a problem):
- `_SYSTEM_PROMPT` is a module-level constant with no seam — untestable in isolation. A `PromptBuilder` abstraction would fix this if prompt variants ever need testing.
