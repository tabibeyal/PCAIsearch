"""
Live-query analysis for issue #135, part 2.

Asks the deployed backend a set of strong-pool queries (the recall@10
benchmark cases -- correctly spelled, on-topic) and weak-pool queries
(typos and off-topic prompts that should trip the ADR-0009 floor), then
compares the word-length distribution of the chunks each kind of page
surfaces. Answers: do weak-pool pages disproportionately surface short,
context-free chunks?

Hits the project's own deployed backend (read-only /search endpoint) --
no local models, no OS freeze risk. Rate limit is 30/min, so we sleep
between requests.

Run:
    python3 analysis/weak_pool_surfaces.py
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

BACKEND = "https://pcaisearch-jol64.ondigitalocean.app"
WORD_FLOOR = 12  # match corpus analysis threshold
TOP_K = 10

# Correctly-spelled, on-topic -> expected strong pools.
STRONG_QUERIES = [
    "what is the one precept you should never break",
    "what were the Buddha's last words before he died",
    "why does loving someone lead to grief and suffering",
    "should a monk feel anger even if attacked with a saw",
    "is having a good spiritual friend the whole of the holy life",
    "what is the path between self-indulgence and harsh self-denial",
    "what is the deepest origin of all suffering",
    "how should one breathe mindfully during sitting meditation",
    "how does ignorance cause suffering step by step",
    "how do you know whether a religious teaching is worth following",
    "what are the four foundations of mindfulness",
    "what are the components of the noble eightfold path",
    "how should one treat parents family and friends according to the Buddha",
    "are the five aggregates permanent or do they lack a self",
    "what did the Buddha consider after enlightenment before deciding to teach",
    "is there more than one version of the definition of suffering",
]

# Typos of core terms + topics the Pali Canon does not cover -> expected weak pools.
WEAK_QUERIES = [
    "consentration",
    "medtation technique",
    "mindfulnes practice",
    "carburetor adjustment",
    "quantum field theory explained",
    "how to bake sourdough bread",
    "best pizza in naples",
    "python decorator syntax",
    "kubernetes pod crashloop backoff",
    "stock market prediction algorithm",
    "what is the capital of france",
    "how to fix a leaky faucet",
]


def search(q: str) -> dict:
    url = f"{BACKEND}/search?q={urllib.parse.quote(q)}&top_k={TOP_K}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def word_count(text: str) -> int:
    return len((text or "").split())


def collect(queries, label, sleep=2.5):
    pages = []
    for i, q in enumerate(queries):
        try:
            data = search(q)
        except Exception as e:
            print(f"  [{label}] query failed: {q!r} -> {e}")
            time.sleep(sleep)
            continue
        weak = bool(data.get("is_weak_pool"))
        results = data.get("results", [])
        word_counts = [word_count(r.get("english", "")) for r in results]
        pages.append({
            "query": q,
            "is_weak_pool": weak,
            "n_results": len(results),
            "result_words": word_counts,
            "top_ids": [r.get("id") for r in results[:3]],
        })
        flag = "WEAK" if weak else "strong"
        top_wc = word_counts[0] if word_counts else 0
        print(f"  [{label}] {flag:<5} top={top_wc:>2}w  q={q!r}")
        time.sleep(sleep)
    return pages


def main():
    print("=== Strong-pool queries (benchmark) ===")
    strong_pages = collect(STRONG_QUERIES, "strong")
    print("\n=== Weak-pool queries (typos + off-topic) ===")
    weak_pages = collect(WEAK_QUERIES, "weak")

    all_pages = strong_pages + weak_pages
    print("\n" + "=" * 60)
    print("AGGREGATE: weak-pool pages vs strong-pool pages (regardless of query set)")
    print("=" * 60)
    weak = [p for p in all_pages if p["is_weak_pool"]]
    strong = [p for p in all_pages if not p["is_weak_pool"]]
    print(f"  pages: {len(weak)} weak, {len(strong)} strong (of {len(all_pages)} total)")
    for kind, sub in (("weak", weak), ("strong", strong)):
        if not sub:
            print(f"  {kind}: none")
            continue
        all_wc = [w for p in sub for w in p["result_words"]]
        top_wc = [p["result_words"][0] for p in sub if p["result_words"]]
        short_all = sum(1 for w in all_wc if w <= WORD_FLOOR)
        short_top = sum(1 for w in top_wc if w <= WORD_FLOOR)
        print(f"  {kind} ({len(sub)} pages, {len(all_wc)} chunks surfaced):")
        print(f"    short (<= {WORD_FLOOR}w) among ALL surfaced:  {short_all}/{len(all_wc)} "
              f"= {100.0*short_all/len(all_wc):.1f}%")
        print(f"    short (<= {WORD_FLOOR}w) among TOP result:    {short_top}/{len(top_wc)} "
              f"= {100.0*short_top/len(top_wc):.1f}%")
        print(f"    top-result word counts: {sorted(top_wc)}")
    print()
    # Show the actual top result of each weak-pool page
    print("=== Weak-pool pages: top result per page ===")
    for p in weak:
        top_wc = p["result_words"][0] if p["result_words"] else 0
        top_id = p["top_ids"][0] if p["top_ids"] else "?"
        flag = "  <-- SHORT" if top_wc <= WORD_FLOOR else ""
        print(f"  {top_id:<14} [{top_wc:>2}w]  q={p['query']!r}{flag}")

    # Persist raw per-query results so the Part 2 numbers in the report are
    # auditable without re-running the ~12-minute live sweep against the
    # deployed backend.
    out_path = Path(__file__).parent / "issue-135-weak-pool-run-2026-07-21.json"
    payload = {
        "backend": BACKEND,
        "word_floor": WORD_FLOOR,
        "top_k": TOP_K,
        "strong_queries": strong_pages,
        "weak_queries": weak_pages,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\nraw per-query results written to {out_path} "
          f"({len(weak)} weak, {len(strong)} strong pages)")


if __name__ == "__main__":
    main()