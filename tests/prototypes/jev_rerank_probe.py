"""Throwaway probe: does a Jev (TypeSafe System One) reranker beat the current
cross-encoder on recall@10?

Answers wayfinder ticket "Would a Jev score rerank better than the
English-only cross-encoder?" (#200).
Not a pytest test: it makes paid network calls. Run it by hand.

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
      && PYTHONPATH=. python3 tests/prototypes/jev_rerank_probe.py

Runs the full 16-query benchmark twice against the same live retrieval:
  baseline  - unmodified pipeline (ms-marco-MiniLM-L-6-v2, plain query +
              pali_dictionary hint variants — search_pipeline.py:674)
  jev       - pipeline.reranker.rerank_multi swapped for JevReranker below

JevReranker uses only the plain query, no hint. #196 already tested Jev
against the pali_dictionary hint's whole reason for existing (bridging
vocabulary gaps like "one precept" -> "deliberate lie") and found Jev reads
that gap unaided — Noul beat Score there too, hence Noul here (see #196's
resolution comment on issue #196).
"""

import asyncio
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.backend.retrieval_benchmark import (  # noqa: E402
    BENCHMARK_CASES, _DUMPS_DIR, _matches, _sutta_of, _print_report,
)

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

# citation_support_check.py batches 2-5 citations per call; this probe scores
# up to _RERANK_CANDIDATE_BUDGET (60) chunks per query, so batch in groups
# rather than risk one oversized request the API has never seen from us.
_BATCH_SIZE = 20

RERANK_QUESTION_TEMPLATE = (
    "Does the passage in `chunks[{i}]` directly answer the user's `query`?"
)
RERANK_CRITERIA = {
    "true": "The passage states the answer the query is looking for.",
    "false": "The passage is merely on a related topic, or repeats similar "
             "wording without answering the query.",
}

usage_totals = {"input_tokens": 0, "output_tokens": 0, "requests": 0}


def load_key():
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key
    for parent in Path(__file__).resolve().parents:
        env_file = parent / ".env"
        if not env_file.is_file():
            continue
        for line in env_file.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "TYPESAFE_API_KEY":
                return value.strip().strip("'\"")
    sys.exit("TYPESAFE_API_KEY is not set and no .env above this file defines it.")


def _ask(state, questions):
    body = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {load_key()}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    usage = payload.get("usage", {})
    usage_totals["input_tokens"] += usage.get("input_tokens", 0)
    usage_totals["output_tokens"] += usage.get("output_tokens", 0)
    usage_totals["requests"] += 1
    return payload["answers"]


class JevReranker:
    """Drop-in replacement for Reranker.rerank_multi (search_pipeline.py),
    scoring each candidate with one Noul question instead of the
    cross-encoder. Same call shape: pipeline.search runs it inside the
    existing thread executor, so a blocking HTTP call here is safe.
    """

    def rerank_multi(self, queries: list[str], chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []
        query = queries[0]  # see module docstring: no hint variant
        texts = [c.get("english", "") for c in chunks]
        scores: list[float] = [0.0] * len(texts)
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start:start + _BATCH_SIZE]
            state = {"query": query, "chunks": [{"text": t} for t in batch]}
            questions = {
                f"p{i}": {
                    "type": "noul",
                    "instructions": RERANK_QUESTION_TEMPLATE.format(i=i),
                    "criteria": RERANK_CRITERIA,
                }
                for i in range(len(batch))
            }
            answers = _ask(state, questions)
            for i in range(len(batch)):
                scores[start + i] = answers[f"p{i}"]["noul"]
        order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
        return [{**chunks[i], "rerank_score": scores[i]} for i in order]


async def run_with_jev(top_k: int = 10) -> tuple[list[dict], float]:
    from backend.app.services.search_pipeline import SearchPipeline
    from backend.app.services.sutta_title_index import SuttaTitleIndex
    from backend.app.services.bm25_retriever import BM25Retriever

    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    pipeline = SearchPipeline(title_index=title_index, bm25_retriever=bm25_retriever)
    pipeline.reranker.rerank_multi = JevReranker().rerank_multi

    results = []
    started = time.monotonic()
    for query, expected_suttas, difficulty, note in BENCHMARK_CASES:
        chunks = await pipeline.search(query, top_k=top_k)
        retrieved_suttas = {_sutta_of(c["id"]) for c in chunks}
        hit = any(_matches(s, expected_suttas) for s in retrieved_suttas)
        results.append({
            "query": query,
            "expected": " | ".join(expected_suttas),
            "difficulty": difficulty,
            "note": note,
            "hit": hit,
            "best_score": chunks[0].get("rerank_score", 0.0) if chunks else 0.0,
            "variants": [],
        })
    wall = time.monotonic() - started
    return results, wall


def _summary(results: list[dict]) -> dict:
    by_diff: dict[str, list] = {"hard": [], "medium": [], "easy": []}
    for r in results:
        by_diff[r["difficulty"]].append(r)
    return {
        "total": f"{sum(r['hit'] for r in results)}/{len(results)}",
        **{d: f"{sum(r['hit'] for r in g)}/{len(g)}" for d, g in by_diff.items()},
    }


async def main():
    load_key()
    from tests.backend.retrieval_benchmark import run_benchmark

    print("Running baseline (current cross-encoder + pali_dictionary hint)...")
    t0 = time.monotonic()
    baseline = await run_benchmark(top_k=10, with_expansion=True)
    baseline_wall = time.monotonic() - t0
    _print_report(baseline, top_k=10, mode="baseline: cross-encoder")

    print("Running Jev reranker (Noul, plain query, no hint)...")
    jev, jev_wall = await run_with_jev(top_k=10)
    _print_report(jev, top_k=10, mode="jev: Noul, no hint")

    baseline_summary = _summary(baseline)
    jev_summary = _summary(jev)
    flips = [
        {"query": b["query"], "baseline_hit": b["hit"], "jev_hit": j["hit"]}
        for b, j in zip(baseline, jev) if b["hit"] != j["hit"]
    ]

    cost = usage_totals["input_tokens"] / 1_000_000 * 0.042
    print("=== head-to-head, same 16 queries, same retrieval, same day ===")
    print(f"baseline recall@10: {baseline_summary['total']}  ({baseline_wall:.1f}s wall)")
    print(f"jev      recall@10: {jev_summary['total']}  ({jev_wall:.1f}s wall)")
    print(f"per-difficulty  baseline={baseline_summary}  jev={jev_summary}")
    if flips:
        print("queries where the two disagreed:")
        for f in flips:
            print(f"  baseline={f['baseline_hit']!s:5}  jev={f['jev_hit']!s:5}  {f['query']}")
    else:
        print("no disagreements: identical hit/miss on all 16 queries")
    print(f"jev requests: {usage_totals['requests']}  "
          f"input tokens: {usage_totals['input_tokens']}  "
          f"estimated cost: ${cost:.5f}")

    out = Path(__file__).with_suffix(".results.json")
    out.write_text(json.dumps({
        "baseline": baseline, "jev": jev,
        "baseline_summary": baseline_summary, "jev_summary": jev_summary,
        "flips": flips, "usage": dict(usage_totals),
        "baseline_wall_seconds": baseline_wall, "jev_wall_seconds": jev_wall,
    }, indent=2, ensure_ascii=False))
    print(f"raw results written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
