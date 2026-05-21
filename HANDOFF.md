# Handoff — Session 2026-05-21 (latest)

## What happened this session (2026-05-21)

**Sub-session 11 — Mobile background/foreground bug + double-request fix:**

- **Root cause diagnosed:** backgrounding the app on mobile caused two problems:
  1. If the stream was still in progress, the mobile browser killed the fetch → `setError` fired → "Search Error" shown on return.
  2. React StrictMode (enabled in `npm run dev`) double-invokes effects synchronously. Both invocations sent a fetch to the backend → NVIDIA API serialised them → ~60s response time instead of ~30s.
- **Fix 1 — `setTimeout(0)` debounce** (`SynthesisLoader.tsx`): stream start is deferred by one event-loop tick. StrictMode's cleanup fires synchronously within the same tick and calls `clearTimeout`, so the phantom request is never sent. Only one request reaches the backend.
- **Fix 2 — `AbortController`** (`SynthesisLoader.tsx`, `lib/api.ts`): signal threaded through `streamSynthesis(query, nikayas, signal)`. On effect cleanup, `controller.abort()` is called — browser cancels the in-flight connection so the backend can stop sooner.
- **Fix 3 — sessionStorage cache**: completed `SynthesisResponse` written to `sessionStorage` on `done` event (key: `synthesis:<query>:<nikayas>`). On mount, cache is checked first; if hit, answer is shown instantly with no stream request. Handles the page-reload-on-return case.
- **Fix 4 — visibility-based auto-retry**: if the stream was killed mid-flight (component still mounted, error state set), a `visibilitychange` listener fires when the page becomes visible again and increments `retryCount`, re-running the streaming effect.
- **Fix 5 — "Try again" button**: error screen now has a one-tap retry button (non-rate-limit errors only) alongside "Return to home".
- Files changed: `frontend/components/deep-dive/SynthesisLoader.tsx`, `frontend/lib/api.ts`.
- Commit: `e410ff1`.

**Sub-session 10 — Mobile donation banner:**

- `SupportBanner` converted to a client component. On mobile (< 768px) it is hidden by default and slides in from the bottom when the user scrolls within 80px of the end of any large scroll container (captured via `document.addEventListener('scroll', ..., { capture: true })`). Scrolling back up hides it. Desktop behavior unchanged — always visible in flow.
- **Bug fix (fast-scroll):** in-flow positioning caused the banner's ~141px height to shrink the `main` flex container when it appeared, pushing `FeedbackBar` out of the `SynthesisView` scroll container. Switched to `position: fixed bottom-0` on mobile (`md:static` returns it to flow on desktop). Added a `--banner-h` CSS variable + `data-banner-open` attribute on `<html>` so a global CSS rule pads all `div.overflow-y-auto` / `div.overflow-auto` containers on mobile, keeping bottom content reachable above the fixed banner.
- Files changed: `frontend/components/SupportBanner.tsx`, `frontend/app/globals.css`.

**Sub-session 8 — Feedback mechanism:**

Built a full thumbs up/down feedback mechanism attached to every synthesis answer.

- **Backend:** `POST /feedback` endpoint in `main.py`. Request body: `{query, answer, rating, category, comment}`. Stores to `feedback.db` (SQLite, initialized in the `lifespan` context manager at startup). Rate-limited. Validates `rating` as a literal type (`"up"` | `"down"`). Uses `datetime.now(UTC)` (not deprecated `utcnow()`).
- **Frontend:** `FeedbackBar` component (`frontend/components/deep-dive/FeedbackBar.tsx`) — thumbs up/down buttons, 5-category downvote panel, optional free-text comment, paper airplane submit icon. Appears below the synthesis answer once streaming completes. `submitFeedback()` typed fetch wrapper added to `lib/api.ts`.
- **Integration:** `FeedbackBar` rendered in `SynthesisView.tsx`. `query` prop threaded down: `SynthesisLoader` → `DualPaneContainer` → `SynthesisView` → `FeedbackBar`.
- **Behavior:** thumbs up → immediate confirm, no panel. Thumbs down → opens category panel; submit collapses panel and shows "Thank you". Once submitted, both buttons disabled for the session. Disclaimer: *"Feedback includes your question and this full answer."*
- Fixed double-scroll jank on results page (unrelated UI regression).

