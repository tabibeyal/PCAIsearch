# Expansion Recall Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the expansion pipeline recall gap (26% → ≥47%) by replacing first-seen dense dedup with multi-list RRF and shipping a Pāḷi-term-rich expansion prompt v2.

**Architecture:** Two independent fixes applied in sequence. Fix 1 adds `rrf_fuse_multi` to `fusion.py` and wires it into `search_pipeline.py` replacing the first-seen dedup loop. Fix 2 adds `ExpansionPrompt` v2 with a strict two-line contract (English passage vocabulary + Pāḷi term cluster) and switches the pipeline default.

**Tech Stack:** Python, rank_bm25, sentence-transformers CrossEncoder, Qdrant, pytest-asyncio, unittest.mock

---

## File Map

| File | Change |
|---|---|
| `backend/app/services/fusion.py` | Add `rrf_fuse_multi` function |
| `backend/app/services/search_pipeline.py` | Replace first-seen dedup with `rrf_fuse_multi`; add `ExpansionPrompt` v2; switch default to v2 |
| `tests/backend/test_fusion.py` | Add `rrf_fuse_multi` tests |
| `tests/backend/test_search_pipeline.py` | Add hierarchical RRF wiring test; add v2 prompt tests |
| `tests/backend/retrieval_benchmark.py` | Add `--log-variants` flag |

---

## Task 1: Add `rrf_fuse_multi` to fusion.py

**Files:**
- Modify: `backend/app/services/fusion.py`
- Test: `tests/backend/test_fusion.py`

- [ ] **Step 1: Write failing tests for `rrf_fuse_multi`**

Add to the bottom of `tests/backend/test_fusion.py`:

```python
from backend.app.services.fusion import rrf_fuse, rrf_fuse_multi


LIST_A = [
    {"id": "A", "english": "alpha"},
    {"id": "B", "english": "beta"},
    {"id": "C", "english": "gamma"},
]
LIST_B = [
    {"id": "B", "english": "beta"},
    {"id": "D", "english": "delta"},
]
LIST_C = [
    {"id": "A", "english": "alpha"},
    {"id": "E", "english": "epsilon"},
]


def test_rrf_fuse_multi_output_is_list_of_dicts():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    assert isinstance(result, list)
    assert all(isinstance(x, dict) for x in result)


def test_rrf_fuse_multi_fusion_score_field_present():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    assert all("fusion_score" in x for x in result)


def test_rrf_fuse_multi_all_ids_present():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    ids = {x["id"] for x in result}
    assert ids == {"A", "B", "C", "D"}


def test_rrf_fuse_multi_item_in_both_lists_scores_higher_than_item_in_one():
    result = rrf_fuse_multi([LIST_A, LIST_B])
    scores = {x["id"]: x["fusion_score"] for x in result}
    # B appears in both LIST_A (rank 1) and LIST_B (rank 0) — should beat C (only LIST_A rank 2)
    assert scores["B"] > scores["C"]


def test_rrf_fuse_multi_later_list_item_not_penalised_vs_first_seen():
    """An item only in the second list at rank 0 should beat an item in the first list at rank 2."""
    result = rrf_fuse_multi([LIST_A, LIST_B])
    scores = {x["id"]: x["fusion_score"] for x in result}
    # D is rank 0 in LIST_B; C is rank 2 in LIST_A
    # D score = 1/61; C score = 1/63  →  D > C
    assert scores["D"] > scores["C"]


def test_rrf_fuse_multi_sorted_descending():
    result = rrf_fuse_multi([LIST_A, LIST_B, LIST_C])
    scores = [x["fusion_score"] for x in result]
    assert scores == sorted(scores, reverse=True)


def test_rrf_fuse_multi_three_lists_accumulates_correctly():
    # A is rank 0 in LIST_A and rank 0 in LIST_C → score = 1/61 + 1/61 = 2/61
    result = rrf_fuse_multi([LIST_A, LIST_B, LIST_C])
    scores = {x["id"]: x["fusion_score"] for x in result}
    expected_a = 1 / 61 + 1 / 61  # rank 0 in LIST_A, rank 0 in LIST_C
    assert abs(scores["A"] - expected_a) < 1e-9


def test_rrf_fuse_multi_single_list_matches_one_side_of_rrf_fuse():
    result_multi = rrf_fuse_multi([LIST_A])
    result_rrf = rrf_fuse(LIST_A, [])
    scores_multi = {x["id"]: x["fusion_score"] for x in result_multi}
    scores_rrf = {x["id"]: x["fusion_score"] for x in result_rrf}
    assert scores_multi == scores_rrf


def test_rrf_fuse_multi_empty_lists():
    assert rrf_fuse_multi([]) == []
    assert rrf_fuse_multi([[]]) == []
    assert rrf_fuse_multi([[], []]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_fusion.py -k "multi" -v
```

