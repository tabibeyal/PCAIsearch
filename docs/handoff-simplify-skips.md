# Simplify handoff — items left out

These were identified during the `/simplify` run on 2026-06-05 (commit `898d0ba`)
but deliberately not applied because each carries non-trivial risk or behaviour
trade-offs that need a focused session to do right.

**Status as of 2026-06-05:**
- ~~**Item 1: Unify `search()` paths~~ — **DONE.** Commit `435d674` on
  `main-branch` / `master` (PRs #14 and #15). recall@10 = 15/15 (100%);
  204/204 backend tests pass.
- Item 2: Flatten `SearchResultsLoader` state machine — open.
- Item 3: Replace SupportBanner ↔ deep-dive coupling with React context — open.
- Item 4: Fix the landing-page hydration at the source — open.

---

## 1. ~~Unify the two `search()` paths and batch the reranker once~~ DONE

Shipped in commit `435d674` (PRs #14 and #15, both merged 2026-06-05).

`search()` now runs a single path: normalise nikayas into buckets, run shared
BM25 once and partition, fan out retrieve+fuse per bucket in parallel, union
candidates, rerank the union in one batched `rerank_multi` call, partition the
scored list back by bucket, round-robin interleave. `_run_pipeline` is a
"retrieve + fuse" helper; the dead `prefetched_first is None` branch is gone.

Interleave budget is **loose** (round-robin draws from each bucket's full
ranked list, not a top-K/N pre-trim) so small nikayas like DHP can surface
their second-best match in the final top 10.

Verification: 204/204 backend tests pass (including the two critical behaviour
guards — multi-nikaya inclusion and nikaya-filter purity); recall@10 = 15/15
(100%) on the unified code; `scripts/run_recall_benchmark.sh` is the repeatable
harness for future before/after measurement.

---

## 2. Flatten the `SearchResultsLoader` state machine

**File:** `frontend/components/search/SearchResultsLoader.tsx` — lines 92–164

**What's wrong.**  
The component carries three boolean/enum pieces of state (`phase`, `resultsReady`,
`showResults`) coordinated by four separate `useEffect` hooks that each test each
other's values (`if (showResults) return`, `if (!resultsReady || showResults) return`,
`if (phase !== 2 || !resultsReady || showResults)`). `resultsReady` is never read for
any purpose other than triggering re-renders — it exists because setting a `ref` alone
doesn't re-render.

The `TIMING_KEY = 'passages_avg_ms_v3'` comment ("v3: clears stale data from earlier
uncapped measurements") signals this localStorage timing estimator has already been
rebuilt twice. All the clamping guards (`MIN_STEP_MS`, `MAX_STEP_MS`, `MAX_AVG_MS`,
`TIMING_N`) are accreted from prior breakage, not first-principles design.

**The deeper fix.**  
Replace `resultsReady` with a `useReducer`-based phase enum that includes a terminal
state (`'done'`), so results arriving sets the phase directly instead of needing a
separate flag to nudge it. The fetch effect calls `dispatch({ type: 'results', data })`
and the timer effects become one effect on the phase. Removes two state variables and
two effects.

Separately: consider dropping the localStorage timing model entirely and using fixed
generous intervals (or streaming stage events from the backend if you ever add them).
The reveal logic is already correctly gated on real results — the estimator only affects
cosmetic message pacing, which doesn't justify persisted cross-session state.

**Why it was skipped.**  
The loading screen behaviour is working and the timing model was built deliberately
(it's the third version). Changing it is a behaviour change, not a mechanical cleanup.
Deserves an intentional session, not a side-effect of a simplify run.

---

## 3. Replace the SupportBanner ↔ deep-dive coupling with React context

**Files:**
- `frontend/components/SupportBanner.tsx` — lines 7–17 (event listener)
- `frontend/components/deep-dive/DualPaneContainer.tsx` — line 39 (dispatch)
- `frontend/components/deep-dive/SynthesisView.tsx` — line 109 (sentinel div)

**What's wrong.**  
Three magic constants encode one relationship and must stay in sync with nothing
enforcing them:
- `'deepDiveChanged'` — the event name (used in two files)
- `'data-support-trigger'` — the sentinel attribute (queried from the DOM, not passed
  as a ref)
- `h-36` (144px) in `SynthesisView` — must equal the banner's rendered height;
  the comment says so but nothing checks it

The `deepDiveOpenRef` in `SupportBanner` is a shadow copy of state owned by
`DualPaneContainer`, maintained via a DOM event rather than through React.

**The deeper fix.**  
`SupportBanner` and `DualPaneContainer` are siblings rendered by the same search
page (`frontend/app/search/[query]/page.tsx`). A small `SupportBannerContext` provided
at that page lets `DualPaneContainer` call `setDeepDiveOpen(deepDive)` directly and
`SupportBanner` read it — no window event, no magic strings, no ref. The sentinel
spacer's height (`h-36`) should become a shared CSS token or a constant imported by
both `SynthesisView` and whatever calculates the banner's padding, so drift is a
compile error rather than a visual glitch.

**Why it was skipped.**  
Functional and isolated today. The coupling is fragile but not actively broken.
Fixing it correctly means lifting state to a context at `page.tsx` — a small but
deliberate design change.

---

## 4. Fix the landing-page hydration at the source, not with two bandaids

**Files:**
- `frontend/app/page.tsx` — line 13: `<SearchBarClient />` (dynamic ssr:false wrapper)
- `frontend/components/search/SearchBarClient.tsx` — new file with `ssr: false`
- `frontend/app/layout.tsx` — lines 21–22: `suppressHydrationWarning` on `<html>` and `<body>`
- `frontend/components/search/SearchBar.tsx` — `suppressHydrationWarning` on `<textarea>`

**What's wrong.**  
Two separate mitigations for the same underlying problem. `SearchBar` has
non-deterministic content at hydration time: the typing animation (`animText`),
the blinking cursor (`cursorOn`), and `caretColor` derived from `query` all produce
different values on the server and client. `ssr: false` solves it for the landing page
by skipping server rendering entirely; `suppressHydrationWarning` silences warnings
where the mismatch would otherwise surface.

The `ssr: false` wrapper has a real cost: the search box (the primary above-the-fold
element) pops in client-side after a blank, hurting LCP and the no-JS experience.

**The deeper fix.**  
Drop `SearchBarClient` and render `<SearchBar>` directly in `page.tsx`. Make `SearchBar`
hydration-safe by gating all animation state behind a `mounted` flag set in a
`useEffect` (so server and first client render are identical plain state). Then
`suppressHydrationWarning` on all three elements becomes unnecessary too. Both
bandaids go away, the search box is server-rendered again, and the `SearchBarClient`
wrapper file is deleted.

**Why it was skipped.**  
The `ssr: false` choice may be intentional — a deliberate LCP tradeoff trading a
slightly blank first paint for simpler hydration management. Confirm whether you want
the box SSR'd before applying.

---

## Minor: ~~unreachable fallback branch in `_run_pipeline`~~ DONE

Resolved as a side-effect of item 1. `_run_pipeline` no longer has the
`prefetched_first is None` branch — the parameter is non-optional, the dead
else is gone.
