# ADR-0010: Always Rerank Against One Corrected Expansion Variant

**Status:** Accepted  
**Date:** 2026-07-21

## Context

Issue #134 found the cause of the "consentration" repro: `expand_query()` does correct the typo, and the corrected variant drives dense/BM25 retrieval, but `SearchPipeline.search()` builds `rerank_queries` from the raw, uncorrected query before expansion runs. The cross-encoder then scores every candidate against the misspelled text, dragging relevant passages below the weak-pool floor (`_WEAK_POOL_FLOOR = -6.0`) even though they made it into the candidate pool.

The fix is obvious in hindsight: get the corrected query variant into reranking. The trade-off is cost. `rerank_multi()` runs one cross-encoder forward pass per query string it is given over every candidate chunk, so the number of query strings scales rerank cost linearly. Reranking is already the dominant latency in search.

Three approaches were on the table:

1. **Always rerank against all expansion variants** — simplest change, but roughly triples rerank cost (original + up to 2 LLM variants + English hint already adds one).
2. **Fall back to reranking with a corrected variant only when the raw query trips the weak-pool floor** — adds a second rerank pass, but only on searches that would otherwise show the weak-pool notice; leaves the common case untouched.
3. **Always include exactly one corrected expansion variant** — a middle option that bounds the cost increase to 2× on the first rerank pass, and only pays that cost when expansion actually returns a variant different from the raw query.

## Decision

Always rerank candidates against two query strings:

- the raw user query plus the English passage hint (today's behavior); and
- the first LLM-generated expansion variant plus the same English passage hint, if that variant differs from the raw query.

The first expansion variant is used because the current ExpansionPrompt is designed to emit a corrected English-vocabulary reformulation on its first line. If expansion fails, returns only the raw query, or returns Pāḷi/noise as the first extra variant, the second query string is not added.

`rerank_multi()` already takes the maximum per-candidate score across the query strings it is given, so a candidate that is dragged down by the misspelled query can now be rescued by its score against the corrected query.

The title boost remains retrieval-only and is not added to the rerank query set.

This decision's value does not depend on the weak-pool floor: it's about which passages survive into the top-k that feeds both the Passages results and the synthesized answer, not about a notice threshold. See ADR-0011 — `_WEAK_POOL_FLOOR` and weak-pool detection are being removed entirely, so no floor recalibration follows from this change.

## Why

- **Honest rescue:** a typo can suppress the score of every on-topic passage without necessarily pushing the single best score below the weak-pool floor. Fallback-only would miss these silent distortions. Always including one corrected variant covers them in a single scoring pass.
- **Predictable cost:** worst case is a 2× increase in rerank pairs in one batched forward pass, not a second full pipeline pass or an unbounded number of variants. The common case (expansion returns no new English variant) pays nothing extra.
- **Cleaner semantics:** the final results, weak-pool classification, and match percentages all come from the same rerank output. There is no ambiguity about whether the displayed ranking was produced against the raw or the corrected query.
- **Simple implementation:** the corrected variant is captured before `_apply_title_boost()` mutates the query list, and `rerank_queries` is built after expansion returns instead of being constructed from the raw input up front.

## Alternatives Considered

**Always rerank against all expansion variants:** rejected. Up to three variants plus the English hint would multiply rerank cost by roughly three or four on every search. The Pāḷi variant is also deliberately excluded from reranking because the cross-encoder is English-only, so some of those extra queries add noise, not signal.

**Fallback to corrected reranking only when the raw query trips the weak-pool floor:** rejected. It is cheaper in the common case, but it only rescues queries where the raw spelling is bad enough to push the best score below the floor. A typo can hurt ranking quality without crossing that threshold, and running a second rerank pass on a subset of candidates would re-introduce the same ranking/floor mismatch risk the issue is meant to solve.

**Average or min across raw and corrected scores:** rejected. `rerank_multi()` semantics are max-of-queries. Averaging would dilute the rescue effect, and min would let a single bad spelling match suppress an otherwise relevant passage.

## Consequences

- `expand_query()` must return before `rerank_queries` is built. The English passage hint lookup can be done once against the raw query and reused for both query strings.
- `_apply_title_boost()` must not affect which variant is selected as the corrected rerank query. The corrected variant is captured from the expansion result before the title boost appends title text to the query list.
- No `_WEAK_POOL_FLOOR` recalibration follows from this change — ADR-0011 removes weak-pool detection entirely, independent of this decision.
- `CONTEXT.md`'s definition for `Reranker` is updated to reflect the corrected variant's participation. Its `Weak pool` definition is removed by ADR-0011, not amended here.
