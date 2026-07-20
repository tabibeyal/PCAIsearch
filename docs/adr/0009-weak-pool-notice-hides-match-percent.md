# ADR-0009: Weak-Pool Searches Show a Notice and Hide All Match %

**Status:** Accepted
**Date:** 2026-07-19

## Context

ADR-0008 stopped guarantee-filler results from wearing a rank-normalized percentage, but explicitly left open the degenerate case (issue #128): when nothing is forced into the results — most simply, a single-book search — every result is organic under ADR-0008's classification, and `_relevance_scores` still stretches the pool across the 0.5–0.99 band. An off-topic query, or a topic the selected books don't cover, still shows ~99% on its top result.

The root cause is broader than single-book: rank-normalization crowns the best of *any* pool, however weak. A multi-book search where everything retrieved is weak fails the same way. The unit of weakness is the whole search's candidate pool — not an individual result, and not the book count.

## Decision

Introduce a **weak pool** signal: a search whose best absolute cross-encoder rerank score falls below a fixed floor. (The pool's best raw score and the displayed set's best raw score are the same number — the top-scored candidate survives both book-representation policies — so the check is one comparison over the final results.)

On a weak-pool search the results view:

- shows a notice — "No strong matches — showing the closest passages found" (exact copy adjustable at implementation);
- renders every card without a Match %;
- keeps guarantee-filler badges — the badge explains why a card is present, the notice explains why nothing has a number; they compose;
- never hides or collapses the results.

The floor errs toward **not firing**: it is placed low, under the measured gap between known-good and known-weak pools, so the notice appears only when the pool is clearly weak. Its value is empirical, not guessed — measured over the retrieval benchmark's known-good queries plus deliberately off-topic and known-corpus-gap queries.

Scope: results view only. The deep-dive answer flow (`global_best`, no percentages) is untouched; making synthesis acknowledge a weak pool would be a separate issue.

## Why

Same honesty principle as ADR-0008: don't display a number whose real meaning ("standing within this set") the user will read as something else ("match quality"). For filler results the honest replacement was a badge; for a weak pool it is a page-level notice, because weakness here is a property of the search, not of any single entry.

Erring toward showing percentages: a good page falsely stamped "no strong matches" teaches users to distrust both the notice and the engine — worse than the status quo surviving on some weak pages. The reranker's uncalibrated raw scores also under-score legitimate queries whose vocabulary it doesn't recognize (the gap `pali_dictionary` hints exist to bridge), so a high floor would misfire on exactly those queries.

## Alternatives Considered

**Accept and document (wontfix):** defensible for single-book searches ("best of what this book has"), but the off-topic-query case — asking about something the canon doesn't cover and seeing 99% matches — sits badly with the project's accuracy-over-creativity principle.

**Cap displayed % by absolute score:** partial calibration — the problem rank-normalization was introduced to avoid; a previous attempt collapsed every result to ~1% (see ADR-0008). Third rejection of calibration; stop suggesting it.

**Rename the label only ("Top result" instead of "match"):** removes signal from good searches too, and a percentage next to any label still implies quality.

**Hide results behind a click, or show nothing:** punishes the false-positive case and withholds genuinely useful near-miss passages.

## Consequences

- A per-response weak-pool flag must travel from the pipeline through the API to the results view, alongside (not replacing) the per-result guarantee-filler flag.
- Floor derivation is a prerequisite of implementation: log best raw rerank scores for the benchmark queries and a set of off-topic / corpus-gap queries, then place the floor under the separation gap. Two cautions: several benchmark queries currently fail recall@10 (#117), so their pools are not automatically "known good"; and local reranker runs risk the machine's RAM freeze — measure with Firefox closed or against the deployed backend.
- Weak pages below detection keep today's behavior (percentages shown). Accepted — the floor is deliberately conservative.
- A page can be simultaneously noticed (weak pool) and badged (fillers). Accepted as coherent, not contradictory.
