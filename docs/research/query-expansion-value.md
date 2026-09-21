# Does query expansion earn its place, now that it can run again?

Research for [Does query expansion earn its place, now that it can run again?](https://github.com/tabibeyal/PCAIsearch/issues/214), a ticket of map [Put Jev to work in PCAIsearch](https://github.com/tabibeyal/PCAIsearch/issues/194).

Builds on [Local EXPANSION_MODEL falls back to a retired NVIDIA model, breaking expansion silently](https://github.com/tabibeyal/PCAIsearch/issues/211) and [Query expansion cannot run on any model left on this NVIDIA account](https://github.com/tabibeyal/PCAIsearch/issues/212), which found that query expansion — and, separately, answer synthesis — had been silently doing nothing since August 2026, because every model those two settings pointed at answers `410 Gone` or `404 model_not_found` on this account.

## Terms used in this report

- **Recall@10** — of the top 10 retrieved passages, does the expected sutta appear anywhere among them? The project's headline retrieval-quality number.
- **Expansion** — the query-expansion step: before searching, an LLM call rewrites the user's question into several alternate phrasings (the "variants"), using a 53-entry prompt table. Each variant is searched and the results are merged.
- **`--with-bm25`** — the benchmark's no-expansion baseline: the user's question, unrewritten, run through dense (vector) search and BM25 (keyword search) together, fused into one ranked list. No LLM call, no API key needed.
- **`--with-expansion`** — the benchmark's full-pipeline mode: expansion runs, every variant is searched (dense + BM25 fused), all those results are merged again across variants, and the cross-encoder reranker sorts the merged list. Requires `GROQ_API_KEY`.

## Summary findings

1. **Expansion is worth +32 points of recall@10: 12/16 (75%) with it, against 7/16 (43%) without**, same 16-query gold set, same retrieval index, same day (2026-09-21). This is a real gap, not noise from a broken model — both runs completed with zero `query expansion failed` lines in the `--with-expansion` log.
2. **This settles the map's open Fog question of whether expansion earns its keep: it does.** The 53-entry expansion table is vindicated in aggregate.
3. **Caveat — the gap is not isolated to expansion alone.** `--with-expansion` also runs the cross-encoder reranker; `--with-bm25` never reranks (there is no `--with-bm25 --no-rerank` distinction to make, since `--with-bm25` skips the reranker unconditionally). So the 32-point gap is really "expansion + multi-variant fusion + reranking" against "single-query fusion, no reranking" — not expansion in isolation. A clean isolation would compare `--with-expansion --no-rerank` against `--with-bm25`; that run has not been done.
4. **Per [ADR-0011](https://github.com/tabibeyal/PCAIsearch/blob/master/docs/adr/0011-remove-passages-only-search-policies.md)'s convention, these are recorded as a new baseline, not a delta.** The only prior comparison (2026-05-16: 26% with expansion, 46% without) was measured while expansion was silently broken — a bug report, not a verdict, and not a fair comparison point.
5. **These numbers came from [PR #215](https://github.com/tabibeyal/PCAIsearch/pull/215)'s own acceptance test**, not a fresh run performed for this ticket. At the time of writing, this machine had multiple Claude Code sessions running and swap already full — the same memory-pressure pattern that has previously frozen this machine during a `--with-expansion` benchmark run (see `project_dev_server_freeze_diagnosis` / the full-suite-guard history). Re-running the benchmark myself under those conditions risked losing the session rather than adding information, since #215's numbers already are the "modern pair" this ticket asks for. If independent reproduction is wanted later, the exact commands are in [Numbers](#numbers) below.
6. **The unrelated coincidence worth flagging for #117:** the with-expansion number, 12/16 (75%), happens to numerically match the regressed figure #117 was opened against in July 2026. This is almost certainly a coincidence, not confirmation — the model (Groq's `qwen/qwen3.8-27b` vs NVIDIA Llama), the retrieval config, and possibly the index have all changed since then — but it means #117 should not be closed as "resolved" on the strength of this number matching a healthy-looking 75%. See [Implications](#implications) below.

## Numbers

| Mode | Command | Recall@10 |
| --- | --- | --- |
| With expansion (Groq `qwen/qwen3.8-27b`, full pipeline: expansion → dense+BM25 fusion per variant → rerank) | `PYTHONPATH=. GROQ_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion --log-variants` | **12/16 (75%)** |
| Without expansion (single query, dense + BM25 fusion, no rerank) | `PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --with-bm25` | **7/16 (43%)** |

- **Run date:** 2026-09-21.
- **Commit:** `bad7fb6`, tip of branch `worktree-groq-213` — the code [PR #215](https://github.com/tabibeyal/PCAIsearch/pull/215) opened, resolving [#213](https://github.com/tabibeyal/PCAIsearch/issues/213). **Not yet merged to `master`** as of this writing; `master`'s `search_pipeline.py` still reads `NVIDIA_API_KEY`, a dead credential, and cannot run `--with-expansion` at all.
- Both runs used the same 16-query gold set in `tests/backend/retrieval_benchmark.py` and the same production Qdrant Cloud index.

## Implications

**For [#117](https://github.com/tabibeyal/PCAIsearch/issues/117) (recall@10 regression, 100% June → 75% July):** the June 100% figure is not a fair comparison point for today's stack — different model, different retrieval config, and (per ADR-0011's own precedent) baselines are recorded fresh rather than chased as deltas across migrations. Recommend re-baselining #117 against 75% (this ticket's number) rather than continuing to track a gap against June's figure. Whether #117 counts as "resolved" or "superseded" is Eyal's call, not this ticket's — flagging the numeric coincidence with the old regressed figure (finding 6, above) so whoever makes that call sees it.

**For [#200](https://github.com/tabibeyal/PCAIsearch/issues/200) (Jev-vs-cross-encoder rerank, tied 11/16):** that comparison ran while expansion was silently dead in both arms, so its 11/16-vs-11/16 tie is not trustworthy — neither arm actually got the benefit (or cost) of real expansion. Now that expansion runs, #200 is unblocked for a fresh re-run; this ticket does not re-run it, since that comparison is #200's job and a separate ~4-second-per-query, multi-run measurement.

## What's still open

Whether every one of the 53 expansion table entries pulls its weight, or some exist only to typo-fix the first line, is untested by this result — the 12/16 number is an aggregate. That is a new, sharper question than the one this ticket answered, not a restatement of it.

## Sources

- **[PR #215](https://github.com/tabibeyal/PCAIsearch/pull/215)** — "Point expansion and synthesis at Groq, and warn at startup when a model is retired (#213)" — acceptance section, commit `bad7fb6`.
- **Repo file:** `tests/backend/retrieval_benchmark.py` (benchmark modes, gold set, the `--with-bm25` "not directly comparable" note already in its own source comment).
- **[ADR-0011](https://github.com/tabibeyal/PCAIsearch/blob/master/docs/adr/0011-remove-passages-only-search-policies.md)** — baseline-recording convention followed here.
- **Prior tickets:** [#211](https://github.com/tabibeyal/PCAIsearch/issues/211), [#212](https://github.com/tabibeyal/PCAIsearch/issues/212), [#213](https://github.com/tabibeyal/PCAIsearch/issues/213) — how expansion came to be silently dead, and how it was fixed.
