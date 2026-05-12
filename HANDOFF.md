# Handoff — Architecture Session 2026-05-12

## What happened this session

Completed all remaining items from the previous session's architecture review: one bug fix and three refactor candidates. All 4 landed as separate commits.

---

## What was done

### Bug fix: `CitationOracle` regex missed dotted sutta IDs

**Commit:** `69f0529` — `fix: CitationOracle regex now matches dotted sutta IDs (AN10.100, SN22.12)`

Both `_SUTTA_PARSE_RE` and `_ID_PARSE_RE` used `\d+`, which excluded dot-separated IDs like `AN10.100`. Changed to `[\d.]+` — matching the existing pattern in `SuttaParser` (`indexing.py`). AN/SN/DHP/ITI citations now verify correctly. New test asserts `"AN 10.100"` is in `known_suttas`.

---

### Candidate 3: `suttaCentralUrl` extracted to shared module

**Commit:** `b478f8d` — `refactor: extract suttaCentralUrl to shared frontend/lib/suttacentral.ts`

Identical function was defined in both `SearchResultsView.tsx` and `SourceViewer.tsx`. Moved to `frontend/lib/suttacentral.ts`; both components now import from there.

---

### Candidate 2: `_build_messages` pure fn; `stripThinking` to `frontend/lib/utils.ts`

**Commit:** `b6864fe` — `refactor: extract _build_messages pure fn; move stripThinking to frontend/lib/utils`

- `synthesize()` and `stream_synthesize()` shared identical context-formatting code. Extracted to `_build_messages(query, chunks) -> List[Message]` pure function above `SearchPipeline`.
- `THINK_RE` / inline `.replace()` in `SynthesisLoader.tsx` moved to `frontend/lib/utils.ts` as `stripThinking(text)`. Component now imports and calls that.

---

### Candidate 1: `Retriever` extracted from `SearchPipeline`

**Commit:** `c493ef2` — `refactor: extract Retriever from SearchPipeline; seam between retrieval and orchestration`

**Files:** `backend/app/services/retriever.py` (new), `backend/app/services/search_pipeline.py`

`SearchPipeline._retrieve_one` moved to `Retriever` with interface `retrieve(query, top_k, nikayas) -> List[Chunk]`. `Retriever` takes `(client, embedding_mgr, collection_name, executor)` at construction — directly injectable in tests without touching LLM or pipeline logic. `SearchPipeline.search()` is now pure orchestration: expand → retrieve → rerank.

`pipeline.client` and `pipeline.embedding_mgr` kept as aliases for test compatibility. Tests updated to also wire `pipeline.retriever.client` when swapping in an in-memory Qdrant.

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

None from the previous architecture review. The codebase is clean.

Potential future work (not yet identified as problems):
- `pipeline.client` / `pipeline.embedding_mgr` kept as aliases post-Retriever extraction — could be removed if tests are updated to wire `Retriever` directly.
- `_SYSTEM_PROMPT` is a module-level constant with no seam — still untestable in isolation (the `build_messages` extraction didn't address this; a `PromptBuilder` abstraction would).
