# Handoff — Session 2026-05-12 (retrieval quality)

## What happened this session

Diagnosed a retrieval quality failure, ran an LLM Council to decide the fix strategy, built a 15-case retrieval benchmark, and shipped two pipeline changes that raised recall@10 from 26% → 46%.

---

## What was done

### Commit: `053c56a` — `perf: improve retrieval recall from 26% to 46% via wider candidate pool`

**Files changed:**
- `backend/app/services/search_pipeline.py`
- `tests/backend/retrieval_benchmark.py` (new)

---

### Root cause diagnosis

Query: *"what is the one precept you should never break"* returned a vague generic answer.

Confirmed via Qdrant inspection:
- MN 61:36 IS in the index ("when someone is not ashamed to tell a deliberate lie, there is no bad deed they would not do")
- Original query scores MN 61:36 at 0.44 — never enters `top_k=10` candidate pool
- Near-verbatim passage language scores 0.78 — model CAN retrieve it
- Root cause: semantic gap between user vocabulary and canonical passage language

---

### Fix 1 — Expansion prompt revised (`search_pipeline.py:71`)

Old prompt: generate "alternative phrasings, synonyms, Pali terms" → produced user-query paraphrases.

New prompt: generate keyword-focused strings with Pali doctrinal terms and passage-proximate English keywords; explicitly bans sutta name/number output (Gemma hallucinates wrong sutta names when asked for passage fragments).

Investigation path: tried HyDE framing (passage-fragment generation) → Gemma 3n too small, hallucinated wrong suttas. Tried Llama 3.1 8B → same problem. Settled on keyword+Pali-term approach which is within small-model capability.

---

### Fix 2 — Decouple retrieval_k from top_k (`search_pipeline.py:130`)

```python
# Before
per_query = await asyncio.gather(*[self.retriever.retrieve(q, top_k, nikayas) for q in queries])

# After
retrieval_k = max(top_k * 3, 30)
per_query = await asyncio.gather(*[self.retriever.retrieve(q, retrieval_k, nikayas) for q in queries])
```

MN 61:36 sits at rank 21 for the original query. Old pipeline only retrieved top 10 per query → MN 61 never entered the reranker pool. Now retrieves 30 candidates per query (3× top_k), reranker sees rank-21 passages and promotes them. Final output still top_k.

---

### Retrieval benchmark (`tests/backend/retrieval_benchmark.py`)

15 labeled cases across three difficulty tiers:

| Tier | Characteristic | Cases |
|---|---|---|
| Hard | Large semantic gap, user/canon vocabulary diverge | MN 61, DN 16, MN 87, MN 21, SN 45.2 |
| Medium | Partial vocabulary overlap | SN 56.11 ×2, MN 118, SN 12.1, AN 3.65 |
| Easy | Vocabulary close but canonical sutta buried by generic mentions | MN 10, MN 117, DN 31, SN 22.59, MN 26 |

Run modes:
```bash
# Raw vector retrieval only (no API key needed, ~15s)
PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py

# Full pipeline with LLM expansion
PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion
```

**Baseline (raw vector, no expansion):** recall@10 = 4/15 (26%), recall@20 = 6/15 (40%)
**After fix (with expansion):** recall@10 = 7/15 (46%)

---

## Remaining known issues

### Easy tier: 0/5 at recall@10 and recall@20

Queries like "what are the four foundations of mindfulness" (→ MN 10) return high-scoring generic mindfulness content from many suttas instead of the canonical source sutta. The problem is **specificity**, not semantic gap. The embedding model finds high-confidence mentions scattered across 134k verses rather than identifying the definitional sutta.

Possible fixes (not yet attempted):
- BM25 hybrid search (council option B) — would help when query terms appear in the right sutta's title or key passages
- Domain-adapted embedding model trained on Buddhist texts
- Sutta-level metadata filtering (nikaya + sutta-title index)

### MN 21 and SN 12.1 still missing at recall@10

MN 21 ("saw parable") — query phrasing doesn't match passage language well enough even with wider retrieval.
SN 12.1 (dependent origination) — similar vocabulary mismatch.

### `_EXPANSION_PROMPT` not testable in isolation

Module-level constant. Would need `PromptBuilder` abstraction if prompt variants need unit testing (not currently a blocker).

---

## Architecture vocabulary (cumulative)

- **Pipeline** — RAG orchestrator: expand → retrieve → rerank → synthesize (`SearchPipeline`)
- **Retriever** — vector retrieval against Qdrant; injectable seam (`Retriever`)
- **Reranker** — CrossEncoder (`ms-marco-MiniLM-L-6-v2`) reranks expanded candidate pool before returning top_k
- **Guardrail** — post-generation citation verifier/redactor (`CitationGuardrail`)
- **CitationOracle** — answers "does `[ID:Verse]` exist?" (`citation_oracle.py`)
- **SuttaRelations** — answers "what is related to sutta X?" (`sutta_relations.py`)
- **Registry** — `Dict[str, Set[int]]` sutta ID → verse numbers, loaded from local dumps
- **retrieval_k** — internal candidate pool size = `max(top_k * 3, 30)`; decoupled from `top_k` to give reranker wider input
