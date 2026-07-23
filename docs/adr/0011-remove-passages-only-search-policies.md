# ADR-0011: Remove Passages-Only Search Policies and Weak-Pool Scoring

**Status:** Accepted
**Date:** 2026-07-23

## Context

The Passages tab (the raw list-of-retrieved-passages view, as opposed to the synthesized answer) is being hidden from the UI (map #142). `SearchPipeline.search()` supports three result-selection policies in `_select_results()`: `round_robin` (default — interleaves one result per selected book, used only by the Passages tab), `global_best` (take the globally highest-scoring passages, used by the synthesized-answer flow via `AnswerComposer`), and `relevance_floor:<ratio>` (a round-robin variant with a per-book score floor, which turned out to have zero production callers — only exercised by tests).

Auditing callers found one more implicit dependency: `gap_detector.py`'s retrieval-gap issue filer called `search()` without specifying a policy, silently inheriting `round_robin`'s per-book interleaving for what is actually a diagnostic "what did we retrieve" snapshot — a case where book diversity was never a deliberate requirement.

Once the Passages tab's UI is gone, `round_robin` and `relevance_floor` have no remaining reason to exist, and the weak-pool notice (`is_weak_pool`, `_WEAK_POOL_FLOOR`, ADR-0009) and guarantee-filler badge (`is_guarantee_filler`, ADR-0008) that only that tab displayed become dead computation performed on every search call regardless of consumer.

## Decision

- Switch `gap_detector.py` to call `search(..., policy="global_best")` explicitly, removing round_robin's only remaining caller.
- Delete `round_robin` and `relevance_floor:<ratio>` from `_select_results()`. `global_best` becomes the only behavior.
- Remove the `policy` parameter from `search()` entirely; `_select_results()`, `_interleave()`, and `_bucket_of()` are deleted outright, since they exist solely to serve the removed policies.
- Remove weak-pool detection (`_WEAK_POOL_FLOOR`, `is_weak_pool`) and guarantee-filler classification (organic/filler split, `is_guarantee_filler`) from `search()`'s return value, along with `_relevance_scores()` (used only to compute the now-removed `score` field).
- Delete the backend `GET /search` route (`main.py`) and its frontend consumer (`searchVerses()`, the `/api/search` proxy route) — folded into the Passages-tab-removal ticket (#143) since it's the same deletion, same area.
- `buckets` (per-nikaya bucketing for parallel retrieval) is retained — it does real retrieval-time work unrelated to result-selection policy.
- `tests/backend/retrieval_benchmark.py` now explicitly passes `policy="global_best"` (previously implicit via the default) and is re-run after implementation to record a fresh baseline, kept separate from the unrelated #117 recall regression investigation.

## Why

- **No dead code, git has history** (`.claude/rules/code-quality.md`): once the Passages tab is hidden and Gap Detector no longer needs it, nothing calls `round_robin` or `relevance_floor`, and nothing reads the fields their bookkeeping produces.
- **The notice was the feature, not the plumbing:** weak-pool/guarantee-filler exist to annotate the Passages results list for display. `AnswerComposer` computes and discards these fields on every synthesis call today; removing them is a pure simplification with no behavioral effect on synthesis.
- **Correcting an accidental dependency:** Gap Detector's reliance on round_robin's book diversity was never a deliberate design choice; a diagnostic retrieval snapshot has no clear need for cross-book representation, so `global_best` is arguably a quality improvement there too, not just a migration necessity.

## Alternatives Considered

**Keep `round_robin` alive solely for Gap Detector:** rejected. Preserving a whole book-interleaving code path, plus its supporting `_bucket_of`/`_interleave` helpers, for one caller whose need for it was never established, is exactly the premature-abstraction / speculative-generality this repo's conventions warn against.

**Leave weak-pool/guarantee-filler computed but unread, in case Passages returns:** rejected. Git history restores the code faithfully if Passages ever comes back; keeping it live in the meantime means `_WEAK_POOL_FLOOR` silently bit-rots against a changing corpus with nothing exercising or validating it.

## Consequences

- `search()`'s return shape loses `score`, `is_weak_pool`, and `is_guarantee_filler` — any future consumer that wants a "how confident is this match" signal will need to reintroduce it deliberately, not resurrect these fields.
- ADR-0008 (guarantee-filler) and ADR-0009 (weak-pool notice) are marked superseded by this ADR; they remain as historical record of why those features existed.
- ADR-0010 (corrected variant in reranking) no longer has a weak-pool-floor recalibration consequence — corrected there directly.
- `retrieval_benchmark.py`'s recall@10 number may shift as a side effect of `global_best` replacing the implicit `round_robin` default; the post-implementation run should be recorded as a new baseline, not compared against pre-cleanup numbers as if policy were held constant.
