# Handoff — Session 2026-05-15 (Pāḷi parallel-passage detector)

## What happened this session

Built the Phase 1 philological cross-referencing feature: an offline parallel-passage detector over the full Sutta corpus.

**Commits this session:**
- `729b55b` — `feat: add Pāḷi parallel-passage detector (Phase 1)`
- `e351ded` — `docs: update README with parallel-passage detector`
- `bc1865c` — `docs: add CLI quick-reference COMMANDS.md for parallels tool`

---

## What was built

### `analysis/parallels/` — new top-level package

| File | Purpose |
|------|---------|
| `normalise.py` | Light Pāḷi normalisation: NFC, lower-case, strip punctuation, collapse whitespace, ṁ→ṃ |
| `tokenise.py` | Per-sutta tokenisation; returns `(tokens, offsets)` where each offset is `(verse_number, char_offset_in_raw_pali)` |
| `schema.py` | `open_db()` + `create_tables()`; WAL mode, foreign keys on |
| `detector.py` | k-shingle (default k=7) seed + maximal left/right extension; content-addressed span IDs (SHA-256 → 12 hex); `DETECTOR_VERSION = "v1-k7-light"` |
| `reconstruct.py` | `reconstruct_raw(sutta_data, verse_number, char_offset, char_length)` → raw Pāḷi slice |
| `queries.py` | `list_spans`, `show_span`, `spans_in_sutta`, `top_formulas`, `stats` |
| `cli.py` | argparse wrapper; every command supports `--json` |
| `__main__.py` | Entry point for `python3 -m analysis.parallels` |
| `COMMANDS.md` | CLI quick-reference |

### `tests/analysis/` — 38 new tests

`test_normalise.py`, `test_tokenise.py`, `test_detector.py`, `test_reconstruct.py`, `test_queries.py`

### `docs/adr/`

- `0001-philological-cross-referencing-as-goal.md` — philological features first; corpus expansion (Vinaya, Aṭṭhakathā) is downstream
- `0002-parallel-passage-design.md` — span node, per-sutta tokenisation, light normalisation only

### `CONTEXT.md`

Domain vocabulary: corpus phases, retrieval pipeline terms, philological cross-referencing terms (span, occurrence, shingle, detector, light normalisation).

---

## Full-corpus build results

```
Suttas:      4,691
Spans:       31,711
Occurrences: 153,119
Artifact:    data/parallels.sqlite (18 MB, gitignored)
Build time:  ~20 seconds
Version:     v1-k7-light
```

Notable formulas found:
- `vivicceva kāmehi…paṭhamaṃ jhānaṃ upasampajja` — 93 occurrences (1st jhāna formula)
- `khīṇā jāti vusitaṃ brahmacariyaṃ…` — 188 occurrences (knowledge-of-destruction)
- `yena bhagavā tenupasaṅkami…` — 340 occurrences (visitor-approaches formula)

---

## SQLite schema

```sql
span(id TEXT PK, normalised_pali TEXT, token_count INT, occurrence_count INT, detector_version TEXT)
occurrence(id INT PK, span_id TEXT FK, sutta_id TEXT, verse_number INT, char_offset INT, char_length INT)
```

`span.id` = first 12 hex chars of SHA-256 of `normalised_pali`. Content-addressed: same formula gets the same ID across corpus rebuilds.

---

## CLI (package installed)

```bash
python3 -m analysis.parallels build
python3 -m analysis.parallels top-formulas --limit 20
python3 -m analysis.parallels spans-in-sutta MN36
python3 -m analysis.parallels show-span <span_id>
python3 -m analysis.parallels stats
```

See `analysis/parallels/COMMANDS.md` for full reference.

---

## Design decisions (locked)

All three are ADR'd. Changing any requires rebuilding the artifact and updating downstream consumers.

1. **Span node** (not verse-pair, not sutta-pair) — exact recurring text as first-class entity; verse/sutta views are trivial `GROUP BY`s over it.
2. **Per-sutta tokenisation** — Bilara segments are fine-grained; long formulas (jhāna, paticcasamuppāda) span multiple segments; per-verse tokenisation would fragment them.
3. **Light normalisation only** — catches exact oral-tradition repetition without importing morphological analyser error rate; heavier fuzzy matching is a future "Pass 2" edge type.

---

## Open issues / next steps

### Phase 1.5 — Pāḷi word clusters

Inverted index: doctrinal term → all occurrences. Fits same `analysis/` directory and SQLite file (new tables). Can reuse the normalised token stream already produced by the detector.

### Phase 2 — Vinaya ingestion (re-planned)

Deferred. When scheduled: re-plan from scratch under the philological lens (Brahmali footnotes as structural signal). Existing parser regex `r"([a-zA-Z]+)([\d.]+)"` won't match Vinaya IDs like `pli-tv-bu-vb-pj1` — needs extension.

### Phase 2.5 — Public read-only API + explorer UI

`/parallels` route in frontend backed by 4–5 read-only endpoints over `data/parallels.sqlite`. Schema already shaped for this; ~20 LOC HTTP layer.

### Full-corpus BM25 hybrid (retrieval, from previous session)

Add sparse BM25 pass over all 134k verses, RRF-fuse with dense results before reranking. Most direct fix for vocabulary-mismatch failures.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — vector retrieval against Qdrant; injectable seam (`Retriever`)
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks expanded candidate pool
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15; `get_title_text()` returns v3 for SN/AN chapter-header suttas
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; currently v1 only
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?"
- **SuttaRelations** — answers "what is related to sutta X?"
- **Span** — maximal recurring Pāḷi token sequence; content-addressed by SHA-256 of normalised text
- **Occurrence** — `(span_id, sutta_id, verse_number, char_offset, char_length)`; char offsets index raw pali field
- **Detector** — offline batch tool producing `data/parallels.sqlite`; versioned (`v1-k7-light`)
- **Light normalisation** — NFC + lower + strip punctuation + collapse whitespace + ṁ→ṃ
- **Shingle** — k=7 consecutive normalised tokens; used to seed span detection
- **retrieval_k** — internal candidate pool = `max(top_k * 3, 30)`
- **expansion_model** — model for `expand_query`; separate from `llm_model` (synthesis)
