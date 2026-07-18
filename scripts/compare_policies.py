"""Side-by-side comparison of deep-dive retrieval policies (issue #111).

Produces a markdown asset comparing what each candidate policy would hand to
the deep-dive answer flow for a fixed set of multi-nikāya queries.

Policies compared:
  1. round_robin      - status-quo interleave (one per selected book in turn)
  2. global_best      - pure rerank order across selected books
  3. relevance_floor  - interleave with a per-book relevance threshold

Usage:
    PYTHONPATH=. NVIDIA_API_KEY=... QDRANT_URL=... QDRANT_API_KEY=... \
        python3 scripts/compare_policies.py

Output:
    analysis/policy-comparison-YYYY-MM-DD.md
    analysis/policy-comparison-YYYY-MM-DD.json
"""

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

# Add repo root to PYTHONPATH for imports when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.services.search_pipeline import SearchPipeline
from backend.app.services.bm25_retriever import BM25Retriever
from backend.app.services.sutta_title_index import SuttaTitleIndex

_DUMPS_DIR = ROOT / "data" / "dumps"
_ANALYSIS_DIR = ROOT / "analysis"

# Deep-dive path: canon-only, same top_k the answer flow uses.
_TOP_K = 10
_NIKAYAS = ["DN", "MN", "SN", "AN", "DHP", "ITI"]

_QUERIES = [
    "What did the Buddha say about anger?",
    "How does one develop mindfulness in meditation?",
    "What is the middle way between indulgence and asceticism?",
    "What happens after death according to the Buddha?",
]

_POLICIES = [
    "round_robin",
    "global_best",
    "relevance_floor:0.60",
    "relevance_floor:0.75",
    "relevance_floor:0.90",
]


def _get_sutta_id(chunk_id: str) -> str:
    return chunk_id.rsplit(":", 1)[0]


def _get_nikaya(chunk_id: str) -> str:
    return chunk_id.split(" ", 1)[0] if chunk_id else "?"


def _make_gist(english: str) -> str:
    text = (english or "").replace("\n", " ").strip()
    if len(text) <= 120:
        return text
    return text[:119] + "…"


def _get_title(chunk: dict, title_index: SuttaTitleIndex) -> str:
    sutta_key = _get_sutta_id(chunk.get("id", "")).replace(" ", "")
    title = title_index.get_title_text(sutta_key)
    return title or _get_sutta_id(chunk.get("id", ""))


async def _run(pipeline: SearchPipeline, title_index: SuttaTitleIndex) -> dict:
    results = {"queries": []}
    for query in _QUERIES:
        query_results = {"query": query, "nikayas": list(_NIKAYAS), "policies": {}}
        for policy in _POLICIES:
            try:
                chunks = await pipeline.search(
                    query,
                    top_k=_TOP_K,
                    nikayas=list(_NIKAYAS),
                    exclude_commentary=True,
                    policy=policy,
                )
            except Exception as exc:
                query_results["policies"][policy] = {
                    "error": f"{type(exc).__name__}: {exc}"
                }
                continue

            rows = []
            for rank, chunk in enumerate(chunks, start=1):
                rows.append(
                    {
                        "rank": rank,
                        "id": chunk.get("id"),
                        "nikaya": _get_nikaya(chunk.get("id", "")),
                        "title": _get_title(chunk, title_index),
                        "match_pct": round(chunk.get("score", 0.0) * 100, 1),
                        "gist": _make_gist(chunk.get("english", "")),
                    }
                )
            query_results["policies"][policy] = {
                "source_count": len(rows),
                "rows": rows,
            }
        results["queries"].append(query_results)
    return results


def _render_markdown(results: dict) -> str:
    """Render comparison results as a markdown document."""
    lines = [
        "# Deep-dive retrieval policy comparison",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "This asset compares the source lists that three candidate retrieval policies would feed to the deep-dive answer flow. All runs use the canon-only path (`exclude_commentary=True`) and the same six nikāyas selected, matching the reproduced scenario from issue #99.",
        "",
        "- **round_robin** — status quo: one result per selected nikāya in turn.",
        "- **global_best** — pure rerank order across the selected nikāyas; no representation guarantee.",
        "- **relevance_floor:X.XX** — round-robin, but a nikāya only contributes chunks whose raw rerank score is at least `X.XX` times the best score in the candidate set.",
        "",
        "The *Match %* column is the rank-normalized score the UI would display for that result set. The *Gist* is the first ~120 characters of the retrieved passage; judge on-topic/off-topic manually from the gist and title.",
        "",
    ]

    for query_results in results["queries"]:
        lines.extend(
            [
                f"## Query: {query_results['query']}",
                "",
                f"Selected nikāyas: {', '.join(query_results['nikayas'])}",
                "",
            ]
        )

        for policy in _POLICIES:
            policy_data = query_results["policies"].get(policy, {})
            if "error" in policy_data:
                lines.extend([f"### {policy}", "", f"Error: {policy_data['error']}", ""])
                continue

            lines.extend(
                [
                    f"### {policy} ({policy_data.get('source_count', 0)} sources)",
                    "",
                    "| # | Sutta ID | Nikāya | Title | Match % | Gist |",
                    "|---|----------|--------|-------|--------:|------|",
                ]
            )
            for row in policy_data.get("rows", []):
                title = row['title'].replace('|', '\\|')
                gist = row['gist'].replace('|', '\\|').replace('\n', ' ')
                lines.append(
                    f"| {row['rank']} | {row['id']} | {row['nikaya']} | {title} | {row['match_pct']}% | {gist} |"
                )
            lines.append("")

    lines.extend(
        [
            "## How to reproduce",
            "",
            "```bash",
            "PYTHONPATH=. NVIDIA_API_KEY=... QDRANT_URL=... QDRANT_API_KEY=... \\",
            "    python3 scripts/compare_policies.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    if not os.environ.get("NVIDIA_API_KEY"):
        print("ERROR: NVIDIA_API_KEY is required for query expansion.")
        print("Set it, or run with a local backend that has it configured.")
        return 1

    if not _DUMPS_DIR.exists():
        print(f"ERROR: dumps directory not found: {_DUMPS_DIR}")
        return 1

    _ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    title_index = SuttaTitleIndex.from_directory(_DUMPS_DIR)
    bm25_retriever = BM25Retriever.from_directory(_DUMPS_DIR)
    pipeline = SearchPipeline(title_index=title_index, bm25_retriever=bm25_retriever)

    print("Running comparison...")
    try:
        results = asyncio.run(_run(pipeline, title_index))
    finally:
        pipeline.shutdown()

    stem = f"policy-comparison-{date.today().isoformat()}"
    md_path = _ANALYSIS_DIR / f"{stem}.md"
    json_path = _ANALYSIS_DIR / f"{stem}.json"

    md_path.write_text(_render_markdown(results), encoding="utf-8")
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
