"""Fair follow-up to jev_rerank_probe.py: is Jev's reranker actually faster,
or was the first measurement just an artifact of run order?

jev_rerank_probe.py ran the cross-encoder first, then Jev, in the same
process — so the cross-encoder paid the one-time cost of loading its ~400MB
model into memory, and Jev's run got to reuse that already-warm process for
free (shared retrieval infra: embedding model, BM25 index). That understates
the cross-encoder's real per-query speed.

This script isolates each variant in its own OS process, and inside that
process runs one untimed warm-up search before the timed 16-query loop — so
neither variant's number includes model-loading time, and neither benefits
from the other having already paid it. Two separate invocations:

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
      && PYTHONPATH=. python3 tests/prototypes/jev_rerank_timing.py --variant baseline
      && PYTHONPATH=. python3 tests/prototypes/jev_rerank_timing.py --variant jev

Each run appends its numbers to jev_rerank_timing.results.json under its own
key, so run both (either order) and then read the file for the comparison.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.backend.retrieval_benchmark import BENCHMARK_CASES, _DUMPS_DIR  # noqa: E402
from tests.prototypes.jev_rerank_probe import JevReranker, load_key, usage_totals  # noqa: E402

# Deliberately not one of BENCHMARK_CASES — this result is thrown away, only
# used to force every model into memory before the timer starts.
_WARMUP_QUERY = "what is mindfulness"


async def _build_pipeline(variant: str):
    from backend.app.services.search_pipeline import SearchPipeline
    from backend.app.services.sutta_title_index import SuttaTitleIndex
    from backend.app.services.bm25_retriever import BM25Retriever

    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    pipeline = SearchPipeline(title_index=title_index, bm25_retriever=bm25_retriever)
    if variant == "jev":
        load_key()
        pipeline.reranker.rerank_multi = JevReranker().rerank_multi
    return pipeline


async def run(variant: str, top_k: int = 10) -> dict:
    pipeline = await _build_pipeline(variant)

    warmup_started = time.monotonic()
    await pipeline.search(_WARMUP_QUERY, top_k=top_k)
    warmup_seconds = time.monotonic() - warmup_started
    print(f"[{variant}] warm-up search (untimed against the real result): "
          f"{warmup_seconds:.1f}s")

    started = time.monotonic()
    for query, *_ in BENCHMARK_CASES:
        await pipeline.search(query, top_k=top_k)
    wall = time.monotonic() - started

    return {
        "variant": variant,
        "warmup_seconds": warmup_seconds,
        "queries": len(BENCHMARK_CASES),
        "wall_seconds": wall,
        "seconds_per_query": wall / len(BENCHMARK_CASES),
        "usage": dict(usage_totals) if variant == "jev" else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["baseline", "jev"], required=True)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()

    result = asyncio.run(run(args.variant, top_k=args.k))
    print(f"[{args.variant}] timed run: {result['wall_seconds']:.1f}s for "
          f"{result['queries']} queries "
          f"({result['seconds_per_query']:.2f}s/query)")

    out = Path(__file__).with_suffix(".results.json")
    data = json.loads(out.read_text()) if out.exists() else {}
    data[args.variant] = result
    out.write_text(json.dumps(data, indent=2))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
