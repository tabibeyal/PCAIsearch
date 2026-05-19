# PCAIsearch — Domain Context

Vocabulary used in the codebase. Update inline as terms are resolved.

## Corpus

- **Sutta Piṭaka** — currently the only ingested division of the Pāḷi Canon. ~4,691 suttas across DN, MN, SN, AN, Dhp, Iti. Source: SuttaCentral `bilara-data` (Mahāsaṅgīti edition for Pāḷi root; Sujato for English).
- **Vinaya Piṭaka** — not yet ingested. Planned but deferred behind the philological-cross-reference work.
- **Aṭṭhakathā** — Pāḷi commentaries. Not yet ingested. English coverage upstream is ~10–15%; Pāḷi and Thai coverage is much fuller. Phase-3 corpus.

## Retrieval pipeline (existing)

- **Pipeline** — RAG orchestrator: expand → retrieve (dense + BM25) → RRF fusion → rerank → synthesize (`backend/app/services/search_pipeline.py`). Recall@10: 93% on 15-query benchmark.
- **Retriever** — Qdrant vector retrieval over a single `pali_canon` collection. Injectable seam (`backend/app/services/retriever.py`).
- **BM25Retriever** — sparse keyword retrieval over English text. Fused with dense results via RRF (`backend/app/services/bm25_retriever.py`).
- **ExpansionPrompt** — versioned LLM prompts for query expansion; currently v6. Outputs English vocab line + Pāḷi terms line. Pāḷi terms are used for retrieval only — not passed to the reranker (`backend/app/services/search_pipeline.py`).
- **pali_dictionary** — keyword-matched lookup returning Pāḷi terms (`lookup`) and verbatim English passage hints (`lookup_english`). The English hints are appended as a 5th search variant and also used as the second reranking query (`backend/app/services/pali_dictionary.py`).
- **Reranker** — cross-encoder (`ms-marco-MiniLM-L-6-v2`). `rerank_multi` scores each candidate against multiple queries and takes the max; currently called with `[original_query, english_hint]`. Pāḷi terms are excluded — the model is English-only (`backend/app/services/search_pipeline.py`).
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`backend/app/services/citation_oracle.py`).
- **SuttaRelations** — hand-curated doctrinal pairs + ±2 numeric adjacency within a nikāya. Surfaces a "see also" sutta list per query (`backend/app/services/sutta_relations.py`).
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15. Boosts retrieval when the query matches a canonical title (`backend/app/services/sutta_title_index.py`).
- **Chunk ID** — verse-level identifier in the form `"<nikāya> <number>:<verse>"`, e.g. `"MN 27:14"`. Used end-to-end (Qdrant payload, citations, related-suttas API).

## Philological cross-referencing (in design)

The current goal. Parallel passage detection is being built first; word clustering and commentary-link features will follow.

- **Parallel passage** — a recurring sequence of Pāḷi tokens shared verbatim (after light normalisation) across two or more places in the canon. The mnemonic stock-formulas of oral Pāḷi tradition (jhāna formula, hindrances, dependent origination, *anussati* list, etc.).
- **Span** — the first-class node of the parallel-passage graph. A *maximal* recurring sequence of normalised Pāḷi tokens. Identified by content hash (12 hex chars of the normalised text). Sub-sequences of a span are not stored as separate spans.
- **Occurrence** — one appearance of a span in the corpus. Tuple of `(span_id, sutta_id, verse_number, char_offset, char_length)`. Char offsets index into the *raw* (un-normalised) `pali` field of the verse, so the original text is reconstructible.
- **Light normalisation** — the canonicalisation applied before span detection: Unicode NFC, lower-case, strip punctuation, collapse whitespace, canonicalise niggahita (ṁ/ṃ → one form). Deterministic, no lemmatisation, no sandhi-splitting, no stop-word removal. Used only for matching; raw text is preserved separately.
- **Detector** — the offline batch tool that produces the parallel-passage graph from `data/dumps/*.json`. Versioned (e.g. `v1-k7-light`); each build of the artifact records the version it was produced under, so algorithm changes do not silently corrupt downstream queries.
- **Shingle** — a window of *k* consecutive normalised tokens, hashed. Used by the detector to seed matches before extending to maximal spans. Fixed at *k* = 7 tokens.
- **Parallel-passage artifact** — the output of a detector run. A SQLite file `data/parallels.sqlite` with `span` and `occurrence` tables. Regenerable; gitignored.

## Deployment

- **Hosting target** — Fly.io (backend), Vercel (frontend), Qdrant Cloud (vector DB). See ADR-0003.
- **QDRANT_URL** — environment variable controlling the Qdrant connection in `SearchPipeline`. Must be set to the Qdrant Cloud cluster URL on deployment; defaults to `http://localhost:6333` for local dev.
- **NVIDIA_API_KEY** — environment variable for LLM inference (Gemma 3n expansion + Llama 3.3 synthesis). Free tier, 40 rpm limit. Set as a secret in Fly.io and Vercel environments.
- **CORS_ORIGINS** — comma-separated list of allowed frontend origins. Set to the Vercel deployment URL on production. Already reads from env in `main.py`.
- **data/dumps/** — 38MB of source JSON (4,691 files) committed to the repo. Loaded at startup by BM25Retriever, CitationOracle, and SuttaTitleIndex. Gitignored locally but must be present on the server.
- **Qdrant collection** — 134,102 vectors, 384 dims, ~320MB RAM. Migrated once to Qdrant Cloud free tier via snapshot; not rebuilt on every deploy.

## Conventions

- **Nikāya** — used loosely throughout the code as the prefix tag in chunk IDs (`DN`, `MN`, `SN`, `AN`, `KN`). Strictly speaking applies only to the Sutta Piṭaka; when Vinaya is ingested the same field will carry tags like `VIN-BU`, `VIN-KD`, which is a slight abuse of the term but preserves a single payload field.
- **Phase** — Phase 1 = parallel-passage detection on Sutta-only. Phase 2 = Vinaya ingestion + re-run detector across Sutta+Vinaya. Phase 3 = Aṭṭhakathā ingestion + commentary-link edges. Word-clustering is interleaved when the term-dictionary work happens.
