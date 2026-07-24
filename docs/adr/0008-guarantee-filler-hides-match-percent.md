# ADR-0008: Guarantee-Filler Results Hide Match %, Show Book Badge Instead

**Status:** Superseded by ADR-0011
**Date:** 2026-07-19

## Context

`_relevance_scores` (`search_pipeline.py:136`) rank-normalizes cross-encoder rerank scores into a 0.5–0.99 band, called on the *final* `results` list after `_select_results` has already applied the book-representation policy (`search_pipeline.py:593-600`). The results view runs `policy="round_robin"` (ADR-0007), which guarantees every selected book at least one slot in the final top-k even if its best passage scores far below the rest.

Because normalization only looks at the final displayed set, a result that only made the list to satisfy round_robin's per-book guarantee gets stretched across the same 50–99% band as everything else — it can display near the ceiling regardless of its absolute relevance. Issue #114 named this: a weak book's forced-in entry can display ~98% while off-topic.

## Decision

For every results-view entry, classify it as **organic** (it would appear in the top-*k* under pure rerank-score order — i.e. it's in `scored[:top_k]`) or **guarantee filler** (it's only present because round_robin forced its book in).

- Organic results keep the existing behavior: rank-normalized `score`, rendered as "N% match".
- Guarantee-filler results show no percentage. The frontend renders a book-attribution badge, "Included for `<Book>`" (using the existing book code, e.g. `DHP`), reusing the badge slot/pattern already used for the "Translator's introduction" tag in `SearchResultsView.tsx`.
- `_relevance_scores`'s min/max is computed only over the organic subset of the final results — filler scores are excluded from the normalization range. This is a minimal, localized change to the existing function rather than widening its input to the full candidate pool.

## Why

Rank-normalization was already a deliberate choice (see comment at `search_pipeline.py:127-131`) to work around the cross-encoder's uncalibrated logits — an absolute transform (sigmoid) previously collapsed every result to ~1%. That constraint is real and isn't touched here. Rather than trying to compute a "more correct" percentage for guarantee-filler results — a calibration problem this project already tried and backed away from once — this decision sidesteps the question: filler results don't get a percentage at all, because the reason they're present isn't "the model thinks this is a strong match," it's the book guarantee, and the badge says so honestly.

This follows ADR-0007's own reasoning that book representation in the results view is a deliberate, user-facing feature (the user picked that book) rather than a bug to paper over — making it visible via a badge, rather than hiding or faking a number, applies the same principle to the score display.

## Alternatives Considered

**Normalize against the full reranked candidate pool instead of the final set:** Rejected as the primary mechanism — it widens the reference set for multi-book searches, but does nothing for the degenerate case where the final set and the candidate pool are already the same (e.g. exactly one book selected), so it doesn't eliminate the failure mode the issue names. Considered as a secondary refinement for organic-result normalization too, but rejected in favor of keeping the fix minimal — excluding filler scores from the organic min/max is enough to stop filler entries from distorting the range for genuine results.

**Absolute score calibration:** Rejected — would require real benchmark-driven calibration work, the exact thing rank-normalization was introduced to avoid. Out of scope for this fix.

**Guarantee at least one visible percentage even when the whole set is filler:** Rejected — would reintroduce the false-precision problem this decision exists to remove. An all-badged results page is accepted as an honest, if unusual, outcome.

## Consequences

- A new per-result field is needed to carry the organic/filler classification from `search_pipeline.py` through the API response to `SearchResultsView.tsx`.
- The single-book-selected case (or any case where round_robin's output happens to equal `global_best`'s) still shows a near-ceiling percentage for an off-topic top result. This is a distinct, pre-existing defect — rank-normalization always produces a near-ceiling top score for any pool, however weak — and is explicitly out of scope here; to be tracked as a separate issue.
- A results page can end up mostly or entirely badged rather than percentaged if round_robin's per-book cycling diverges heavily from rerank order (`_interleave` cycles books in a fixed order each round, not globally re-scored). This is accepted as correct behavior, not something to guard against.
- Deep-dive flow is unaffected: it already runs `global_best` (ADR-0007) and doesn't render per-passage match percentages at all.