**Sub-session 9 — Pāḷi dictionary expansion + nikaya filter fix:**

- **Nikaya filter bug fixed:** Qdrant Cloud requires an explicit keyword payload index on any field used in filters. The `nikaya` field had no index, causing 400 errors when a nikaya filter was applied. Added idempotent index creation at startup in `main.py`.
- **19 new pali_dictionary entries** across: Four Foundations of Mindfulness (satipaṭṭhāna, all 4 individually keyworded with Thanissaro translations); Five Spiritual Faculties / Five Powers (pañcaindriya / pañcabala); Four Bases of Power (iddhipāda); Six Sense Bases (āyatana, gratification/danger/escape keywords); Dāna / Generosity; Three Trainings (tisikkhā); Disenchantment chain (nibbidā → virāga → release); Liberation of mind / through discernment (cetovimutti / paññāvimutti); Body contemplation / asubha; 37 Wings to Awakening; Skillful / unskillful roots (kusala / akusala); Heedfulness (appamāda, last words of the Buddha); Anger / aversion (kodha / āghāta); Grief and loss (soka / parideva).

---

# Handoff — Session 2026-05-20

## What happened this session

**Sub-session 6 — Deployment + citation/streaming fixes:**
- Deployed live: Netlify (frontend, manual deploy) + DigitalOcean 2GB Droplet (backend) + Qdrant Cloud (134K vectors) + NVIDIA API. See ADR-0003.
- Added `/health` endpoint to backend.
- Fixed streaming latency: added `X-Accel-Buffering: no` + `Cache-Control: no-cache` headers to SSE endpoint — disables nginx proxy buffering on DigitalOcean.
- System prompt tightened: require responses to paraphrase passage content (not just cite), cap 3 citations per bracket, place citations immediately (no end-paragraph dumps).
- Passage filter: switched from 30-char to 4-word minimum — fixes "No source verses found" regression caused by BM25 returning chapter headers like "7. Overcome" (2 words) that the old 30-char filter wiped out.
- Added craving/addiction cluster to ExpansionPrompt v6 reference table and `pali_dictionary.py` — āsava/taṇhā/rāga keywords, english_hint with "consumed by craving overwhelmed by desire ferment taint clinging".

**Sub-session 7 — Thanissaro Bhikkhu translations across pali_dictionary:**

Added Thanissaro's primary translations as first-class keywords and expansion prompt terms for all major doctrinal lists. Each list now has every member as its own searchable keyword (Pali + English).

| Pali term | Thanissaro prime | Previously |
|-----------|-----------------|------------|
| mettā | good will | loving-kindness |
| anicca | inconstant | impermanent |
| anattā | not-self | no-self |
| dukkha | stress | suffering |
| saṅkhāra | fabrications | formations |
| sammā-saṅkappa | right resolve | right intention |
| vicikicchā | uncertainty | doubt |
| saḷāyatana | six sense media | six sense bases |
| vitakka | directed thought | applied thought |
| vicāra | evaluation | sustained thought |
| ekaggatā | singleness of preoccupation | unification of mind |

