# Handoff: Pre-existing Test Failures (2026-05-26)

## Status

**Resolved.** All 3 failures fixed in the same session they were documented.

---

## What failed and why

### 1 & 2 — `test_reranking.py::test_search_calls_reranker` and `test_search_result_order_follows_reranker`

**Root cause:** Tests mocked `p.reranker.rerank` (single-query method), but `search()` calls `p.reranker.rerank_multi` (multi-query method). The mocked `.rerank` was never called; the pipeline received a raw `MagicMock` from `.rerank_multi`.

**Fix:** Updated both tests to mock `rerank_multi` instead of `rerank`. The assertion on `call_args.args[0]` now checks that the original query is present in the list of queries passed.

### 3 — `test_synthesize.py::test_synthesize_includes_all_context_ids_in_message`

**Root cause:** The `sample_context` fixture had `"Right Mindfulness"` (2 words) as the English text for MN 10:5. `_build_messages()` in `search_pipeline.py` silently filters out any context chunk whose English text is shorter than 4 words — so MN 10:5 was dropped before the user message was built, and the test's `assert "MN 10:5" in user_text` failed.

**Fix:** Expanded the fixture's English text to `"Right mindfulness is awareness of the present moment"` (≥4 words), matching the filter's contract.

---

## Invariant to keep in mind

`_build_messages()` (`search_pipeline.py:351`) applies a **4-word minimum filter** on context chunks. Any test that asserts a specific chunk appears in the synthesized prompt must ensure that chunk's English text has at least 4 words.