Expected: ImportError or NameError — `rrf_fuse_multi` does not exist yet.

- [ ] **Step 3: Implement `rrf_fuse_multi` in fusion.py**

Add after the existing `rrf_fuse` function in `backend/app/services/fusion.py`:

```python
def rrf_fuse_multi(
    lists: List[List[Dict[str, Any]]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Reciprocal Rank Fusion over N ranked result lists keyed by 'id'."""
    scores: Dict[str, float] = {}
    sources: Dict[str, Dict[str, Any]] = {}

    for lst in lists:
        for rank, item in enumerate(lst):
            item_id = item["id"]
            if item_id is None:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
            if item_id not in sources:
                sources[item_id] = item

    return [
        {**sources[item_id], "fusion_score": score}
        for item_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_fusion.py -v
```

Expected: all fusion tests pass (existing 11 + new 9 = 20 total).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fusion.py tests/backend/test_fusion.py
git commit -m "feat: add rrf_fuse_multi for multi-list reciprocal rank fusion"
```

---

## Task 2: Wire hierarchical RRF into search_pipeline.py

**Files:**
- Modify: `backend/app/services/search_pipeline.py`
- Test: `tests/backend/test_search_pipeline.py`

- [ ] **Step 1: Write failing test**

Add to `tests/backend/test_search_pipeline.py`:

```python
@pytest.mark.asyncio
async def test_dense_results_use_rrf_fuse_multi_not_first_seen():
    """Pipeline must call rrf_fuse_multi on per-query dense results, not first-seen dedup."""
    from unittest.mock import patch as _patch
    chunks = [{"id": "MN 10:1", "pali": "", "english": "mindfulness body"}]
    pipeline, _ = await _make_pipeline_with_client(chunks)
    pipeline.expand_query = AsyncMock(return_value=["query one", "query two"])

    with _patch("backend.app.services.search_pipeline.rrf_fuse_multi") as mock_multi:
        mock_multi.return_value = []
        await pipeline.search("mindfulness", top_k=5)

    mock_multi.assert_called_once()
    call_arg = mock_multi.call_args[0][0]
    assert isinstance(call_arg, list), "rrf_fuse_multi must receive a list of lists"
    assert len(call_arg) == 2, f"Expected 2 per-query result lists, got {len(call_arg)}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py::test_dense_results_use_rrf_fuse_multi_not_first_seen -v
```

Expected: FAIL — `rrf_fuse_multi` is not imported or called in `search_pipeline.py`.

- [ ] **Step 3: Update the import in search_pipeline.py**

In `backend/app/services/search_pipeline.py`, change the fusion import line from:

```python
from backend.app.services.fusion import rrf_fuse
```

to:

```python
from backend.app.services.fusion import rrf_fuse, rrf_fuse_multi
```

- [ ] **Step 4: Replace first-seen dedup with hierarchical RRF in search_pipeline.py**

In `backend/app/services/search_pipeline.py`, find the `search` method. Replace this block:

```python
        seen_ids: set = set()
        dense_deduped: List[Dict[str, Any]] = []
        for batch in per_query:
            for result in batch:
                if result["id"] not in seen_ids:
                    seen_ids.add(result["id"])
                    dense_deduped.append(result)

        if self.bm25_retriever:
            seen_bm25: dict = {}
            for q in queries:
                for item in self.bm25_retriever.retrieve(q, retrieval_k, nikayas):
                    item_id = item["id"]
                    if item_id not in seen_bm25 or item["bm25_score"] > seen_bm25[item_id]["bm25_score"]:
                        seen_bm25[item_id] = item
            bm25_results = sorted(seen_bm25.values(), key=lambda x: x["bm25_score"], reverse=True)
            all_results = rrf_fuse(dense_deduped, bm25_results)
        else:
            all_results = dense_deduped
