# Handoff — Session 2026-05-13 (easy-tier specificity + model split)

## What happened this session

Attacked the easy-tier recall failure (0/5), shipped `SuttaTitleIndex` (BM25 over sutta titles), split expansion and synthesis into separate LLM models, and diagnosed two blocking issues that prevent the easy tier from improving.

---

## What was done

### Commit: `9898ff5` — `feat: add sutta title BM25 boost to improve easy-tier recall`

**Files changed / created:**
- `backend/app/services/sutta_title_index.py` (new)
- `backend/app/services/search_pipeline.py`
- `backend/app/main.py`
- `tests/backend/test_sutta_title_index.py` (new)
- `tests/backend/test_title_boost_integration.py` (new)

### Uncommitted changes (staged-but-not-committed, branch `master`)

- `backend/app/services/search_pipeline.py` — `expansion_model` param (Gemma for expand, Llama for synthesize)
- `tests/backend/test_query_expansion.py` — 2 tests asserting model routing
- `tests/backend/retrieval_benchmark.py` — benchmark now wires `SuttaTitleIndex.from_directory` when `--with-expansion`

---

## SuttaTitleIndex

`backend/app/services/sutta_title_index.py`

BM25 index (`rank_bm25.BM25Okapi`) over all 4691 sutta dump files. Each entry = verse 2 (the title verse) pali + english text. At query time, if the top BM25 hit scores > 0, its sutta's title text is appended as an extra retrieval query so the reranker sees its verses.

```python
# Construction (at app startup)
title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)

# Usage (inside SearchPipeline.search)
title_hits = self.title_index.search(query, top_n=1)
title_text = self.title_index.get_title_text(top_sutta_id)
queries = list(queries) + [title_text]   # extra retrieval query
```

Injected as optional seam: `SearchPipeline(title_index=title_index)`. No-op when `None`.

---

## Model split

Default models (both overridable via env):

| Task | Env var | Default |
|------|---------|---------|
| Query expansion | `EXPANSION_MODEL` | `google/gemma-3n-e4b-it` |
| Synthesis | `LLM_MODEL` | `meta/llama-3.3-70b-instruct` |

Llama 3.3-70b produces cleaner synthesis (better citation formatting, stays on-topic). Gemma is kept for expansion because it generates short keyword strings which is what the retrieval step needs.

Side-by-side synthesis test run this session: Llama stays on-topic and cites sources; Gemma wanders to unrelated passages. Verdict: Llama is better for synthesis, the split is correct.

---

## Benchmark results this session

```
Raw vector (no expansion):      4/15  (26%)   — unchanged baseline
With expansion + title boost:   4/15  (26%)   — no improvement yet
```

The 7/15 (46%) from the previous session was not reproduced. See diagnosis below.

---

## Blocking issues diagnosed this session

### Issue 1 — Benchmark non-reproducibility: Gemma expansion is unreliable

The previous session's 7/15 was likely a lucky run. Gemma 3n is too small for consistent Pali term generation:

- Generates Thai script: `kāmaภりたい ภวังคะ` — complete hallucination
- Repeats `musavada` (false speech) across unrelated queries
- Misses the correct Pali term for the query's topic (e.g. `kalyanamitta` should appear for the spiritual-friend query but doesn't reliably)

The benchmark is measuring a non-deterministic system. A single run is not a reliable signal.

**Implication**: any recall improvement we measure may wash out on re-run. Need either a deterministic retrieval augmentation or to average over multiple runs.

---

### Issue 2 — Title boost misfires for easy-tier queries

Root cause traced for `MN 10` ("what are the four foundations of mindfulness"):

```
BM25 title match → MN119 ("Mindfulness of the Body"), score 7.84
                   MN118 ("Mindfulness of Breathing"), score 7.20
                   NOT MN10 ("Mindfulness Meditation"), which scores lower

Reason: query token "foundations" does not appear in any sutta title.
MN10 title = "Satipaṭṭhānasutta Mindfulness Meditation" — no match on "foundations".
```

The title-only BM25 has too little text to distinguish definitional suttas from incidental mentions. The title text "Mindfulness Meditation" loses to "Mindfulness of the Body" because the latter shares more tokens with a generic mindfulness query.

---

## Remaining known issues

### Easy tier: 0/5 (unchanged)

The specificity problem is not yet fixed. Two paths forward:

**A — Extend `SuttaTitleIndex` with opening thesis verses (next recommended step)**

Currently `from_directory` indexes only verse 2 (the title). The thesis verse (typically verse 9–12) contains the sutta's defining statement. For MN 10, verse 9: *"the four kinds of mindfulness meditation are the path to convergence"* — the word `path` and `four` and `mindfulness` would correctly score MN 10 above MN 119/118 for the failing query.

Change: `SuttaTitleIndex.from_directory` should concatenate verses 2–15 per sutta (not just verse 2) as the BM25 document.

**B — Full-corpus BM25 hybrid (more powerful, more work)**

Add a sparse BM25 pass over all 134k verses, RRF-fuse with dense results before reranking. Qdrant supports sparse vectors natively. Addresses easy tier AND the medium/hard vocabulary-mismatch cases more broadly.

### MN 21 and SN 45.2 (hard tier)

Still missing at recall@10. Both are vocabulary-mismatch cases the current expansion doesn't reliably bridge.

### SN 56.11 (medium, ×2), SN 12.1 (medium), AN 3.65 (medium)

Expansion sometimes generates the right Pali terms (avijjā, paṭicca-samuppāda, kalyānamitta) but is non-deterministic. These would likely improve with path A or B above.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — vector retrieval against Qdrant; injectable seam (`Retriever`)
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks expanded candidate pool before returning `top_k`
- **SuttaTitleIndex** — BM25 over sutta titles (+ soon: thesis verses); injectable seam; loaded from `data/dumps/` at startup
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; currently v1 only
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`citation_oracle.py`)
- **SuttaRelations** — answers "what is related to sutta X?" (`sutta_relations.py`)
- **Registry** — `Dict[str, Set[int]]` sutta ID → verse numbers, loaded from local dumps
- **retrieval_k** — internal candidate pool size = `max(top_k * 3, 30)`; decoupled from `top_k`
- **expansion_model** — model used for `expand_query`; separate from `llm_model` (synthesis)
