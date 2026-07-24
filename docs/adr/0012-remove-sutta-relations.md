# ADR-0012: Remove SuttaRelations

**Status:** Accepted
**Date:** 2026-07-24

## Context

Issue #144 audited what becomes dead once the Passages tab is hidden and produced ADR-0011, which removed the result-selection policies, weak-pool notice, and guarantee-filler classification. It deliberately left `SuttaRelations` (`backend/app/services/sutta_relations.py`) and `SearchPipeline.get_related_suttas()` untouched, flagging them as a probable follow-up rather than folding them into that change (issue #151).

`SuttaRelations.get_related()` combines a hardcoded table of ~15 doctrinal pairs (e.g. DN 22 ↔ MN 10) with structural adjacency (the ±2 numeric neighbors within the same nikāya), filtered to IDs the `CitationOracle` actually knows about. `SearchPipeline.get_related_suttas()` wraps it: given a results list, it returns related sutta IDs not already present in the top `n`.

Auditing its callers found exactly one: the `GET /search` route (`main.py`), which called `pipeline.get_related_suttas(results)` and returned the result under a `related_suttas` key. That route has no remaining frontend caller as of the Passages-tab removal (#143) — `searchVerses()`, the `/api/search` proxy route, and the `SearchResponse` type it belonged to are all being deleted by ADR-0011/#150. Neither `/synthesize` nor `/stream` (the routes that survive, both behind `AnswerComposer`) reference `sutta_relations` anywhere. Once #150 lands, `GET /search` itself is gone, so `SuttaRelations`/`get_related_suttas` would have zero remaining callers in the running application — the same shape of problem ADR-0011 already solved for the other Passages-only code.

The only other reference is `scripts/run_gap_detector.py`, which constructs a `SuttaRelations` instance and passes it into `SearchPipeline(sutta_relations=...)` purely because the constructor accepts it — `gap_detector.py` itself never reads `sutta_relations` or calls `get_related_suttas`.

This is unrelated to the broader philological cross-referencing goal (ADR-0001) or the parallel-passage detector (ADR-0002/`PassageStore`) — those are a separate, corpus-wide detection mechanism and are unaffected by this change. `SuttaRelations` was a simpler, hand-curated "see also" list scoped to the now-dead Passages results view, not part of that later work.

## Decision

- Delete `backend/app/services/sutta_relations.py` and its dedicated unit tests (`tests/backend/test_sutta_relations.py`).
- Delete `SearchPipeline.get_related_suttas()` and the `sutta_relations` constructor parameter/attribute from `search_pipeline.py`.
- Remove the `SuttaRelations` construction and `sutta_relations=` wiring from `main.py`'s `lifespan()` and `scripts/run_gap_detector.py`. In `run_gap_detector.py` this also removes the now-unused `oracle = CitationOracle(...)` line and its import, since `SuttaRelations` was its only consumer there.
- `main.py`'s own `oracle` variable is retained — it's still used to construct `CitationGuardrail(oracle=oracle)`.

This depends on ADR-0011/#150 (which deletes `GET /search` itself) and is branched on top of it rather than `master`.

## Why

- **No dead code, git history has it** (`.claude/rules/code-quality.md`): the same rationale ADR-0011 used. Once `GET /search` is gone, nothing calls this code and nothing reads its output.
- **Consistent with the pattern already set**: ADR-0011 established that Passages-tab-only backend code gets removed, not preserved "in case Passages comes back." Applying that inconsistently — keeping `SuttaRelations` alive for no caller while deleting everything else in the same tab — would leave an arbitrary exception.

## Alternatives Considered

**Keep it live in case the "see also" feature returns in some other UI surface:** rejected for the same reason ADR-0011 rejected keeping weak-pool/guarantee-filler alive — git restores it faithfully if a future feature wants it, and a hand-curated 15-pair table left unexercised is more likely to silently rot (new suttas ingested without corresponding pairs added) than to be usefully resurrected as-is.

**Fold into #150/ADR-0011 directly:** rejected when #144 was first scoped — ADR-0011 was kept to the result-selection-policy question specifically; this is a separate, independently-removable piece of dead code once `/search` is gone, better tracked and reviewed on its own.

## Consequences

- `SearchPipeline`'s constructor loses the `sutta_relations` parameter; any future caller constructing `SearchPipeline` directly no longer needs (or can pass) it.
- `scripts/run_gap_detector.py` no longer constructs a `CitationOracle` at all, since that was solely in service of building the now-deleted `SuttaRelations` instance.
- If a "see also related suttas" feature is wanted again — in the deep-dive/synthesis view or elsewhere — it needs a deliberate design decision about where it surfaces, not a resurrection of this dead code as-is, since it was never wired into the flow that survives.
