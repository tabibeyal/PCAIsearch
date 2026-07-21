# Issue #135 — How common are context-free single-line chunks, and how often does weak-pool fallback surface them?

**Date:** 2026-07-21
**Part of:** #133 (Passages search: weak results read as broken)
**Question:** What fraction of chunks in `data/dumps/*.json` fall below a "readable on its own" length threshold, and do weak-pool result pages (best rerank score under `_WEAK_POOL_FLOOR = -6.0`) disproportionately surface these short chunks compared to strong-pool pages? Is this a narrow edge case or a systemic pattern?

## Method

Two analyses, both committed under `analysis/`:

1. **`chunk_length_corpus.py`** — pure data pass over all 1,405 dump files (29,221 per-verse chunks). Counts words and characters in each chunk's `english` field, tallies how many fall under candidate thresholds, and labels short chunks (title/header, verse-or-fragment, numbered-list-item, short-prose). No models, no network — safe with Firefox open.
2. **`weak_pool_surfaces.py`** — live queries against the deployed backend's read-only `/search` endpoint (the same method used to confirm the #133 repro). Runs the 16 recall@10 benchmark queries (expected strong pools) and 12 typo / off-topic queries (expected weak pools), records each page's `is_weak_pool` flag and the word count of every surfaced chunk, then compares the two populations. Raw per-query results are written to **`issue-135-weak-pool-run-2026-07-21.json`** so Part 2 is auditable without re-running.

**Threshold choice.** The three weak-pool fragments observed in #133 anchor it: AN 4.50:21 ("unwise, consent to gold & silver,") = 6 words, UD 2.9:6 = 4 words, DN 33:309 = 7 words. A 12-word floor sits above these fragments but below a normal sentence, separating "broken-looking snippet" from "readable prose." Results are reported at multiple thresholds so the choice is auditable.

## Part 1 — How common are short, context-free chunks in the corpus?

The corpus is **29,221 chunks** across 1,405 dump files. Length distribution of the `english` field:

| threshold | chunks | % of corpus |
|-----------|-------:|------------:|
| ≤ 3 words  | 6,033  | 20.6% |
| ≤ 5 words  | 9,488  | 32.5% |
| ≤ 8 words  | 12,221 | 41.8% |
| ≤ 10 words | 12,978 | 44.4% |
| ≤ 12 words | 13,592 | 46.5% |
| ≤ 15 words | 14,291 | 48.9% |
| ≤ 20 words | 15,703 | 53.7% |

Median chunk is 16 words; mean is 35.8 (pulled up by long prose suttas). **Roughly half the corpus is under 12 words** — but that raw number conflates content with titles, so the honest read needs titles separated out.

**Separating titles from content.** The first verse or two of every dump is the series title and sutta title (e.g. AN 1.50:1 "Numerical Discourses 1.50", AN 1.50:2 "–53 Luminous"). These are short by nature but are metadata, not the "broken fragment" the issue is about. Titles are identified by *position* (verses 1–2) plus an explicit heading pattern — not by length — so that a short verse line elsewhere (e.g. UD 2.9:6 "All subjection to others") is not mistaken for a title. This finds 2,810 title/header chunks. Labeling the ≤12-word chunks:

| label | count | % of short |
|-------|------:|-----------:|
| verse-or-fragment | 7,566 | 55.7% |
| other-prose (short prose line) | 3,180 | 23.4% |
| title-or-header | 2,810 | 20.7% |
| numbered-list-item | 36 | 0.3% |

Excluding titles, **content chunks number 26,411, of which 10,782 (41%) are ≤12 words.** Of those short content chunks, **71% are verse/poem lines** (e.g. AN 10.101:5 "'My life is dependent on others.", AN 10.118:6 "Wrong view is the near shore; right view, the far shore.") and **29% are short prose lines** that are really enumerated list items in prose form (e.g. AN 10.108:7 "In one who has right resolve, wrong resolve is purged away.…"). The literal numbered-list pattern (a digit enumerator at the start) is rare — only 36 chunks — because Thanissaro renders most enumerations as repeated prose sentences rather than `1. ... 2. ...` lists; DN 33:309 is one of the few genuine ones.

