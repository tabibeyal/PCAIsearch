"""
Retrieval benchmark for PCAIsearch.

Measures recall@k: does the expected sutta appear anywhere in the top-k results?

Run standalone:
    PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py
    PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --k 20

    # With BM25 + vector fusion (no API key needed):
    PYTHONPATH=. python3 tests/backend/retrieval_benchmark.py --with-bm25

    # With LLM expansion (requires NVIDIA_API_KEY):
    PYTHONPATH=. NVIDIA_API_KEY=... python3 tests/backend/retrieval_benchmark.py --with-expansion

Raw mode (default) tests vector retrieval only — no API key needed, fast.
BM25 mode tests vector + BM25 + RRF fusion — no API key needed.
Expansion mode tests the full pipeline including query expansion.
"""

import asyncio
import argparse
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from qdrant_client.async_qdrant_client import AsyncQdrantClient

from backend.app.core.indexing import EmbeddingManager
from backend.app.services.retriever import Retriever

_DUMPS_DIR = Path(__file__).parent.parent.parent / "data" / "dumps"

COLLECTION = "pali_canon"

# Each case: (query, expected_suttas, difficulty, note)
# expected_suttas is a list of acceptable sutta IDs OR prefixes (with trailing dot).
# A prefix like "SN 47." matches any sutta in the SN 47 saṃyutta (e.g. SN 47.40).
# A bare ID like "MN 10" matches only that exact sutta.
# A result counts as a hit if any retrieved chunk's sutta matches any expected entry.
BENCHMARK_CASES = [
    # --- Hard: large semantic gap between user vocabulary and canonical language ---
    (
        "what is the one precept you should never break",
        ["MN 61"],
        "hard",
        "MN 61:36 — 'not ashamed to lie → no bad deed they would not do'",
    ),
    (
        "what were the Buddha's last words before he died",
        ["DN 16"],
        "hard",
        "DN 16:1433 — 'Conditions fall apart. Persist with diligence.'",
    ),
    (
        "why does loving someone lead to grief and suffering",
        ["MN 87"],
        "hard",
        "MN 87:66 — 'our loved ones are a source of sorrow'",
    ),
    (
        "should a monk feel anger even if attacked with a saw",
        ["MN 21"],
        "hard",
        "MN 21:215 — even sawed limb from limb, show no malevolence",
    ),
    (
        "is having a good spiritual friend the whole of the holy life",
        ["SN 45.2", "SN 3.18"],
        "hard",
        "SN 45.2 — 'half the spiritual life' → Buddha says it is the whole; SN 3.18 parallel",
    ),
    # --- Medium: vocabulary partially overlaps with canonical text ---
    (
        "what is the path between self-indulgence and harsh self-denial",
        ["SN 56.11"],
        "medium",
        "SN 56.11 — the middle way and the noble eightfold path",
    ),
    (
        "what is the deepest origin of all suffering",
        ["SN 56.11", "SN 12."],
        "medium",
        "SN 56.11 — second noble truth: craving; SN 12.* — dependent origination",
    ),
    (
        "how should one breathe mindfully during sitting meditation",
        ["MN 118", "SN 54."],
        "medium",
        "MN 118 — Ānāpānasati Sutta; SN 54 — Ānāpāna Saṃyutta",
    ),
    (
        "how does ignorance cause suffering step by step",
        ["SN 12."],
        "medium",
        "SN 12.* — any Nidāna-saṃyutta sutta covers the dependent origination chain",
    ),
    (
        "how do you know whether a religious teaching is worth following",
        ["AN 3.65", "AN 3.66"],
        "medium",
        "AN 3.65/66 — Kālāma Sutta and parallel: don't believe by tradition alone",
    ),
    # --- Easier: user vocabulary closer to canonical language ---
    (
        "what are the four foundations of mindfulness",
        ["MN 10", "DN 22", "SN 47."],
        "easy",
        "MN 10 / DN 22 — Satipaṭṭhāna Suttas; SN 47 — Satipaṭṭhāna Saṃyutta",
    ),
    (
        "what are the components of the noble eightfold path",
        ["MN 117", "SN 45.8", "SN 45."],
        "easy",
        "MN 117 — Mahācattārīsaka; SN 45 — Magga Saṃyutta",
    ),
    (
        "how should one treat parents family and friends according to the Buddha",
        ["DN 31"],
        "easy",
        "DN 31 — Sigālovāda Sutta: duties to parents, spouse, friends, teachers",
    ),
    (
        "are the five aggregates permanent or do they lack a self",
        ["SN 22.59"],
        "easy",
        "SN 22.59 — Anattalakkhaṇa Sutta: form, feeling, etc. are not self",
    ),
    (
        "what did the Buddha consider after enlightenment before deciding to teach",
        ["MN 26", "SN 6.1"],
        "easy",
        "MN 26 — Ariyapariyesanā; SN 6.1 — Brahmā's request to teach",
    ),
    (
        "is there more than one version of the definition of suffering",
        ["MN 141"],
        "hard",
        "MN 141 — Sāriputta's analysis drops 'association with unbeloved / separation from loved' vs Buddha's definition in SN 56.11 / DN 22",
    ),
]


