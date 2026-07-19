# ADR-0007: Book-Representation Guarantee Split by Flow (Results View vs. Deep-Dive)

**Status:** Accepted
**Date:** 2026-07-19

## Context

`SearchPipeline._select_results` (`search_pipeline.py`) dispatches on a `policy` argument: `round_robin` (default, per-book interleave), `global_best` (pure rerank-score top-k, no book guarantee), and `relevance_floor:<ratio>` (round-robin, but a book only qualifies if its best passage clears a ratio of the top score in the candidate set).

The `round_robin` guarantee was added deliberately in `b21fab8` (2026-06-01) to fix two combined failure modes when multiple books were selected: (1) the shared dense-retrieval pool let a large book (SN) crowd out a small one (DHP) before reranking ever saw it; (2) even once DHP entered the pool, the cross-encoder reranker systematically scored SN prose above DHP verse for topically-matched queries, so DHP still lost.

Failure mode (1) has since been independently fixed by the per-bucket retrieval architecture in `search()`: every selected book gets its own retrieval/BM25/RRF-fusion pool before the union is reranked (`search_pipeline.py:518-570`), regardless of which `_select_results` policy runs afterward. So the choice of policy today only protects against failure mode (2) — the cross-encoder's known bias against verse-style text.

Issue #112 asked which policy should apply where. Both the results view (`main.py:223`, no `policy=` argument — defaults to `round_robin`) and the deep-dive answer flow (`AnswerComposer.answer`/`answer_stream`, `answer_composer.py:41,57`, also no `policy=` today) currently run on `round_robin`.

A `relevance_floor` empirical comparison (`analysis/policy-comparison-2026-07-14.md`) tested ratios 0.60/0.75/0.90 against real queries and found it collapses to a single book in 3 of 4 test queries, identically at all three thresholds — its floor is relative to the top score in the candidate set, not absolute, so it behaves as a bimodal switch rather than a tunable dial.

## Decision

- Results view keeps `policy="round_robin"` (no code change — already the default).
- Deep-dive answer flow (`AnswerComposer.answer` / `answer_stream`) switches to `policy="global_best"`.
- `relevance_floor` is not adopted anywhere.

## Why

The results view is a case where each selected book's presence is itself part of what the user asked for — dropping one silently because of a cross-encoder scoring quirk (not a real relevance gap) would read as a bug to a user who explicitly picked that book. No UI grouping depends on this (`SearchResultsView.tsx` renders a flat list), but the expectation is still user-facing, not structural.

The deep-dive flow synthesizes one answer rather than presenting book-by-book results; citing the genuinely highest-scoring passages serves the project's accuracy-over-creativity principle better than forcing in a weaker passage from an under-selected book just to preserve representation.

The pool-starvation half of the original bug (failure mode 1) is unaffected by this change — it's already fixed in `search()` independent of `_select_results`. Only the scoring-bias half was actually being traded here.

## Alternatives Considered

**`relevance_floor` everywhere:** Rejected — empirically collapses to a single book in the majority of tested queries at every threshold tried; not a real dial between `round_robin` and `global_best`.

**Drop the guarantee entirely (`global_best` for both flows):** Rejected for the results view — a user who selected multiple books would likely read a silent all-from-one-book result as broken, not as "the model chose the best passages."

**Keep `round_robin` everywhere (status quo):** Rejected — deep-dive answers could end up citing a weaker passage from an under-represented book purely due to the verse/prose scoring bias, when a genuinely stronger passage from another selected book was available.

## Consequences

- Code change required: add `policy="global_best"` to the two `self.pipeline.search(...)` calls in `answer_composer.py` (lines 41 and 57). No change needed in `main.py`.
- Deep-dive answers may now cite zero passages from a book the user selected, if that book's best passage doesn't clear the reranked top-k — this is the accepted trade-off, not a bug.
- The cross-encoder's verse-vs-prose scoring bias (failure mode 2) remains unaddressed at the model level; it's now only masked (for the results view) by `round_robin`, not fixed. A future reranker swap or fine-tune could reduce or remove the need for this split.
- Relies on the Book vs. Nikāya distinction pinned in `CONTEXT.md` this session — "book" is the correct unit for this guarantee, not "nikāya."
