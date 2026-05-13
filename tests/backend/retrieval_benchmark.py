"""
Retrieval benchmark for PCAIsearch.

Measures recall@k: does the expected sutta appear anywhere in the top-k results?

Run standalone:
    PYTHONPATH=. python tests/backend/retrieval_benchmark.py
    PYTHONPATH=. python tests/backend/retrieval_benchmark.py --k 20

    # With LLM expansion (requires NVIDIA_API_KEY):
    PYTHONPATH=. NVIDIA_API_KEY=... python tests/backend/retrieval_benchmark.py --with-expansion

Raw mode (default) tests vector retrieval only — no API key needed, fast.
Expansion mode tests the full pipeline including query expansion.
"""

import asyncio
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from qdrant_client.async_qdrant_client import AsyncQdrantClient

from backend.app.core.indexing import EmbeddingManager
from backend.app.services.retriever import Retriever

COLLECTION = "pali_canon"

# Each case: (query, expected_sutta_prefix, difficulty, note)
# A result counts as a hit if any retrieved chunk ID starts with expected_sutta.
BENCHMARK_CASES = [
    # --- Hard: large semantic gap between user vocabulary and canonical language ---
    (
        "what is the one precept you should never break",
        "MN 61",
        "hard",
        "MN 61:36 — 'not ashamed to lie → no bad deed they would not do'",
    ),
    (
        "what were the Buddha's last words before he died",
        "DN 16",
        "hard",
        "DN 16:1433 — 'Conditions fall apart. Persist with diligence.'",
    ),
    (
        "why does loving someone lead to grief and suffering",
        "MN 87",
        "hard",
        "MN 87:66 — 'our loved ones are a source of sorrow'",
    ),
    (
        "should a monk feel anger even if attacked with a saw",
        "MN 21",
        "hard",
        "MN 21:215 — even sawed limb from limb, show no malevolence",
    ),
    (
        "is having a good spiritual friend the whole of the holy life",
        "SN 45.2",
        "hard",
        "SN 45.2:7-22 — 'half the spiritual life' → Buddha says it is the whole",
    ),
    # --- Medium: vocabulary partially overlaps with canonical text ---
    (
        "what is the path between self-indulgence and harsh self-denial",
        "SN 56.11",
        "medium",
        "SN 56.11 — the middle way and the noble eightfold path",
    ),
    (
        "what is the deepest origin of all suffering",
        "SN 56.11",
        "medium",
        "SN 56.11 — second noble truth: craving as the origin of suffering",
    ),
    (
        "how should one breathe mindfully during sitting meditation",
        "MN 118",
        "medium",
        "MN 118 — Ānāpānasati Sutta, full mindfulness of breathing instructions",
    ),
    (
        "how does ignorance cause suffering step by step",
        "SN 12.1",
        "medium",
        "SN 12.1 — dependent origination chain from ignorance to suffering",
    ),
    (
        "how do you know whether a religious teaching is worth following",
        "AN 3.65",
        "medium",
        "AN 3.65 — Kālāma Sutta: don't believe by tradition alone, test by experience",
    ),
    # --- Easier: user vocabulary closer to canonical language ---
    (
        "what are the four foundations of mindfulness",
        "MN 10",
        "easy",
        "MN 10 — Satipaṭṭhāna Sutta: body, feelings, mind, phenomena",
    ),
    (
        "what are the components of the noble eightfold path",
        "MN 117",
        "easy",
        "MN 117 — right view through right concentration",
    ),
    (
        "how should one treat parents family and friends according to the Buddha",
        "DN 31",
        "easy",
        "DN 31 — Sigālovāda Sutta: duties to parents, spouse, friends, teachers",
    ),
    (
        "are the five aggregates permanent or do they lack a self",
        "SN 22.59",
        "easy",
        "SN 22.59 — Anattalakkhaṇa Sutta: form, feeling, etc. are not self",
    ),
    (
        "what did the Buddha consider after enlightenment before deciding to teach",
        "MN 26",
        "easy",
        "MN 26 — Ariyapariyesanā Sutta: teaching to those with little dust in their eyes",
    ),
]


