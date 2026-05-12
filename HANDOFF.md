# Handoff — Architecture Session 2026-05-11/12

## What happened this session

Ran `/improve-codebase-architecture` over the full backend. Identified four deepening opportunities, explored candidate 2 in depth, ran an LLM council on the design, implemented and committed the refactor.

**Commit:** `4d4b97b` — `refactor: split CanonGraph into CitationOracle and SuttaRelations`

---

## What was done

### Refactor: `CanonGraph` → `CitationOracle` + `SuttaRelations`

`CanonGraph` bundled two independent responsibilities with two different callers. It was split into focused modules:

| Module | File | Caller | Interface |
|---|---|---|---|
| `CitationOracle` | `backend/app/services/citation_oracle.py` | `CitationGuardrail` | Loads dump registry; verifies `[DN 15:3]` citations |
| `SuttaRelations` | `backend/app/services/sutta_relations.py` | `SearchPipeline` | Takes `frozenset[str]` of known sutta IDs; returns related IDs |

**Key design decisions (from LLM council + implementation):**
- `CitationOracle` owns the dump registry. Single disk read at startup.
- `SuttaRelations` takes `oracle.known_suttas` at construction — no file I/O, directly injectable in tests.
- `main.py` wires them: `oracle = CitationOracle(dumps_dir)` → `SuttaRelations(oracle.known_suttas)`.
- `known_suttas` stored as `frozenset` in `SuttaRelations` (immutability, not aliasing).
- No `CanonRegistry` abstraction introduced — the council recommended against it for two consumers.

**Tests:**
- `test_canon_graph.py` deleted; replaced by `test_citation_oracle.py` (6 tests) and `test_sutta_relations.py` (5 tests, including a new invariant: all returned IDs are within known suttas).
- `test_guardrail.py` updated to use `CitationOracle` directly.
- All 19 affected tests pass.

---

## Remaining deepening opportunities (not yet done)

Three candidates from the architecture review were identified but not implemented. In rough priority order:

### 1. `SearchPipeline` has no seam between retrieval and orchestration

**Files:** `backend/app/services/search_pipeline.py`

`SearchPipeline` currently owns query expansion, vector retrieval, nikaya filter construction, reranking, synthesis, and streaming synthesis — all in one class. There's no place to swap retrieval strategy without editing the class. Tests must stub `expand_query` just to test retrieval.

**Proposed fix:** Extract a `Retriever` module with interface `retrieve(query, top_k, nikayas) -> List[Chunk]`. `SearchPipeline.search()` becomes pure orchestration: expand → retrieve → rerank.

### 2. Context formatting and synthesis prompt have no seam — `<think>` stripping duplicated

**Files:** `backend/app/services/search_pipeline.py` (both `synthesize()` and `stream_synthesize()`), `frontend/components/deep-dive/SynthesisLoader.tsx`

- `synthesize()` and `stream_synthesize()` share identical context-formatting code (the `"\n\n".join(...)` block).
- `_strip_thinking` exists in Python AND as `THINK_RE` in `SynthesisLoader.tsx` — the frontend must strip `<think>` tags independently because the backend can only strip from complete responses.
- `_SYSTEM_PROMPT` is a module-level constant with no seam — untestable.

**Proposed fix:** Extract `build_messages(query, chunks) -> List[Message]` as a pure function. Move `_strip_thinking` there. Add `stripThinking` to `frontend/lib/utils.ts`.

### 3. `suttaCentralUrl` duplicated in two frontend components

**Files:** `frontend/components/search/SearchResultsView.tsx:4`, `frontend/components/deep-dive/SourceViewer.tsx:4`

Identical function defined twice. Move to `frontend/lib/suttacentral.ts`.

---

## Pre-existing known issue

`CanonGraph._SUTTA_PARSE_RE` (now `CitationOracle._SUTTA_PARSE_RE`) matches `r"^([A-Za-z]+)(\d+)$"` — integer IDs only. AN/SN/DHP/ITI suttas have dotted IDs (e.g., `AN10.100`) that don't match, so they are silently absent from the citation registry. The library expansion (AN, SN, DHP, ITI) added these suttas to Qdrant but did not update the oracle regex. Citation verification for non-DN/MN suttas always falls through as "not in canon." Fix: change the regex to `r"^([A-Za-z]+)([\d.]+)$"` (same change already applied to `SuttaParser` in `indexing.py`).

---

## Architecture vocabulary (for future sessions)

Terms established in this session, consistent with the codebase:

- **Citation oracle** — answers "does this `[ID:Verse]` exist in the canon?" (`CitationOracle`)
- **Sutta relations** — answers "what is related to sutta X?" (`SuttaRelations`)
- **Guardrail** — deterministic post-generation layer that verifies and redacts hallucinated citations (`CitationGuardrail`)
- **Pipeline** — the RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Registry** — `Dict[str, Set[int]]` mapping sutta ID → set of verse numbers, loaded from local dump files
