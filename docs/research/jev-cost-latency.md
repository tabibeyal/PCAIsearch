# What does Jev cost us, and how much time does it add to a search?

Research for [What does Jev cost us, and how much time does it add to a search?](https://github.com/tabibeyal/PCAIsearch/issues/197),
ticket of the map [Put Jev to work in PCAIsearch](https://github.com/tabibeyal/PCAIsearch/issues/194).
Builds on the pricing and floor established in
[Make the API key reachable from code and from the live backend](https://github.com/tabibeyal/PCAIsearch/issues/195)
and the accuracy/harness work in
[Does Jev understand Buddhist and Pali text at all?](https://github.com/tabibeyal/PCAIsearch/issues/196)
([PR #202](https://github.com/tabibeyal/PCAIsearch/pull/202)). Measured 2026-09-21.

## Terms used in this report

- **Jev** — the nickname used on this map for TypeSafe AI's `jev-latest` model. It cannot write
  sentences; it only picks between choices written in advance, and every answer comes back as a
  probability.
- **Noul** — one of Jev's three answer shapes: "does this condition hold?", answered as a
  probability from 0 to 1. The out-of-scope guard and the reranker both use this shape.
- **Token** — the unit TypeSafe bills by. Roughly three-quarters of an English word. A short
  question is still billed for a **floor** of about 273 input tokens even if the words themselves
  are far fewer — established in issue #195.
- **Candidate / passage** — one chunk of scripture text the search pipeline is deciding whether to
  show. The reranker step scores every candidate in the pool against the search question.
- **Rate limit** — the largest number of requests (or tokens) the API accepts in a given
  stretch of time before it starts rejecting them with a `429` error. TypeSafe publishes one:
  1,200 requests per minute and 250,000 tokens per second.

## Summary of findings

1. **Pricing has not changed since the map's launch-day figure.** Live docs, checked 2026-09-21,
   confirm $0.042 per million input tokens, output tokens free, no published free tier.
2. **Correction: a numeric rate limit *is* published — this ticket's first pass missed it.**
   The `models` reference page states **250,000 tokens/second and 1,200 requests/minute**
   (20 requests/second), marked "adjusting dynamically" and subject to change, with higher
   limits on custom/enterprise plans. This is a materially better number than "undocumented,"
   which is what this ticket's own answer comment said before this file was written — see
   §4 for what it changes.
3. **The 273-token floor dominates the guard and (mostly) the reranker, not the per-token price.**
   At this project's realistic search volume, the price per token barely matters — the fixed
   floor per call is what adds up, because it applies once per call regardless of how short the
   text is.
4. **The out-of-scope guard is free in every practical sense.** One call per search,
   ~$0.0000115, well under a second.
5. **The reranker is the number that matters, and it splits into two separate questions.** The
   dollar cost is negligible at any volume this project has plausibly seen. The **latency**
   works out to roughly **4 seconds** for a search's 60 reranker calls, computed from the
   published rate limit — comparable to, maybe better than, today's CPU cross-encoder rerank
   (1.2–9.1s). That figure assumes the client keeps enough calls in flight to use the published
   rate; a client that calls one at a time would still take ~51 seconds regardless of what the
   limit allows.
6. **Triage is a different budget line, not a search-time cost.** One call per GitHub issue
   filed, not per search — a handful a week, a fraction of a cent each.
7. **Passage pool size confirmed from the code, not guessed:** `_RERANK_CANDIDATE_BUDGET = 60`
   (`backend/app/services/search_pipeline.py:166`) — 60 candidates go through reranking on every
   search that doesn't narrow to a single nikāya.

---

## 1. Pricing and limits — live docs vs. the map's launch-day figure

The map's Notes quote pricing from a launch announcement and flag it as possibly stale. Checked
against the live TypeSafe docs on 2026-09-21:

| Figure | Map's launch-day quote | Live docs, 2026-09-21 | Changed? |
|---|---|---|---|
| Input token price | ~$0.042 / million | $0.042 / million | No |
| Output token price | free | free | No |
| Free tier | not mentioned | none published — pay-as-you-go only | Confirmed absent |
| Rate limit (numeric) | not mentioned | **250,000 tokens/sec, 1,200 requests/min** (`models.md`) | **New — not in the map's Notes at all** |
| Max choices per question | 255 | not found on the pages checked this session | Not re-confirmed |

**The price has not changed since launch. The rate limit is a genuinely new finding for this
map** — it is not in the map's Notes and was not found by this ticket's own first pass either
(the answer comment already posted on this ticket says "no published numeric rate limit," which
this file corrects). The `models` reference page states it plainly:
"250,000 tokens per second / 1,200 requests per minute," flagged as "adjusting dynamically" —
i.e. it can move with demand and GPU capacity, and is not a contractual guarantee. Exceeding
either triggers `429 Too Many Requests`. Higher, more stable limits are available on
custom/enterprise plans, which implies this default is the early-access tier's number, not
necessarily a permanent one.

The reranking cookbook's own example (`ThreadPoolExecutor(max_workers=12)`) is still relevant
as a **working pattern** for how to call the API concurrently, but it is no longer the only
data point for how many calls can run at once — the account-level rate limit now sets that.

The cookbook also confirms a mechanical fact that matters for cost: **one API call per candidate
item, not batched.** Multiple *questions* about the same item can be packed into a single call
cheaply (TypeSafe measures 12.2x cheaper / 10x faster that way), but multiple *different*
candidates cannot share a call. That rules out batching the reranker's 60 candidates into fewer
calls.

## 2. The 273-token floor vs. the per-token price

Issue #195 established that even the simplest one-question call is billed for a floor of about
273 input tokens — not the handful of tokens the actual words would cost. At $0.042/million,
that floor alone costs:

273 tokens × $0.042 / 1,000,000 = **$0.0000115 per call**, before adding a single word of
passage text.

For the guard (one short question) and the triage call (one short question), the floor **is**
almost the whole cost — the real question text adds only a few more tokens. For the reranker,
each call also carries a passage, so the floor is a smaller share, but it still sets the price
that matters more than the exact word count: a 20-word passage and a 100-word passage cost
close to the same amount, because both are dwarfed by the 273-token floor plus overhead.

Passage lengths in this corpus, measured from the same chunk data behind the search index: median
20 words, mean 39, p90 105. Short. A realistic per-call size for the reranker, floor plus passage
plus question, is roughly **300–400 tokens** — the floor is doing most of the work, exactly as
the ticket suspected.

## 3. Real measured local pipeline (today, no Jev)

Reusing the harness style from PR #202 (`tests/prototypes/jev_pali_probe.py`), ran the actual
`SearchPipeline.search()` three times against the real Qdrant Cloud index and the real NVIDIA
expansion call. Synthesis (the final answer-writing step) is excluded — a separate, later stage.
BM25 is excluded — this local instance had none wired; production does.

| Query | Expansion (NVIDIA) | Retrieval (Qdrant) | Rerank (local cross-encoder) | Total |
|---|---|---|---|---|
| "what did the Buddha say about anger" | 5.01s | 0.30s | 1.20s (60 candidates × 2 query strings) | 6.61s |
| "why does loving someone lead to grief and suffering" | 3.50s | 0.35s | 7.38s (60 × 3) | 11.31s |
| "what is the one precept you should never break" | 2.10s | 0.33s | 9.11s (60 × 3) | 11.69s |

Two facts carried forward from this: the pool really is **60 passages** per search
(`_RERANK_CANDIDATE_BUDGET`, single-nikaya-unfiltered case), and today's CPU cross-encoder
rerank stage already costs **1.2–9.1 seconds** — it is not free today either, so a Jev rerank
is being compared against a real number, not against zero.

## 4. Per candidate spot

### Out-of-scope guard (one Noul call per search)

Cost: ~$0.0000115 per search — a rounding error at any volume. Latency: ~0.85s median
(measured in #196), but the guard needs nothing the pipeline doesn't already have at the start
(the raw query), so it can run concurrently with expansion the same way `expand_query` already
overlaps with initial retrieval today. Worst case it adds under a second to a pipeline that
already takes 6.6–11.7s. **Verdict: free in every practical sense.**

### Reranking (one Noul call per candidate, 60 candidates/search)

**Cost:** ~300–400 tokens/call × 60 calls × $0.042/million ≈ **$0.0009–0.0012 per search.**
Negligible against the $25/month backend bill until volume reaches the low tens of thousands of
searches per month — see the table below.

**Latency now has a documented number to compute from**, not just a precedent:

| If calls run… | Time for 60 calls | Basis |
|---|---|---|
| One at a time (serial) | ~51 seconds (0.85s × 60) | Worst case — a client that never overlaps calls |
| At the published rate limit (1,200 req/min = 20 req/s) | ~3.85 seconds (60 ÷ 20 = 3.0s to send them all, + 0.85s for the last one to finish) | Best available estimate, using the account's stated ceiling |
| At TypeSafe's own cookbook precedent, 12 concurrent | 60 ÷ 12 = 5 rounds × 0.85s ≈ 4–5 seconds | Cross-check — close to the rate-limit figure, which is reassuring |

The rate-limit estimate and the cookbook-precedent estimate land within about a second of each
other, which is a good sign — two different sources of evidence agree on roughly **4 seconds**
for a search's reranking step, comparable to or better than today's CPU cross-encoder (1.2–9.1s).

Two caveats keep this from being a settled number, and are why #200 (the reranking prototype)
still needs to measure real throughput rather than trust this arithmetic outright:

- **"Adjusting dynamically"** — TypeSafe's own words for the published limit. It can be lower
  under load, and the early-access tier's default may not match what a paying account gets.
- **The estimate assumes the calling code keeps enough requests in flight** (Little's Law:
  roughly 17 concurrent calls to sustain 20/second at 0.85s each). A naive implementation that
  calls one at a time, or caps concurrency low "to be safe," would land closer to the 51-second
  case regardless of what the account is allowed to do. This is an implementation choice for
  #200's prototype, not a TypeSafe constraint.

This sharpens, but does not remove, the map's Fog item "what happens when TypeSafe is down or
rate-limits us" — the *ceiling* is now documented, but real behavior at that ceiling (and what
happens when it's hit mid-search) is still unmeasured.

One more finding worth carrying into the reranking prototype: today's rerank step asks
2–3 query-string variants per candidate specifically because the cross-encoder is English-only
and needs a hint to bridge Pāḷi loanwords. #196 found Jev reads those loanwords natively — so a
Jev rerank may only need **one** call per candidate, not 2–3, which would roughly halve or third
both the cost and the latency estimates above.

### Citation guardrail — excluded

Already decided on the map: `CitationGuardrail` is an exact, deterministic lookup, not a
judgment call. No Jev calls, no cost, nothing to compute here.

### GitHub issue triage labels — decoupled from search volume

One call per *issue filed*, not per *search*. Issue volume on this repo is a handful a week at
most. At the same ~300-token floor, cost is a fraction of a cent per issue — a different budget
line from the search-time spots, not additive with them.

## 5. Against the $25/month bill

No usage telemetry exists for this project — no analytics wired into the frontend or backend,
and the live site's searches have been failing since the `LLM_MODEL` retirement, so there is no
current traffic to sample. Rather than guess a volume, here is the added monthly cost as a
function of it. Guard + reranker combined; triage omitted as a separate budget line:

| Searches/month | Guard | Reranker (60 calls, 1 variant) | Reranker (60 calls, 3 variants) | Total added |
|---|---|---|---|---|
| 100 | $0.001 | $0.03–0.04 | $0.09–0.12 | under 15 cents |
| 1,000 | $0.01 | $0.30–0.40 | $0.90–1.20 | 30 cents–$1.20 |
| 10,000 | $0.12 | $3–4 | $9–12 | $3–12, i.e. rivaling the existing $25/month bill |
| 100,000 | $1.15 | $30–40 | $90–120 | would dominate the bill |

**Take-away:** at any volume this pre-launch project has plausibly seen so far, Jev's added cost
rounds to nothing. It only becomes a budget-relevant line item somewhere in the low
tens-of-thousands-of-searches-per-month range.

---

## What this report does not answer

- **Real measured throughput against the live API.** The ~4-second figure for reranking is
  computed from the published rate limit and cross-checked against the cookbook's precedent —
  it is not a measurement. Confirming the pipeline actually achieves it, and what happens if the
  published limit turns out lower under real conditions, is
  [Would a Jev score rerank better than the English-only cross-encoder?](https://github.com/tabibeyal/PCAIsearch/issues/200)'s job.
- **What happens on `429`/`529` mid-search.** Whether a rate-limited or overloaded call should
  fail the search or fall back silently is a design choice, not a cost question, and stays in the
  map's Fog.
- **Today's real search volume.** No telemetry exists to sample; the table above is deliberately
  shaped as "cost at X volume" rather than "here is the bill" for that reason.

## Sources

**Live measurement, 2026-09-21** — `SearchPipeline.search()` run locally against the production
Qdrant Cloud index and the real NVIDIA expansion endpoint, harness style reused from
[PR #202](https://github.com/tabibeyal/PCAIsearch/pull/202)
(`tests/prototypes/jev_pali_probe.py`). `TYPESAFE_API_KEY` loaded from
`/home/eyal/PCAIsearch/.env`.

**Live docs, 2026-09-21** — `docs.typesafe.ai/models.md` (pricing, rate limits),
`docs.typesafe.ai/api.md` (error codes, retry guidance), and
`docs.typesafe.ai/cookbooks/rerank_typesafe.md` (concurrency precedent), fetched directly this
session (via the `typesafe:typesafe-ai` skill's guidance to always read the live docs).

**Repo files** — `backend/app/services/search_pipeline.py:166` (`_RERANK_CANDIDATE_BUDGET`),
corpus chunk data behind the search index.

**Prior tickets** — [#195](https://github.com/tabibeyal/PCAIsearch/issues/195) (273-token floor,
API shape), [#196](https://github.com/tabibeyal/PCAIsearch/issues/196) (accuracy, per-call
latency, cost per call).
