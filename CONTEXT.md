# PCAIsearch — Domain Context

Vocabulary used in the codebase. Update inline as terms are resolved.

## Corpus

- **Sutta Piṭaka** — currently the only ingested division of the Pāḷi Canon. ~4,691 suttas across DN, MN, SN, AN, Dhp, Iti. Source: SuttaCentral `bilara-data` (Mahāsaṅgīti edition for Pāḷi root; Sujato for English).
- **Vinaya Piṭaka** — not yet ingested. Planned but deferred behind the philological-cross-reference work.
- **Aṭṭhakathā** — Pāḷi commentaries. Not yet ingested. English coverage upstream is ~10–15%; Pāḷi and Thai coverage is much fuller. Phase-3 corpus.

## Retrieval pipeline (existing)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`backend/app/services/search_pipeline.py`).
- **Retriever** — Qdrant vector retrieval over a single `pali_canon` collection. Injectable seam (`backend/app/services/retriever.py`).
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

## Conventions

- **Nikāya** — used loosely throughout the code as the prefix tag in chunk IDs (`DN`, `MN`, `SN`, `AN`, `KN`). Strictly speaking applies only to the Sutta Piṭaka; when Vinaya is ingested the same field will carry tags like `VIN-BU`, `VIN-KD`, which is a slight abuse of the term but preserves a single payload field.
- **Phase** — Phase 1 = parallel-passage detection on Sutta-only. Phase 2 = Vinaya ingestion + re-run detector across Sutta+Vinaya. Phase 3 = Aṭṭhakathā ingestion + commentary-link edges. Word-clustering is interleaved when the term-dictionary work happens.