New full-list entries added or expanded:
- **Seven awakening factors** (bojjhaṅgā) — inserted before nibbāna entry to avoid "awakening" keyword collision; all 7 factors individually keyworded.
- **Five hindrances** — all 5 individually keyworded; "uncertainty" as prime for vicikicchā.
- **Noble Eightfold Path** — all 8 factors individually keyworded with Pali transliterations.
- **Four Noble Truths** — all 4 truths individually keyworded; "origination of stress", "cessation of stress", "unbinding", "path of practice".
- **Dependent Origination** — all 12 links individually keyworded; "six sense media", "fabrications", "becoming", "aging-and-death".
- **Four Brahmavihārās** — all 4 individually keyworded; english_hints added.
- **Jhāna factors** — all 5 form-jhāna factors + all 4 immaterial attainments keyworded.
- **Five Aggregates** — all 5 aggregates individually keyworded.

**Structural fix — word-boundary lookup:**
- `lookup()` and `lookup_english()` now use `re.search(r"\b" + re.escape(kw) + r"\b", q)` instead of plain `kw in q`.
- Prevents false substring matches: "form" no longer matches "formless jhana"; "consciousness" no longer matches "infinite consciousness" (jhāna attainment) when the aggregates entry comes first.
- `"perception aggregate"` and `"consciousness aggregate"` used in the aggregates entry to preserve specificity without stealing broad jhāna queries.

---

## What happened previous sessions

**Recall pushed from 60% → 93% (14/15).**

Four sub-sessions of work (previous + this session):

**Sub-session 1 — BM25 hybrid retrieval (previous):** Built BM25 retrieval fused with dense results via RRF.

**Sub-session 2 — nikayas filter parity:** Fixed `BM25Retriever.retrieve()` ignoring the `nikayas` restriction.

**Sub-session 3 — benchmark investigation:** Loosened benchmark gold standard; diagnosed expansion underperformance; fixed BM25 to run on all expanded variants.

**Sub-session 4 — expansion recall fix:**
- Diagnosed two bugs: (1) first-seen dedup of dense results destroyed meaningful ranking; (2) benchmark's `--with-expansion` path never injected BM25 — it was testing dense-only the whole time.
- Added `rrf_fuse_multi` — proper multi-list RRF over N ranked lists.
- Replaced first-seen dense dedup with `rrf_fuse_multi(per_query)` in `SearchPipeline.search()`.
- Added `ExpansionPrompt` v2: strict two-line contract (Line 1 = English passage vocab, Line 2 = Pāḷi doctrinal term cluster). Switched pipeline default to v2.
- Fixed benchmark to inject `BM25Retriever` into the `--with-expansion` path.
- Added `--log-variants` flag to benchmark for variant inspection.

**Sub-session 5 — rerank_multi + English hints (this session):**
- Added `rerank_multi` to `search_pipeline.py`: cross-encoder scores each candidate against `[original_query, english_hint]` and takes the max.
- Added `english_hint` field to `DictionaryEntry` in `pali_dictionary.py` — verbatim passage fragment from the target sutta.
- Reranking scoped to original query + curated dict hints only (LLM variants excluded — add noise).
- MN 61 `english_hint` corrected to match actual sutta vocabulary ("bad deed" / "deliberate lie").
- ExpansionPrompt advanced through v3 → v6: Pāḷi reference table, few-shot example, English passage hints.
- Fixed `expand_query` stripping `"Line N:"` label prefixes from LLM output.
- Final benchmark: **14/15 (93%)** — stable across two runs. Only miss: SN 12.1 (structurally hard).

---

## Recall@10 scoreboard

| Mode | Hard | Medium | Easy | Total |
|------|------|--------|------|-------|
| Dense only | 3/5 | 1/5 | 0/5 | 4/15 (26%) |
| BM25 + dense (no expansion) | 4/5 | 2/5 | 1/5 | 7/15 (46%) |
| Expansion + BM25 (fixed) | 3/5 | 3/5 | 2/5 | 8/15 (53%) |
| + Pāḷi dict + v3 prompt | 3/5 | 3/5 | 3/5 | 9/15 (60%) |
| **+ rerank_multi + English hints (v6 prompt)** | **5/5** | **4/5** | **5/5** | **14/15 (93%)** |

### What the final push gained

