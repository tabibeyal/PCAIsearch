# PCAIsearch — Domain Context

Vocabulary used in the codebase. Update inline as terms are resolved.

## Corpus

- **Sutta Piṭaka** — currently the only ingested division of the Pāḷi Canon. Suttas across DN, MN, SN, AN, DHP, ITI, UD, STNP, THAG, THIG, KHP. Source: Thanissaro Bhikkhu's translations from the dhammatalks.org epub (`fetch_thanissaro.py`). English-only; Pāḷi body text is not included.
- **Vinaya Piṭaka** — not yet ingested. Planned but deferred behind the philological-cross-reference work.
- **Aṭṭhakathā** — Pāḷi commentaries. Not yet ingested. English coverage upstream is ~10–15%; Pāḷi and Thai coverage is much fuller. Phase-3 corpus.

## Retrieval pipeline (existing)

- **Pipeline** — RAG orchestrator: expand → retrieve (dense + BM25) → RRF fusion → rerank → synthesize (`backend/app/services/search_pipeline.py`). Recall@10: ~86–93% on 15-query benchmark (regression introduced 2026-06-03, fix committed 2026-06-04; awaiting re-benchmark).
- **Retriever** — Qdrant vector retrieval over a single `pali_canon` collection. Injectable seam (`backend/app/services/retriever.py`).
- **BM25Retriever** — sparse keyword retrieval over English text. Fused with dense results via RRF (`backend/app/services/bm25_retriever.py`).
- **ExpansionPrompt** — versioned LLM prompts for query expansion; currently v6. Outputs English vocab line + Pāḷi terms line. Pāḷi terms are used for retrieval only — not passed to the reranker (`backend/app/services/search_pipeline.py`).
- **pali_dictionary** — keyword-matched lookup returning Pāḷi terms (`lookup`) and verbatim English passage hints (`lookup_english`). The English hints are appended as a 5th search variant and also used as the second reranking query (`backend/app/services/pali_dictionary.py`). ~84 entries covering all major doctrinal lists with Thanissaro Bhikkhu's primary translations.
- **Reranker** — cross-encoder (`ms-marco-MiniLM-L-6-v2`). `rerank_multi` scores each candidate against multiple queries and takes the max; currently called with `[original_query, english_hint]`. Pāḷi terms are excluded — the model is English-only (`backend/app/services/search_pipeline.py`).
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`backend/app/services/citation_oracle.py`).
- **Feedback** — `POST /feedback` endpoint in `main.py`. Stores thumbs-up/down ratings with optional category + comment to Supabase Postgres in production (via `SUPABASE_URL` / `SUPABASE_KEY` env vars); falls back to local SQLite when those vars are absent. No admin UI; review via Supabase dashboard in production.
- **SuttaRelations** — hand-curated doctrinal pairs + ±2 numeric adjacency within a nikāya. Surfaces a "see also" sutta list per query (`backend/app/services/sutta_relations.py`).
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15. Boosts retrieval when the query matches a canonical title (`backend/app/services/sutta_title_index.py`).
- **Chunk ID** — verse-level identifier in the form `"<nikāya> <number>:<verse>"`, e.g. `"MN 27:14"`. Used end-to-end (Qdrant payload, citations, related-suttas API).

## Deployment

- **Hosting target** — DigitalOcean App Platform (backend), Netlify (frontend), Qdrant Cloud (vector DB). See ADR-0003.
- **QDRANT_URL** — environment variable controlling the Qdrant connection in `SearchPipeline`. Must be set to the Qdrant Cloud cluster URL on deployment; defaults to `http://localhost:6333` for local dev.
- **QDRANT_API_KEY** — environment variable for Qdrant Cloud authentication. Set as an App Platform secret.
- **Nikaya payload index** — Qdrant Cloud requires an explicit keyword payload index on any field used in filters. Created idempotently at startup in `main.py`; without it, nikaya-filtered queries return 400 errors.
- **NVIDIA_API_KEY** — environment variable for LLM inference (Gemma 3n expansion + Llama 3.1 8B synthesis). Free tier, 40 rpm limit. Set as an App Platform secret.
- **SUPABASE_URL / SUPABASE_KEY** — env vars for feedback storage. When set, `POST /feedback` writes to Supabase Postgres; otherwise falls back to local SQLite. Set as App Platform secrets in production.
- **CORS_ORIGINS** — comma-separated list of allowed frontend origins. Set to the Netlify deployment URL on production. Already reads from env in `main.py`.
- **data/dumps/** — source JSON files committed to the repo. Loaded at startup by BM25Retriever, CitationOracle, and SuttaTitleIndex. Must be present on the server.
- **Qdrant collection** — 134,102 vectors, 384 dims, ~320MB RAM. Migrated once to Qdrant Cloud free tier via snapshot; not rebuilt on every deploy.

## Conventions

- **Nikāya** — used loosely throughout the code as the prefix tag in chunk IDs (`DN`, `MN`, `SN`, `AN`, `KN`). Strictly speaking applies only to the Sutta Piṭaka; when Vinaya is ingested the same field will carry tags like `VIN-BU`, `VIN-KD`, which is a slight abuse of the term but preserves a single payload field.
- **Phase** — Phase 2 = Vinaya ingestion (deferred; parser regex needs extension for `pli-tv-*` IDs). Phase 3 = Aṭṭhakathā ingestion + commentary-link edges.

## Gap detection (implemented and scheduled)

- **Retrieval gap** — a query where the pipeline fails to surface a relevant sutta/passage. Signalled by a `down` row in the Supabase `feedback` table with category `Not relevant to my question` or `Missing important nuance` (the other three categories point at synthesis/guardrail problems, not retrieval). Historically fixed by hand via a new `pali_dictionary` entry (verbatim English hint bridging vocabulary the retriever/reranker doesn't recognize) — see commit 0ba8b6f.
- **Gap Detector** — scans `feedback` for new retrieval-gap candidates (`rating='down'`, qualifying category, `gap_issue_url IS NULL`), re-runs the query live through `SearchPipeline.search()` for diagnostic context (current top candidates), and files a `needs-triage` GitHub issue per candidate — capped per run, and deduped by checking for an existing open issue on the same query text first (comments instead of duplicating). Runs daily via the `.github/workflows/gap-detector.yml` scheduled workflow (`NVIDIA_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` / `SUPABASE_URL` / `SUPABASE_KEY` supplied as GitHub Actions repo secrets; issue creation authenticates via the workflow's default `GITHUB_TOKEN`).
- **gap_issue_url** — column to be added to the Supabase `feedback` table; nullable, set once a row has been turned into (or matched against) a GitHub issue so the Gap Detector doesn't reprocess it.
