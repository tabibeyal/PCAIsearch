# Answer Depth and Citation Diversity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make conceptual queries return structured answers with at least 6 cited bullet points drawn from at least 3 different nikāyas.

**Architecture:** Three small changes — raise the token ceiling so the LLM has room to write full answers, raise the default context window so more passages are available, and add explicit minimum rules to the system prompt for conceptual questions.

**Tech Stack:** Python, FastAPI, NVIDIA-hosted Llama 3.1-8B via OpenAI-compatible API.

---

## File Map

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | `max_tokens` 700 → 1200 in `synthesize` and `stream_synthesize`; add minimum bullet + nikāya diversity rules to `_SYSTEM_PROMPT` |
| `backend/app/main.py` | `top_k` default 10 → 15 on `/stream` endpoint |
| `tests/backend/test_synthesize.py` | Add test for max_tokens value |
| `tests/backend/test_api.py` | Add test for /stream default top_k |

---

## Task 1: Enforce max_tokens=1200 in synthesis

**Files:**
- Modify: `backend/app/services/search_pipeline.py` (lines ~642 and ~651)
- Test: `tests/backend/test_synthesize.py`

- [ ] **Step 1: Write the failing test**

Add to the bottom of `tests/backend/test_synthesize.py`:

```python
@pytest.mark.asyncio
async def test_synthesize_uses_1200_max_tokens(pipeline, sample_context):
    mock_client = _mock_llm(pipeline, "Answer")

    await pipeline.synthesize("query", sample_context)

    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["max_tokens"] == 1200
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_synthesize.py::test_synthesize_uses_1200_max_tokens -v
```

Expected: FAIL — `AssertionError: assert 700 == 1200`

- [ ] **Step 3: Raise max_tokens in both synthesis methods**

In `backend/app/services/search_pipeline.py`, find these two calls (both currently read `max_tokens=700`) and change both to `max_tokens=1200`:

```python
# synthesize method (~line 642):
message = await self.llm.chat.completions.create(
    model=self.llm_model,
    max_tokens=1200,
    timeout=120.0,
    messages=_build_messages(query, context_chunks),
)

# stream_synthesize method (~line 651):
stream = await self.llm.chat.completions.create(
    model=self.llm_model,
    max_tokens=1200,
    timeout=120.0,
    stream=True,
    messages=_build_messages(query, context_chunks),
)
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_synthesize.py::test_synthesize_uses_1200_max_tokens -v
```

Expected: PASS

- [ ] **Step 5: Run the full test file to check for regressions**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_synthesize.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_synthesize.py
git commit -m "feat: raise synthesis max_tokens from 700 to 1200"
```

---

## Task 2: Raise /stream default top_k from 10 to 15

**Files:**
- Modify: `backend/app/main.py` (line ~215)
- Test: `tests/backend/test_api.py`

- [ ] **Step 1: Write the failing test**

Add to the bottom of `tests/backend/test_api.py`:

```python
def test_stream_default_top_k_is_15(client):
    captured = {}

    async def fake_search(query, top_k=10, nikayas=None):
        captured["top_k"] = top_k
        return []

    async def fake_stream(query, chunks):
        yield {"type": "done", "text": "", "hallucinations": [], "canonical_misses": [], "is_faithful": True}

    with patch.object(app.state.pipeline, "search", side_effect=fake_search), \
         patch.object(app.state.pipeline, "stream_synthesize", side_effect=fake_stream), \
         patch.object(app.state.guardrail, "process_response", return_value={
             "text": "", "hallucinations": [], "canonical_misses": [], "is_faithful": True
         }):
        client.get("/stream?q=meditation")

    assert captured.get("top_k") == 15
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_api.py::test_stream_default_top_k_is_15 -v
```

Expected: FAIL — `AssertionError: assert 10 == 15`

- [ ] **Step 3: Change the default in main.py**

In `backend/app/main.py`, find the `/stream` endpoint's `top_k` parameter (currently `default=10`) and change it to `default=15`:

```python
top_k: int = Query(default=15, ge=1, le=20, description="Number of context chunks to retrieve"),
```

Only change this line inside the `stream` function — the `/search` and `/synthesize` endpoints keep their own defaults unchanged.

- [ ] **Step 4: Run test to confirm it passes**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_api.py::test_stream_default_top_k_is_15 -v
```

Expected: PASS

- [ ] **Step 5: Run the full test file to check for regressions**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_api.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py tests/backend/test_api.py
git commit -m "feat: raise /stream default top_k from 10 to 15"
```

---

## Task 3: Add minimum bullet count and nikāya diversity to system prompt

**Files:**
- Modify: `backend/app/services/search_pipeline.py` (inside `_SYSTEM_PROMPT`, ~line 338)
- Test: `tests/backend/test_synthesize.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/backend/test_synthesize.py`:

```python
def test_system_prompt_requires_minimum_bullet_points():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "at least 6 cited bullet points" in _SYSTEM_PROMPT


def test_system_prompt_requires_nikaya_diversity():
    from backend.app.services.search_pipeline import _SYSTEM_PROMPT
    assert "at least 3 different nikāyas" in _SYSTEM_PROMPT
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_synthesize.py::test_system_prompt_requires_minimum_bullet_points tests/backend/test_synthesize.py::test_system_prompt_requires_nikaya_diversity -v
```

Expected: both FAIL — `AssertionError`

- [ ] **Step 3: Extend the system prompt**

In `backend/app/services/search_pipeline.py`, find this line inside `_SYSTEM_PROMPT` (around line 338):

```python
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
```

Add the two new lines immediately after it:

```python
    "Each bullet should be a complete sentence or two — not a single word or embedded list.\n"
    "Write at least 6 cited bullet points — not fewer. If the context supports more, include them.\n"
    "When the context includes passages from more than one nikāya, draw from at least 3 different nikāyas.\n"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_synthesize.py::test_system_prompt_requires_minimum_bullet_points tests/backend/test_synthesize.py::test_system_prompt_requires_nikaya_diversity -v
```

Expected: both PASS

- [ ] **Step 5: Run the full test suite**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Expected: all PASS (or same number of pre-existing failures as before this change)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/search_pipeline.py tests/backend/test_synthesize.py
git commit -m "feat: require 6+ cited bullets and 3-nikāya diversity in conceptual answers"
```
