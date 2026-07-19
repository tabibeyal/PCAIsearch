# PCAIsearch — Domain Context

Vocabulary used in the codebase. Update inline as terms are resolved.

## Corpus

- **Sutta Piṭaka** — currently the only ingested division of the Pāḷi Canon. Suttas across DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP. Source: Thanissaro Bhikkhu's translations from the dhammatalks.org epub (`fetch_thanissaro.py`). English-only; Pāḷi body text is not included.
- **Vinaya Piṭaka** — not yet ingested. Planned but deferred behind the philological-cross-reference work.
- **Aṭṭhakathā** — Pāḷi commentaries. Not yet ingested. English coverage upstream is ~10–15%; Pāḷi and Thai coverage is much fuller. Phase-3 corpus.

## Retrieval pipeline (existing)

- **Pipeline** — RAG orchestrator: expand → retrieve (dense + BM25) → RRF fusion → rerank → synthesize (`backend/app/services/search_pipeline.py`). Recall@10: ~86–93% on 15-query benchmark (regression introduced 2026-06-03, fix committed 2026-06-04; awaiting re-benchmark).
- **Kept context** — the filtered, deduplicated chunk list produced by `prepare_context`, public on `Pipeline`: near-empty chunks (<4 words English) dropped, duplicate English text collapsed to first occurrence. Invariant: synthesis, the Guardrail, the Receipt, and the API response must all see the same kept-context list — none should independently re-filter or see a different set than the others.
- **Retriever** — Qdrant vector retrieval over a single `pali_canon` collection. Injectable seam (`backend/app/services/retriever.py`).
- **BM25Retriever** — sparse keyword retrieval over English text. Fused with dense results via RRF (`backend/app/services/bm25_retriever.py`).
- **ExpansionPrompt** — versioned LLM prompts for query expansion; currently v6. Outputs English vocab line + Pāḷi terms line. Pāḷi terms are used for retrieval only — not passed to the reranker (`backend/app/services/search_pipeline.py`).
- **pali_dictionary** — keyword-matched lookup returning Pāḷi terms (`lookup`) and verbatim English passage hints (`lookup_english`). The English hints are appended as a 5th search variant and also used as the second reranking query (`backend/app/services/pali_dictionary.py`). ~84 entries covering all major doctrinal lists with Thanissaro Bhikkhu's primary translations.
- **Reranker** — cross-encoder (`ms-marco-MiniLM-L-6-v2`). `rerank_multi` scores each candidate against multiple queries and takes the max; currently called with `[original_query, english_hint]`. Pāḷi terms are excluded — the model is English-only (`backend/app/services/search_pipeline.py`).
- **Guardrail** — sole authority on citation validity in a synthesized answer (`backend/app/services/guardrail.py`). Scans the answer text for `[ID:Verse]` citations and marks each invalid one visibly in place: `[Hallucinated]` (ID doesn't exist in the canon — checked via `CitationOracle`) or `[Unverified]` (ID is real but wasn't in the retrieved kept context). Does not silently delete invalid citations — see ADR-0006.
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`backend/app/services/citation_oracle.py`).
- **Feedback** — `POST /feedback` endpoint in `main.py`. Stores thumbs-up/down ratings with optional category + comment to Supabase Postgres in production (via `SUPABASE_URL` / `SUPABASE_KEY` env vars); falls back to local SQLite when those vars are absent. No admin UI; review via Supabase dashboard in production.
- **Shared answer snapshot** — a persisted copy of one synthesized answer (query + answer text + context), created only when a user clicks the Share button, kept forever, served read-only at `/share/{id}`. Distinct from re-sharing a live query link (`/search/{query}?view=synthesis`), which would re-run synthesis and could produce different text. See ADR-0005.
- **Receipt** — an HMAC computed server-side over `(query, answer, context)` at synthesis time, returned to the client and required unchanged on `POST /share`. Proves a shared snapshot is byte-identical to something the pipeline actually generated, without re-running the (non-deterministic) LLM or holding server-side session state. See ADR-0005.
- **AnswerComposer** — the deep module behind both `/synthesize` and `/stream`; owns the compose flow (kept context → synthesize → Guardrail → attach passages/titles → Receipt) so it's written once instead of drifting between the two routes. Depends on `Pipeline`, `Guardrail`, `PassageStore`, `SuttaTitleIndex`, and the share-receipt secret — each passed in directly, not reached-through via another collaborator. Raises on failure rather than swallowing; `answer_stream` yields typed `status`/`chunk`/`done` events, with SSE encoding and error-to-`error`-event conversion left to the route as transport glue.
- **SuttaRelations** — hand-curated doctrinal pairs + ±2 numeric adjacency within a nikāya. Surfaces a "see also" sutta list per query (`backend/app/services/sutta_relations.py`).
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15. Boosts retrieval when the query matches a canonical title (`backend/app/services/sutta_title_index.py`).
- **Chunk ID** — verse-level identifier in the form `"<nikāya> <number>:<verse>"`, e.g. `"MN 27:14"`. Used end-to-end (Qdrant payload, citations, related-suttas API).

## Results display

- **Book-representation policy** — the `policy` argument to `SearchPipeline._select_results` (`search_pipeline.py`): `round_robin` (every selected book guaranteed a slot in the result set), `global_best` (pure rerank-score order, no guarantee), or `relevance_floor:<ratio>` (round-robin gated by a score ratio; empirically rejected, see ADR-0007). Results view uses `round_robin`; the deep-dive answer flow uses `global_best`. See ADR-0007.
- **Match %** — the `score` field (0.5–0.99) shown on results-view cards as "N% match". Computed by rank-normalizing cross-encoder rerank scores within a reference set (`_relevance_scores` in `search_pipeline.py`), not an absolute confidence measure — the cross-encoder's logits are uncalibrated, so the percentage reflects standing within whatever set it's normalized against, not real-world match quality.
  _Avoid_: confidence, relevance score (when the subject is this specific display value)