**Where the short content chunks live** (≤12 words, share of that nikaya's chunks): ITI ~91%, KHP ~95%, UD ~64%, SN ~56%, AN ~45%; the prose nikāyas are lower — MN ~29%, DN ~33%. This is expected: ITI, KHP, UD, and parts of SN/AN are verse or short aphoristic suttas whose lines are inherently one-line-per-chunk. Essentially none of the short content chunks carry a non-empty `pali` field — they are English-only translation lines.

**Part 1 answer.** Short, context-free content chunks are **not an edge case — they are a structural feature of about 41% of the indexed content** (≈10,800 of 26,400 content chunks, ~71% of them verse/poem lines, concentrated in the verse and aphoristic nikāyas). They exist by design of the one-verse-per-chunk parse, not by accident.

## Part 2 — Do weak-pool pages disproportionately surface them?

Ran 28 queries against the deployed backend's `/search` endpoint (top_k=10): the 16 recall@10 benchmark queries (expected strong pools) and 12 typo / off-topic queries (expected weak pools). The pipeline decided weak/strong via the ADR-0009 floor (`_WEAK_POOL_FLOOR = -6.0`); the script only recorded the decision and the word count of each surfaced chunk. The full per-query results are persisted at `analysis/issue-135-weak-pool-run-2026-07-21.json` so the numbers below are auditable without re-running the ~12-minute live sweep. (The reranker is mildly non-deterministic across runs, so a re-run may shift a few specific top chunks; the aggregate pattern is stable.)

**How the query sets split.** Of the 12 typo/off-topic queries, 8 tripped the weak-pool floor and 4 were rescued into a strong pool (expansion or the reranker found a passable match — e.g. "medtation technique" and "mindfulnes practice" both came back strong). Of the 16 benchmark queries, all 16 were strong. So the comparison is **8 weak-pool pages vs 20 strong-pool pages**.

**Top-result length, weak vs strong:**

| | weak-pool pages (8) | strong-pool pages (20) |
|---|---:|---:|
| top result ≤ 12 words | 6 (75%) | 2 (10%) |
| top-result word counts | 1, 1, 2, 2, 6, 6, 88, 107 | 3, 6, 24, 29, 39, 40, 42, 46, 46, 70, 72, 76, 84, 123, 139, 154, 156, 161, 163, 220 |

**All-surfaced-chunk length** (10 chunks per page):

| | weak-pool (80 chunks) | strong-pool (200 chunks) |
|---|---:|---:|
| ≤ 12 words | 66 (82.5%) | 42 (21.0%) |

The eight weak-pool top results:

| query | top chunk | words |
|-------|-----------|------:|
| consentration | AN 4.50:21 | 6 (the #133 fragment) |
| carburetor adjustment | ITI 38:12 | 1 |
| how to bake sourdough bread | SN 47.8:2 | 2 |
| python decorator syntax | UD 4.5:10 | 1 |
| kubernetes pod crashloop backoff | ITI 44:19 | 2 |
| how to fix a leaky faucet | MN 82:150 | 6 |
| quantum field theory explained | DN 1:19 | 107 |
| what is the capital of france | AN 9.39:8 | 88 |

**Part 2 answer.** Yes — weak-pool pages surface short, context-free chunks at roughly **four times the rate** of strong-pool pages: 75% vs 10% on the top result, 83% vs 21% across all surfaced chunks. Six of eight weak-pool pages put a fragment of 1–6 words at the top. The signal is consistent with the #133 repro and strong enough that the small sample (8 weak pages) is not a concern.

Two caveats keep this from being a deterministic rule:

1. **Weak pools do not always surface short chunks.** Two of eight weak-pool top results were long prose passages (DN 1:19 at 107 words, AN 9.39:8 at 88 words). When an off-topic query happens to land cosine-near a long passage, that passage wins the weak pool. So weakness and shortness are correlated, not identical.
2. **Short chunks can appear on strong-pool pages too.** Two strong-pool top results were short ("best pizza in naples" → 3-word top, "stock market prediction algorithm" → 6-word top) — the reranker scored the fragment above the floor. Length and rerank score are related but distinct signals.

**Why the correlation holds.** A short chunk (one verse line, one list item, one aphorism) has so few words that a single salient keyword can dominate its cosine similarity, and it has no surrounding prose to dilute a near-match. On an off-topic or misspelled query the dense retriever has no strong signal anywhere in the pool, so these keyword-salient fragments win by default. On a genuine query, real on-topic prose passages outscore the fragments and push them down or off the page. The weak-pool floor fires exactly in the case where the fragments' advantage is uncontested.

## Verdict

This is **a systemic pattern, not a narrow edge case** — but the system problem is the corpus shape, and the visible symptom is concentrated in weak pools.

- **Corpus side (systemic):** ~41% of content chunks (≈10,800 of 26,400) are inherently short, context-free lines — about 71% verse/poem lines and 29% prose-style list items, produced by the one-verse-per-chunk parse. They are concentrated in the verse and aphoristic nikāyas (ITI, KHP, UD, SN, AN). They exist by design, not by accident.
- **Surface side (concentrated in weak pools):** weak-pool pages put a short fragment at the top 75% of the time vs 10% for strong pools, and 83% of all chunks they surface are short vs 21%. So the "reads as broken" symptom the user saw in #133 is the predictable outcome of an off-topic/misspelled query falling into a corpus that is ~40% fragments — the weak pool has nothing better, so a fragment wins.

The implication for the fix decision (deferred to #133's "Fog", not decided here): excluding short chunks from weak-pool candidates would discard ~40% of the indexed content, including legitimate verse and aphorism passages a user might genuinely want — far too blunt. The two surgical options from #133 — merging adjacent verse lines at index time, or showing surrounding context for short chunks in the results UI — both address the symptom without removing the content. Merging adjacent lines would also shrink the 41% figure directly. Whichever fix is chosen, it should stay scoped to the Passages results view (ADR-0009's scope), since the deep-dive flow has its own book-attribution policy and no Match % to mislead.