```

With:

```python
        dense_fused = rrf_fuse_multi(list(per_query))

        if self.bm25_retriever:
            seen_bm25: dict = {}
            for q in queries:
                for item in self.bm25_retriever.retrieve(q, retrieval_k, nikayas):
                    item_id = item["id"]
                    if item_id not in seen_bm25 or item["bm25_score"] > seen_bm25[item_id]["bm25_score"]:
                        seen_bm25[item_id] = item
            bm25_results = sorted(seen_bm25.values(), key=lambda x: x["bm25_score"], reverse=True)
            all_results = rrf_fuse(dense_fused, bm25_results)
        else:
            all_results = dense_fused
```

- [ ] **Step 5: Run all pipeline tests**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py -v
```

Expected: all 6 existing tests + 1 new test pass (7 total).

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

Expected: 101 passed, same 6 pre-existing errors in test_api.py (missing NVIDIA_API_KEY).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_search_pipeline.py
git commit -m "fix: replace first-seen dense dedup with rrf_fuse_multi for proper ranking"
```

---

## Task 3: Add ExpansionPrompt v2 and switch pipeline default

**Files:**
- Modify: `backend/app/services/search_pipeline.py`
- Test: `tests/backend/test_search_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/backend/test_search_pipeline.py`:

```python
from backend.app.services.search_pipeline import ExpansionPrompt


def test_expansion_prompt_v2_exists():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_expansion_prompt_v2_has_two_line_structure():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Line 1" in prompt
    assert "Line 2" in prompt


def test_expansion_prompt_v2_mentions_pali_terms():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "Pali" in prompt or "Pāli" in prompt or "Pāḷi" in prompt


def test_expansion_prompt_v2_forbids_sutta_numbers():
    prompt = ExpansionPrompt("v2").get_prompt()
    assert "sutta number" in prompt.lower() or "sutta numbers" in prompt.lower()


def test_search_pipeline_default_uses_v2():
    with patch("backend.app.services.search_pipeline.AsyncOpenAI"):
        pipeline = SearchPipeline()
    assert pipeline.expansion_prompt.version == "v2"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py -k "v2" -v
```

Expected: FAIL — `"v2"` key missing from `ExpansionPrompt.VERSIONS`; default is still `"v1"`.

- [ ] **Step 3: Add v2 to ExpansionPrompt.VERSIONS in search_pipeline.py**

In `backend/app/services/search_pipeline.py`, find the `VERSIONS` dict in `ExpansionPrompt` and add the `"v2"` entry:

```python
    VERSIONS = {
        "v1": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output 2 keyword-focused search strings that will improve retrieval. "
            "Rules: (1) include relevant Pali terms (e.g. musavada, anicca, dukkha, sila, samadhi); "
            "(2) include concrete English keywords that would appear in the passage itself, not in the question; "
            "(3) do NOT output sutta names or sutta numbers. "
            "Output one string per line, no numbering, no explanation."
        ),
        "v2": (
            "You are a search query expander for a Pali Canon database. "
            "Given a user query, output exactly 2 search strings on separate lines.\n"
            "Line 1 — English passage vocabulary: concrete words likely to appear verbatim in a sutta "
            "verse. Do NOT rephrase the question. Think: what exact words would a monk say in this passage?\n"
            "Line 2 — Pali doctrinal term cluster: the canonical Pali terminology for the concept, "
            "space-separated and transliterated (e.g. avijja sankharā viññāna paticca-samuppāda). "
            "Proper names of communities or persons are allowed (e.g. kālāmā). "
            "Do NOT include sutta numbers.\n"
            "Output exactly two lines, no numbering, no explanation. "
            "The two lines must be maximally distinct from each other and from the original query."
        ),
    }