New hits (v6 prompt + rerank_multi): MN 21 (saw simile), AN 3.65 (Kālāma — teaching worth following), SN 22.59 (five aggregates/anattā), MN 61 (first precept — lying).

Only remaining miss: SN 12.1 — paṭicca-samuppāda passage not retrievable by embedding model in its current corpus form.

---

## Recent commits (2026-05-21)

- `550c9d4` — `fix: prevent donation banner from pushing FeedbackBar out of view on mobile`
- `fffdebd` — `feat: hide donation banner on mobile until user scrolls to bottom`
- `63a8a81` — `fix: restore mobile scroll by adding min-h-0 to flex height chain`

## Earlier commits (2026-05-20)

- `d351a67` — `feat: add jhāna factors with Thanissaro translations + word-boundary lookup fix`
- `89ccf6f` — `feat: expand four brahmavihārās with Thanissaro translations`
- `514087c` — `feat: expand Dependent Origination entry with Thanissaro translations`
- `ccd2013` — `feat: expand Four Noble Truths entry with Thanissaro translations`
- `f761a29` — `feat: expand Noble Eightfold Path with Thanissaro translations`
- `56079c5` — `feat: expand five hindrances entry with Thanissaro translations`
- `aabc400` — `feat: add seven awakening factors (bojjhaṅgā) with Thanissaro translations`
- `02a74e9` — `feat: add individual aggregate keywords and 'fabrications' to Five Aggregates entry`
- `a3c1540` — `feat: add 'stress' as prime translation for dukkha (Thanissaro)`
- `37eaa02` — `feat: add Thanissaro translations as primary terms for metta/anicca/anatta`
- `4330531` — `feat: add craving/addiction cluster to expansion prompt and pali dictionary`
- `cc176aa` — `fix: switch passage filter from character count to word count (>=4 words)`
- `9aced1e` — `fix: disable nginx proxy buffering on SSE stream endpoint`
- `212192e` — `fix: cap citations per bracket at 3, forbid end-of-paragraph dumps`

## Earlier commits (2026-05-17)

- `85675fb` — `docs: update CONTEXT.md retrieval pipeline with new components`
- `d905a56` — `docs: update CLAUDE.md with current test command, benchmark, and architecture`
- `777157c` — `feat: use English-only passage hints for reranking (drop Pāḷi terms)`
- `c8999c4` — `feat: rerank against original + curated dict hints only (not LLM variants)`
- `3cb3bd3` — `feat: rerank against all expanded query variants (max score)`
- `e494c09` — `fix: correct MN 61 english_hint to exact sutta vocabulary`
- `657964c` — `feat: add english_hint to DictionaryEntry for verbatim passage vocabulary`
- `b2acad9` — `fix: strip 'Line N:' label prefixes from expansion variants + fix v6 example contamination`
- `9f6c6e4` — `feat: add ExpansionPrompt v6 with second example and Rahula-specific entry`
- `5e16d48` — `feat: add ExpansionPrompt v5 with English passage hints in reference table`
- `f0e4123` — `feat: add ExpansionPrompt v4 with few-shot example to prevent prompt leakage`

---

## What was built (cumulative)

### Files

| File | Purpose |
|------|---------|
| `backend/app/services/bm25_retriever.py` | `BM25Retriever` — BM25Okapi over English verses; `retrieve(query, top_k, nikayas=None)`; `from_directory(dumps_dir)` |
| `backend/app/services/fusion.py` | `rrf_fuse(dense, sparse, k=60)` + `rrf_fuse_multi(lists, k=60)` — Reciprocal Rank Fusion |
| `tests/backend/test_bm25_retriever.py` | 13 unit tests |
| `tests/backend/test_fusion.py` | 22 unit tests (11 for `rrf_fuse`, 11 for `rrf_fuse_multi`) |
| `tests/backend/retrieval_benchmark.py` | Recall@10 benchmark; `--with-bm25`, `--with-expansion`, `--no-rerank`, `--log-variants`, `--k` flags |

