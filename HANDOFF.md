# Handoff — Session 2026-05-13 (Path A: SuttaTitleIndex body verses)

## What happened this session

Implemented Path A: extended `SuttaTitleIndex` to index English body text from verses 3–15 per sutta, not just the title verse (v2). This fixes the SN/AN title-extraction bug where v2 is a section header (e.g. "6. Involvement") rather than the actual sutta title.

---

## What was done

### Commit `d6c1f15` — `feat: split expansion/synthesis models + update HANDOFF`

(Carried forward from previous session — model split shipped and stable.)

### Commit `4befa46` — `feat: extend SuttaTitleIndex to include body verses 3-15 in BM25`

**Files changed:**
- `backend/app/services/sutta_title_index.py`
- `tests/backend/test_sutta_title_index.py`

**Changes in `sutta_title_index.py`:**

1. `__init__` — BM25 corpus now includes `body_text` field (optional, defaults to `""`):
   ```python
   corpus = [
       _tokenize(f"{e['title_pali']} {e['title_english']} {e.get('body_text', '')}")
       for e in entries
   ]
   ```

2. `from_directory` — collects English text from verses 3–15 as `body_text`:
   ```python
   body_text = " ".join(
       v.get("english", "")
       for v in verses
       if 3 <= v.get("number", 0) <= 15
   )
   ```

**Two new tests added** (`test_sutta_title_index.py`):
- `test_finds_sutta_by_body_text_when_not_in_title` — tracer bullet: body-text-only match works
- `test_from_directory_includes_body_verses_in_search` — end-to-end: `from_directory` picks up v3-v15 content

All 15 title-index / title-boost tests pass.

---

## SuttaTitleIndex (updated)

`backend/app/services/sutta_title_index.py`

BM25 index over all ~4456 suttas. Each document = `title_pali + title_english + body_text` where `body_text` = English text of verses 3–15.

**Why verses 3–15:**
- MN/DN: v2 = title, v3 = "So I have heard." (body starts at v4)
- SN/AN: v2 = section/chapter header, v3 = actual sutta title, v4+ = body

Including v3 in the index fixes SN/AN suttas whose real title was invisible (e.g. SN22.59 v2 = "6. Involvement", v3 = "The Characteristic of Not-Self").

Including v4–v15 catches thesis content not encoded in titles (e.g. SN56.11 v6–v8 = "these two extremes / self-indulgence / self-mortification" now matches "path between self-indulgence and harsh self-denial").

**Note:** `get_title_text()` still returns only v2 title text (used as extra retrieval query in pipeline). This is a remaining gap for SN/AN suttas — see open issues below.

---

## Model split (stable from previous session)

| Task | Env var | Default |
|------|---------|---------|
| Query expansion | `EXPANSION_MODEL` | `google/gemma-3n-e4b-it` |
| Synthesis | `LLM_MODEL` | `meta/llama-3.3-70b-instruct` |

---

## BM25 title boost spot-check (current session)

Against the real 4456-sutta index, querying `SuttaTitleIndex.search(query, top_n=3)`:

| Query | Expected | Top-3 | Hit |
|---|---|---|---|
| what is the path between self-indulgence… | SN56.11 | SN56.11, SN35.85, SN35.142 | ✓ |
| what are the four foundations of mindfulness | MN10 | AN4.154, AN5.15, SN48.8 | ✗ |
| components of noble eightfold path | MN117 | SN45.33, SN45.20, SN45.162 | ✗ |
| five aggregates permanent or lack a self | SN22.59 | SN22.123, SN22.122, SN18.10 | ✗ |
| how does ignorance cause suffering step by step | SN12.1 | AN6.87, AN6.86, AN5.151 | ✗ |

Body text helps SN56.11 (thesis vocab in v6–v8). Does not fix easy-tier 0/5 — see diagnosis below.

---

## Easy-tier diagnosis (current understanding)

Easy tier is 0/5 in BM25 lookup for all benchmark queries. Root causes:

1. **Chapter density beats canonical suttas**: "four foundations of mindfulness" → SN47.x and AN4.x (short, dense, purpose-built chapter suttas) outscore MN10 (long, broad). BM25 scores by term frequency — short suttas win on density.

2. **`get_title_text()` returns v2 for SN/AN**: even when BM25 correctly finds SN22.59 via body text, the pipeline injects "6. Involvement" as the extra retrieval query (v2 title), not "The Characteristic of Not-Self" (v3). The retrieval gain is lost.

---

## Open issues / next steps

### Fix `get_title_text()` for SN/AN suttas (quick win)

For SN/AN the actual sutta title is in v3, not v2. `get_title_text()` should return v3 if v2 looks like a section header (number + dot pattern: `"6. Involvement"`), or simply return v2 + v3.

Estimated impact: fixes cases where BM25 finds the right sutta but the pipeline injects the wrong retrieval query.

### Easy tier: 0/5 (deep fix needed)

The BM25 title boost is not sufficient for easy-tier improvement. The vector search itself is missing these suttas at recall@10. Two options:

**A — Wider retrieval_k** (already tried; 46% at k=30 vs 26% at k=10)

**B — Full-corpus BM25 hybrid**

Add a sparse BM25 pass over all 134k verses, RRF-fuse with dense results before reranking. Qdrant supports sparse vectors natively. This is the most direct fix for vocabulary-mismatch failures across all tiers.

### MN 21, SN 45.2 (hard tier)

Still missing at recall@10. Vocabulary-mismatch cases the current expansion doesn't reliably bridge.

### SN 56.11 ×2, SN 12.1, AN 3.65 (medium tier)

Non-deterministic: depends on whether Gemma generates the right Pali term on a given run.

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — vector retrieval against Qdrant; injectable seam (`Retriever`)
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks expanded candidate pool before returning `top_k`
- **SuttaTitleIndex** — BM25 over sutta titles + body verses 3–15; injectable seam; loaded from `data/dumps/` at startup
- **ExpansionPrompt** — versioned prompt class; injectable in `SearchPipeline`; currently v1 only
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`citation_oracle.py`)
- **SuttaRelations** — answers "what is related to sutta X?" (`sutta_relations.py`)
- **Registry** — `Dict[str, Set[int]]` sutta ID → verse numbers, loaded from local dumps
- **retrieval_k** — internal candidate pool size = `max(top_k * 3, 30)`; decoupled from `top_k`
- **expansion_model** — model used for `expand_query`; separate from `llm_model` (synthesis)
