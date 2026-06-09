# Spec: Answer Depth and Citation Diversity

**Date:** 2026-06-09
**Status:** Approved

## Problem

Broad conceptual queries (e.g. "meditation") produce short answers with only 2–3 citations, all from a single nikāya. The Pali Canon covers meditation across all five nikāyas; a 2-citation SN-only answer is not useful.

**Root cause:** `max_tokens=700` (~500 words) truncates the answer before the LLM can produce a full structured response. The system prompt also has no minimum citation count or nikāya diversity requirement, so the LLM stops early.

The round-robin interleave in the retrieval layer already ensures diverse nikāya coverage in the retrieved chunks — retrieval is not the problem.

## Goals

- Conceptual queries produce a structured breakdown with 6–8+ cited bullet points.
- Answers draw from at least 3 nikāyas when the context contains passages from multiple nikāyas.
- Narrow factual queries (how many, yes/no) are unaffected.

## Non-goals

- Retry/validate-and-regenerate loop (too expensive latency-wise).
- Per-query nikāya detection or dynamic prompt switching.
- Changes to the reranker or retrieval pipeline.

## Changes

### 1. Raise `max_tokens`: 700 → 1200

In `search_pipeline.py`, both `synthesize` and `stream_synthesize` use `max_tokens=700`. Raise to 1200.

Rationale: 6–8 cited bullet points (1–2 sentences each) plus intro and closing paragraphs needs ~900–1000 tokens. 1200 gives headroom without pushing Llama 8B into meandering output.

### 2. Raise default `top_k`: 10 → 15

In `main.py`, the `/stream` endpoint defaults `top_k=10`. Raise to 15.

Rationale: more passages fed into synthesis means more material to draw from. The existing round-robin interleave already distributes these across nikāyas, so no retrieval code changes are needed.

### 3. Add minimum depth and diversity to system prompt

In `_SYSTEM_PROMPT` in `search_pipeline.py`, extend the conceptual question format section with two additions:

**Minimum bullet count:**
> For conceptual questions, write at least 6 cited bullet points — not fewer. If the context supports more, include them.

**Nikāya diversity:**
> When the provided context includes passages from more than one nikāya, your bullet points must draw from at least 3 different nikāyas.

### Existing limits (unchanged)

- Max 3 citations per bracket — stays.
- Max 5 sentences per paragraph — stays.
- No total citation upper limit (not needed; per-bracket cap handles density).

## Files to change

| File | Change |
|------|--------|
| `backend/app/services/search_pipeline.py` | `max_tokens` 700 → 1200 in both `synthesize` and `stream_synthesize`; extend `_SYSTEM_PROMPT` conceptual section |
| `backend/app/main.py` | `top_k` default 10 → 15 on `/stream` endpoint |

## Success criteria

- A "meditation" query produces a structured answer with at least 6 cited bullet points drawing from at least 3 nikāyas.
- A "how many precepts are there?" query is unaffected (factual path, no bullets required).
- Latency increase stays under 5 seconds on average (Llama 8B at 1200 tokens vs 700).