```

- [ ] **Step 4: Switch the default from v1 to v2 in SearchPipeline.__init__**

In `backend/app/services/search_pipeline.py`, in `SearchPipeline.__init__`, change:

```python
        self.expansion_prompt = expansion_prompt or ExpansionPrompt()
```

to:

```python
        self.expansion_prompt = expansion_prompt or ExpansionPrompt("v2")
```

- [ ] **Step 5: Run v2 tests**

```bash
PYTHONPATH=. python -m pytest tests/backend/test_search_pipeline.py -k "v2" -v
```

Expected: all 5 new tests pass.

- [ ] **Step 6: Run full test suite**

```bash
PYTHONPATH=. python -m pytest tests/backend/ -q --ignore=tests/backend/test_e2e_pipeline.py
```

Expected: 106 passed, same 6 pre-existing errors in test_api.py.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_search_pipeline.py
git commit -m "feat: add ExpansionPrompt v2 with structured Pali term cluster line, switch pipeline default"
```

---

## Task 4: Add --log-variants flag to retrieval benchmark

**Files:**
- Modify: `tests/backend/retrieval_benchmark.py`

- [ ] **Step 1: Add `log_variants` parameter to `run_benchmark`**

In `tests/backend/retrieval_benchmark.py`, change the `run_benchmark` signature from:

```python
async def run_benchmark(top_k: int = 10, with_expansion: bool = False, with_bm25: bool = False, no_rerank: bool = False) -> list[dict]:
```

to:

```python
async def run_benchmark(top_k: int = 10, with_expansion: bool = False, with_bm25: bool = False, no_rerank: bool = False, log_variants: bool = False) -> list[dict]:
```

- [ ] **Step 2: Capture variants when `log_variants=True`**

In `run_benchmark`, inside the `if with_expansion:` block, after the pipeline is constructed and before the results loop, add the variant capture setup:

```python
    if with_expansion:
        from backend.app.services.search_pipeline import SearchPipeline
        from backend.app.services.sutta_title_index import SuttaTitleIndex
        title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
        pipeline = SearchPipeline(title_index=title_index)
        if no_rerank:
            pipeline.reranker.rerank = lambda query, chunks: chunks

        _variant_sink: list[list[str]] = [[]]
        if log_variants:
            _orig_expand = pipeline.expand_query
            async def _expand_and_capture(query):
                variants = await _orig_expand(query)
                _variant_sink[0] = list(variants)
                return variants
            pipeline.expand_query = _expand_and_capture

        async def retrieve(query):
            _variant_sink[0] = []
            chunks = await pipeline.search(query, top_k=top_k)
            return chunks, list(_variant_sink[0])
```

- [ ] **Step 3: Update the results loop to capture variants**

In `run_benchmark`, change the results loop from:

```python
    results = []
    for query, expected_suttas, difficulty, note in BENCHMARK_CASES:
        chunks = await retrieve(query)
        retrieved_suttas = {_sutta_of(c["id"]) for c in chunks}
        hit = any(_matches(s, expected_suttas) for s in retrieved_suttas)
        best_score = chunks[0].get("score") or chunks[0].get("fusion_score") or 0.0 if chunks else 0.0
        results.append({
            "query": query,
            "expected": " | ".join(expected_suttas),
            "difficulty": difficulty,
            "note": note,
            "hit": hit,
            "best_score": best_score,
        })
```

to:

```python
    results = []
    for query, expected_suttas, difficulty, note in BENCHMARK_CASES:
        raw = await retrieve(query)
        if with_expansion and log_variants:
            chunks, variants = raw
        else:
            chunks, variants = raw, []
        retrieved_suttas = {_sutta_of(c["id"]) for c in chunks}
        hit = any(_matches(s, expected_suttas) for s in retrieved_suttas)
        best_score = chunks[0].get("score") or chunks[0].get("fusion_score") or 0.0 if chunks else 0.0
        results.append({
            "query": query,
            "expected": " | ".join(expected_suttas),
            "difficulty": difficulty,
            "note": note,
            "hit": hit,
            "best_score": best_score,
            "variants": variants,
        })
```