def _sutta_of(chunk_id: str) -> str:
    """Extract 'MN 61' from 'MN 61:36'."""
    return chunk_id.rsplit(":", 1)[0].strip()


async def run_benchmark(top_k: int = 10, with_expansion: bool = False) -> list[dict]:
    client = AsyncQdrantClient(url="http://localhost:6333")
    executor = ThreadPoolExecutor(max_workers=2)

    if with_expansion:
        from pathlib import Path
        from backend.app.services.search_pipeline import SearchPipeline
        from backend.app.services.sutta_title_index import SuttaTitleIndex
        _dumps_dir = Path(__file__).parent.parent.parent / "data" / "dumps"
        title_index = SuttaTitleIndex.from_directory(_dumps_dir)
        pipeline = SearchPipeline(title_index=title_index)
        async def retrieve(query):
            return await pipeline.search(query, top_k=top_k)
    else:
        retriever = Retriever(client, EmbeddingManager(), COLLECTION, executor)
        async def retrieve(query):
            return await retriever.retrieve(query, top_k=top_k)

    results = []
    for query, expected_sutta, difficulty, note in BENCHMARK_CASES:
        chunks = await retrieve(query)
        retrieved_suttas = {_sutta_of(c["id"]) for c in chunks}
        hit = expected_sutta in retrieved_suttas
        best_score = chunks[0]["score"] if chunks else 0.0
        results.append({
            "query": query,
            "expected": expected_sutta,
            "difficulty": difficulty,
            "note": note,
            "hit": hit,
            "best_score": best_score,
        })

    executor.shutdown()
    return results


def _print_report(results: list[dict], top_k: int, mode: str = "raw vector, no expansion") -> None:
    W = 52
    print(f"\n{'─' * (W + 30)}")
    print(f"  PCAIsearch retrieval benchmark  —  recall@{top_k}  ({mode})")
    print(f"{'─' * (W + 30)}")
    print(f"  {'Query':<{W}} {'Expected':<12} {'Diff':<8} Hit   Score")
    print(f"  {'─'*W} {'─'*12} {'─'*8} {'─'*5} {'─'*5}")

    by_diff: dict[str, list] = {"hard": [], "medium": [], "easy": []}
    for r in results:
        by_diff[r["difficulty"]].append(r)

    for diff in ("hard", "medium", "easy"):
        for r in by_diff[diff]:
            mark = "✓" if r["hit"] else "✗"
            q = r["query"][:W]
            print(f"  {q:<{W}} {r['expected']:<12} {r['difficulty']:<8} {mark}     {r['best_score']:.3f}")

    print()
    total = len(results)
    total_hits = sum(r["hit"] for r in results)
    for diff in ("hard", "medium", "easy"):
        group = by_diff[diff]
        hits = sum(r["hit"] for r in group)
        pct = 100 * hits // len(group) if group else 0
        print(f"  {diff.capitalize():8}: {hits}/{len(group)} ({pct}%)")

    print(f"\n  Overall recall@{top_k}: {total_hits}/{total} ({100*total_hits//total}%)")
    print(f"{'─' * (W + 30)}\n")


async def _main():
    parser = argparse.ArgumentParser(description="PCAIsearch retrieval benchmark")
    parser.add_argument("--k", type=int, default=10, help="top-k cutoff (default 10)")
    parser.add_argument("--with-expansion", action="store_true",
                        help="run full pipeline with LLM expansion (requires NVIDIA_API_KEY)")
    args = parser.parse_args()

    if args.with_expansion and not os.environ.get("NVIDIA_API_KEY"):
        print("ERROR: --with-expansion requires NVIDIA_API_KEY to be set.")
        return

    mode = "with LLM expansion" if args.with_expansion else "raw vector, no expansion"
    results = await run_benchmark(top_k=args.k, with_expansion=args.with_expansion)
    _print_report(results, top_k=args.k, mode=mode)


if __name__ == "__main__":
    asyncio.run(_main())