- **Organic result** — a results-view entry that would appear in the top-*k* under `global_best` ordering, independent of book. Shown with its Match %. See ADR-0008.
  _Avoid_: genuine result, real match
- **Guarantee filler** — a results-view entry present only because `round_robin`'s book-representation policy forced its book to contribute a slot; would not appear under `global_best`. Shown with a book-attribution badge ("Included for `<Book>`") instead of a Match %, since its rank-normalized score would misrepresent relevance. See ADR-0008.
  _Avoid_: bucket-winner, weak bucket-winner (imprecise — doesn't distinguish from an organic result that happens to come from the same book)

## Deployment

- **Hosting target** — DigitalOcean App Platform (backend), Netlify (frontend), Qdrant Cloud (vector DB). See ADR-0003.
- **QDRANT_URL** — environment variable controlling the Qdrant connection in `SearchPipeline`. Must be set to the Qdrant Cloud cluster URL on deployment; defaults to `http://localhost:6333` for local dev.
- **QDRANT_API_KEY** — environment variable for Qdrant Cloud authentication. Set as an App Platform secret.
- **Nikaya payload index** — Qdrant Cloud requires an explicit keyword payload index on any field used in filters. Created idempotently at startup in `main.py`; without it, nikaya-filtered queries return 400 errors.
- **NVIDIA_API_KEY** — environment variable for LLM inference (Gemma 3n expansion + Llama 3.1 8B synthesis). Free tier, 40 rpm limit. Set as an App Platform secret.
- **SHARE_RECEIPT_SECRET** — server-side signing key for the shared-answer receipt (see ADR-0005). Wired into `/synthesize`, `/stream`, and `POST /share` as of 2026-07-04; still needs a production secret provisioned on App Platform (defaults to empty string, which the code accepts but is insecure — must be set before this feature can be trusted in production).
- **SUPABASE_URL / SUPABASE_KEY** — env vars for feedback storage. When set, `POST /feedback` writes to Supabase Postgres; otherwise falls back to local SQLite. Set as App Platform secrets in production.
- **SQLITE_DB_PATH** — path for the local-SQLite fallback (used only when `SUPABASE_URL`/`SUPABASE_KEY` are absent). Read fresh in `lifespan()` on each startup; defaults to the repo-root `feedback.db` when unset. Lets route tests point the app at a `tmp_path` file before `TestClient` triggers startup, instead of writing to the real repo-root file.
- **CORS_ORIGINS** — comma-separated list of allowed frontend origins. Set to the Netlify deployment URL on production. Already reads from env in `main.py`.
- **data/dumps/** — source JSON files committed to the repo. Loaded at startup by BM25Retriever, CitationOracle, and SuttaTitleIndex. Must be present on the server.
- **Qdrant collection** — 134,102 vectors, 384 dims, ~320MB RAM. Migrated once to Qdrant Cloud free tier via snapshot; not rebuilt on every deploy.

## Conventions

- **Book** — the retrieval/filter granularity: one of `DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP` (`_VALID_NIKAYAS` in `main.py`), derived from a chunk's ID prefix (`_bucket_of` in `search_pipeline.py`). Use this term for anything working at selection/bucket granularity — DHP and ITI are books, not nikāyas.
  _Avoid_: nikāya (when the subject is bucket-level filtering or selection)
- **Nikāya** — one of the four primary divisions of the Sutta Piṭaka (DN, MN, SN, AN), plus loosely the Khuddaka Nikāya collection. The code's `nikaya`-named params and fields (chunk ID prefix, the `nikayas` filter arg) actually operate at **book** granularity, not nikāya granularity — a legacy naming choice, not a modeling claim; when Vinaya is ingested the same field will carry book-like tags such as `VIN-BU`, `VIN-KD`.
- **Phase** — Phase 2 = Vinaya ingestion (deferred; parser regex needs extension for `pli-tv-*` IDs). Phase 3 = Aṭṭhakathā ingestion + commentary-link edges.

## Gap detection (implemented and scheduled)

- **Retrieval gap** — a query where the pipeline fails to surface a relevant sutta/passage. Signalled by a `down` row in the Supabase `feedback` table with category `Not relevant to my question` or `Missing important nuance` (the other three categories point at synthesis/guardrail problems, not retrieval). Historically fixed by hand via a new `pali_dictionary` entry (verbatim English hint bridging vocabulary the retriever/reranker doesn't recognize) — see commit 0ba8b6f.
- **Gap Detector** — scans `feedback` for new retrieval-gap candidates (`rating='down'`, qualifying category, `gap_issue_url IS NULL`), re-runs the query live through `SearchPipeline.search()` for diagnostic context (current top candidates), and files a `needs-triage` GitHub issue per candidate — capped per run, and deduped by checking for an existing open issue on the same query text first (comments instead of duplicating). Runs daily via the `.github/workflows/gap-detector.yml` scheduled workflow (`NVIDIA_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` / `SUPABASE_URL` / `SUPABASE_KEY` supplied as GitHub Actions repo secrets; issue creation authenticates via the workflow's default `GITHUB_TOKEN`).
- **gap_issue_url** — column to be added to the Supabase `feedback` table; nullable, set once a row has been turned into (or matched against) a GitHub issue so the Gap Detector doesn't reprocess it.