**Note:** For the non-expansion branches, `retrieve(query)` returns `chunks` directly (not a tuple). Update those branches to also return a tuple for consistency:

In the `elif with_bm25:` block, change:
```python
        async def retrieve(query):
            dense = await retriever.retrieve(query, retrieval_k)
            sparse = bm25_retriever.retrieve(query, retrieval_k)
            return rrf_fuse(dense, sparse)[:top_k]
```
to:
```python
        async def retrieve(query):
            dense = await retriever.retrieve(query, retrieval_k)
            sparse = bm25_retriever.retrieve(query, retrieval_k)
            return rrf_fuse(dense, sparse)[:top_k], []
```

In the `else:` block, change:
```python
        async def retrieve(query):
            return await retriever.retrieve(query, top_k=top_k)
```
to:
```python
        async def retrieve(query):
            return await retriever.retrieve(query, top_k=top_k), []
```

And update the expansion retrieve function from Task 4 Step 2 to return `(chunks, variants)` in both log_variants=True and log_variants=False cases:
```python
        async def retrieve(query):
            _variant_sink[0] = []
            chunks = await pipeline.search(query, top_k=top_k)
            return chunks, list(_variant_sink[0])
```

- [ ] **Step 4: Update `_print_report` to display variants**

In `_print_report`, after the per-result print line, add variant display:

```python
    for diff in ("hard", "medium", "easy"):
        for r in by_diff[diff]:
            mark = "✓" if r["hit"] else "✗"
            q = r["query"][:W]
            print(f"  {q:<{W}} {r['expected']:<22} {r['difficulty']:<8} {mark}     {r['best_score']:.3f}")
            if r.get("variants"):
                for i, v in enumerate(r["variants"]):
                    print(f"    variant {i}: {v}")
```

- [ ] **Step 5: Add `--log-variants` to the CLI parser**

In `_main()`, after the `--no-rerank` argument, add:

```python
    parser.add_argument("--log-variants", action="store_true",
                        help="print generated query variants per case (only with --with-expansion)")
```

And pass it through:

```python
    results = await run_benchmark(top_k=args.k, with_expansion=args.with_expansion, with_bm25=args.with_bm25, no_rerank=args.no_rerank, log_variants=args.log_variants)
```

Also update the mode string logic:

```python
    if args.with_expansion and args.no_rerank:
        mode = "with LLM expansion, no rerank"
    elif args.with_expansion:
        mode = "with LLM expansion"
    elif args.with_bm25:
        mode = "vector + BM25 + RRF, no expansion"
    else:
        mode = "raw vector, no expansion"
```

(This block is unchanged — just leave it as-is.)

- [ ] **Step 6: Run non-expansion benchmark modes to verify no regressions**

```bash
PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --with-bm25
```

Expected: same output as before — 7/15 (46%). No errors.

- [ ] **Step 7: Commit**

```bash
git add tests/backend/retrieval_benchmark.py
git commit -m "feat: add --log-variants flag to retrieval benchmark for expansion query inspection"
```

---

## Task 5: Run expansion benchmark and verify recall

**Files:** None modified — this is a measurement step.

- [ ] **Step 1: Run full expansion benchmark with variant logging**

```bash
PYTHONPATH=. NVIDIA_API_KEY=<your-key> python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants
```

Expected output format:
```
  <query>                                              <expected>             <diff>   ✓/✗   <score>
    variant 0: <original query>
    variant 1: <english passage vocabulary>
    variant 2: <pali term cluster>
```

- [ ] **Step 2: Check overall recall**

Success criterion: overall recall@10 ≥ 47% (≥ 8/15).

If recall is < 47%, inspect the variant output for failing cases:
- Are line 2 variants actually generating Pāḷi terms, or is the LLM ignoring the prompt?
- Which cases regressed vs the BM25+dense baseline?

- [ ] **Step 3: If recall ≥ 47%, commit a benchmark result note to HANDOFF.md**

Update `HANDOFF.md` with the measured recall figures and observed variant quality.

```bash
git add HANDOFF.md
git commit -m "docs: record expansion recall benchmark results after hierarchical RRF + prompt v2"
```
