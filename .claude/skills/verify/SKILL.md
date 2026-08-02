---
name: verify
description: Build, launch and drive the PCAIsearch backend to observe a change at its real surface (HTTP). Use when verifying backend/RAG changes at runtime rather than via tests.
---

# Verifying PCAIsearch at runtime

The surface is the **backend HTTP API**. Drive it with `curl`; do not
import the pipeline and call it directly.

## Launch

```bash
set -a && source .env && set +a && PYTHONPATH=. \
  uvicorn backend.app.main:app --port 8123 --host 127.0.0.1 > uvicorn.log 2>&1
```

Run it backgrounded on a **non-default port** (8123+) so it never collides
with a dev server the user already has on 8000.

`.env` supplies `NVIDIA_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `LLM_MODEL`,
`SHARE_RECEIPT_SECRET`. Without them startup succeeds but every query 500s.

**Memory gotcha:** startup calls `pipeline.warmup()`, which loads the ONNX
embedding model and the PyTorch cross-encoder (~1.6 GB) on a 7.6 GB machine.
Check `free -m` first — under ~2 GB available, close Firefox before launching
or the box swaps to a halt. Only one server at a time.

Startup takes 1–3 min. Wait on health, don't sleep blindly:

```bash
until curl -s -m 2 http://127.0.0.1:8123/health | grep -q ok; do sleep 2; done
```

## Drive

```bash
curl -s -G http://127.0.0.1:8123/synthesize --data-urlencode "q=<question>" | jq -r .answer
```

- `/synthesize` — blocking JSON answer. The one to use for verification.
- `/stream` — same pipeline as SSE; use only when verifying streaming itself.
- Both are rate-limited to 10/minute and take **25–30 s** per query
  (retrieval + rerank + 8B synthesis). Use `-m 180`. Budget ~30 s per probe.

## Flows worth driving

- **Retrieval/ranking change** — ask a question whose expected sutta you know,
  check the citation IDs in the answer.
- **Prompt change** — run the same query against the PR and against
  `git checkout origin/master -- backend/app/services/search_pipeline.py`
  on a second launch. An 8B model's output is noisy; a single post-change
  sample proves nothing without the baseline beside it. Restore with
  `git checkout HEAD -- <file>` afterwards.
- **Any prompt change** — also re-probe the *other* instructions in
  `_SYSTEM_PROMPT`, which is long and easily displaced: out-of-scope
  (`q=what is 17 times 23?` must return the one-line refusal), the
  3-citations-per-bracket limit, and the bullet format.

## Gotcha: query echo

The synthesis model mirrors the querent's wording. When probing whether a
prompt rule changes the model's *word choice*, phrase the query in the
wording the rule forbids — a query that already uses the desired term
proves nothing.