### Modified files

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | Hierarchical RRF (`rrf_fuse_multi` for dense, then `rrf_fuse` vs BM25); ExpansionPrompt v2; default v2; raises on unknown version |
| `backend/app/main.py` | Builds `BM25Retriever` at startup and injects into `SearchPipeline` |
| `tests/backend/test_search_pipeline.py` | 13 tests total |

---

## Search flow (current)

```
query
  └─► expand_query → [q1, q2, q3]   (ExpansionPrompt v2: English vocab + Pāḷi term cluster)
        ├─► dense retrieve (Qdrant, nikayas filter) × 3 queries
        │       └─► rrf_fuse_multi([dense_q1, dense_q2, dense_q3]) → dense_fused
        └─► BM25 retrieve (nikayas filter) × 3 queries
                └─► best bm25_score per verse kept → bm25_merged
                                                    ▼
                                    rrf_fuse(dense_fused, bm25_merged)
                                                    ▼
                          rerank_multi([original_query, english_hint])
                          cross-encoder takes max score per candidate
                                                    ▼
                                            top_k results
```

---

## Test suite

**144 passed**, 6 pre-existing errors in `test_api.py` (missing `NVIDIA_API_KEY` in test env — unchanged).

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

---

## Open issues / next steps

### SN 12.1 — last hard miss

Paṭicca-samuppāda passage not retrievable via embedding model. Options: hand-crafted `english_hint` in pali_dictionary pointing at the dependent origination chain, or ingest a richer version of SN 12.1.

### Phase 2 — Vinaya ingestion (deferred)

Parser regex `r"([a-zA-Z]+)([\d.]+)"` won't match `pli-tv-bu-vb-pj1` IDs — needs extension before Vinaya can be ingested.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — dense vector retrieval against Qdrant; injectable seam (`Retriever`)
- **BM25Retriever** — in-memory BM25 over English verses; loaded from `data/dumps/` at startup; injected into `SearchPipeline`; accepts optional `nikayas` filter (post-score, full-corpus IDF); runs on all expanded query variants
- **rrf_fuse** — two-list Reciprocal Rank Fusion; pure function in `fusion.py`; `k=60` default
- **rrf_fuse_multi** — N-list Reciprocal Rank Fusion; each list contributes independently; first-occurrence payload wins; used for dense side of hierarchical fusion
- **rerank_multi** — cross-encoder scores each candidate against `[original_query, english_hint]`, takes max; English-only model so Pāḷi excluded; defined in `search_pipeline.py`
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15; `get_title_text()` returns v3 for SN/AN chapter-header suttas
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; v2 is default (two-line: English passage vocab + Pāḷi term cluster); raises `ValueError` on unknown version
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?"
- **SuttaRelations** — answers "what is related to sutta X?"
- **retrieval_k** — internal candidate pool = `max(top_k * 3, 30)`; used for dense and BM25 per query
- **PaliDictionary / lookup** — `pali_dictionary.py`; ~65 `DictionaryEntry` objects (label, keywords, pali, english_hint); `lookup(query)` / `lookup_english(query)` use word-boundary regex (`\b...\b`) — not substring — to avoid false matches like "form" → "formless"; pali cluster used in expansion, english_hint fed to `rerank_multi`; all major doctrinal lists have each member as an individual keyword using Thanissaro Bhikkhu's primary translations
- **english_hint** — verbatim passage fragment stored in `DictionaryEntry`; bridges vocabulary gap between query and sutta text for the cross-encoder
- **Thanissaro primes** — primary translations used throughout: good will (mettā), inconstant (anicca), not-self (anattā), stress (dukkha), fabrications (saṅkhāra), directed thought (vitakka), evaluation (vicāra), singleness of preoccupation (ekaggatā), right resolve (sammā-saṅkappa), uncertainty (vicikicchā), six sense media (saḷāyatana)
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