def _matches(sutta: str, expected_entries: list[str]) -> bool:
    """Match if sutta equals an entry, or starts with a prefix entry (ending in '.')."""
    for e in expected_entries:
        if e.endswith("."):
            if sutta.startswith(e) or sutta == e[:-1]:
                return True
        elif sutta == e:
            return True
    return False


def _sutta_of(chunk_id: str) -> str:
    """Extract 'MN 61' from 'MN 61:36'."""
    return chunk_id.rsplit(":", 1)[0].strip()


async def run_benchmark(top_k: int = 10, with_expansion: bool = False, with_bm25: bool = False, no_rerank: bool = False, log_variants: bool = False) -> list[dict]:
    client = AsyncQdrantClient(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("QDRANT_API_KEY"),
    )
    executor = ThreadPoolExecutor(max_workers=2)

    if with_expansion:
        from backend.app.services.search_pipeline import SearchPipeline
        from backend.app.services.sutta_title_index import SuttaTitleIndex
        from backend.app.services.bm25_retriever import BM25Retriever
        title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
        bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
        pipeline = SearchPipeline(title_index=title_index, bm25_retriever=bm25_retriever)
        if no_rerank:
            pipeline.reranker.rerank_multi = lambda queries, chunks: chunks

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
    elif with_bm25:
        from backend.app.services.bm25_retriever import BM25Retriever
        from backend.app.services.fusion import rrf_fuse_multi
        retriever = Retriever(client, EmbeddingManager(), COLLECTION, executor)
        bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
        retrieval_k = max(top_k * 3, 30)
        # Single-query mode: no LLM expansion, one dense + one BM25 query fused.
        # Recall numbers are not directly comparable to --with-expansion, which
        # uses rrf_fuse_multi across all expanded query variants.
        async def retrieve(query):
            dense = await retriever.retrieve(query, retrieval_k)
            sparse = bm25_retriever.retrieve(query, retrieval_k)
            return rrf_fuse_multi([dense, sparse])[:top_k], []
    else:
        retriever = Retriever(client, EmbeddingManager(), COLLECTION, executor)
        async def retrieve(query):
            return await retriever.retrieve(query, top_k=top_k), []

    results = []
    for query, expected_suttas, difficulty, note in BENCHMARK_CASES:
        chunks, variants = await retrieve(query)
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

    executor.shutdown()
    return results


def _print_report(results: list[dict], top_k: int, mode: str = "raw vector, no expansion") -> None:
    W = 52
    print(f"\n{'─' * (W + 30)}")
    print(f"  PCAIsearch retrieval benchmark  —  recall@{top_k}  ({mode})")
    print(f"{'─' * (W + 30)}")
    print(f"  {'Query':<{W}} {'Expected':<22} {'Diff':<8} Hit   Score")
    print(f"  {'─'*W} {'─'*22} {'─'*8} {'─'*5} {'─'*5}")

    by_diff: dict[str, list] = {"hard": [], "medium": [], "easy": []}
    for r in results:
        by_diff[r["difficulty"]].append(r)

    for diff in ("hard", "medium", "easy"):
        for r in by_diff[diff]:
            mark = "✓" if r["hit"] else "✗"
            q = r["query"][:W]
            print(f"  {q:<{W}} {r['expected']:<22} {r['difficulty']:<8} {mark}     {r['best_score']:.3f}")
            if r.get("variants"):
                for i, v in enumerate(r["variants"]):
                    print(f"    variant {i}: {v}")

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
    parser.add_argument("--with-bm25", action="store_true",
                        help="run vector + BM25 + RRF fusion (no API key needed)")
    parser.add_argument("--with-expansion", action="store_true",
                        help="run full pipeline with LLM expansion (requires NVIDIA_API_KEY)")
    parser.add_argument("--no-rerank", action="store_true",
                        help="skip CrossEncoder reranking (only meaningful with --with-expansion)")
    parser.add_argument("--log-variants", action="store_true",
                        help="print generated query variants per case (only with --with-expansion)")
    args = parser.parse_args()

    if args.with_expansion and not os.environ.get("NVIDIA_API_KEY"):
        print("ERROR: --with-expansion requires NVIDIA_API_KEY to be set.")
        return

    if args.log_variants and not args.with_expansion:
        print("WARNING: --log-variants has no effect without --with-expansion.")

    if args.with_expansion and args.no_rerank:
        mode = "with LLM expansion, no rerank"
    elif args.with_expansion:
        mode = "with LLM expansion"
    elif args.with_bm25:
        mode = "vector + BM25 + RRF, no expansion"
    else:
        mode = "raw vector, no expansion"

    results = await run_benchmark(top_k=args.k, with_expansion=args.with_expansion, with_bm25=args.with_bm25, no_rerank=args.no_rerank, log_variants=args.log_variants)
    _print_report(results, top_k=args.k, mode=mode)


if __name__ == "__main__":
    asyncio.run(_main())
