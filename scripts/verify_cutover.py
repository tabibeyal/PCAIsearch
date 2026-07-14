"""Cutover verification for issue #105 — runs against the deployed backend.

Checks (after the vector rebuild + backend redeploy):
 2. Reproduction query "how does kindness is defined in the suttas?" deep-dive
    sources are canon-only (no `section: commentary`) and on topic.
 3. Results view for "kindness in the suttas" surfaces a commentary chunk
    carrying its `section: commentary` marker (labeled in the UI).
 4. A pre-existing shared answer still renders (GET /share/<id>).

Check 1 — recall@10 — is run separately via scripts/run_recall_benchmark.sh
(which drives tests/backend/retrieval_benchmark.py) and recorded on the issue.
Prints a structured report. No secrets.
"""
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error

BACKEND = os.environ.get("BACKEND_URL", "https://pcaisearch-jol64.ondigitalocean.app").rstrip("/")
SHARE_ID = os.environ.get("SHARE_ID", "d6dc5800e8e549288f40c078b58ae13d")


def get(path: str, timeout: int = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(f"{BACKEND}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


print(f"backend: {BACKEND}\n")

# --- Check 2: deep-dive sources are canon-only and on topic -------------------
print("=== Check 2: reproduction query deep-dive sources ===")
q2 = "how does kindness is defined in the suttas?"
status, body = get(f"/synthesize?q={urllib.parse.quote(q2)}&top_k=10", timeout=180)
synth = json.loads(body)
ctx = synth.get("context", [])
commentary_sources = [c for c in ctx if c.get("section") == "commentary"]
print(f"status: {status}")
print(f"answer (first 280 chars): {(synth.get('answer') or '')[:280]!r}")
print(f"sources ({len(ctx)}):")
for c in ctx:
    print(f"  - id={c.get('id')!r} section={c.get('section')!r} "
          f"title={c.get('title_english') or c.get('title')!r}")
print(f"commentary sources in deep-dive (must be 0): {len(commentary_sources)}")
answer_lc = (synth.get("answer") or "").lower()
# Whole-word match only — a bare "kind" substring would false-positive on
# "kind of" / "unkind" / "childhood".
on_topic = bool(re.search(r"\b(kindness|metta|friendliness|friendly|goodwill)\b", answer_lc))
print(f"answer on-topic (kindness/metta/friendliness/goodwill): {on_topic}")

# --- Check 3: results view surfaces a labeled commentary chunk ----------------
print("\n=== Check 3: results-view commentary label ===")
q3 = "kindness in the suttas"
status, body = get(f"/search?q={urllib.parse.quote(q3)}&top_k=15", timeout=120)
sr = json.loads(body)
results = sr.get("results", [])
commentary_hits = [r for r in results if r.get("section") == "commentary"]
print(f"status: {status}")
print(f"results ({len(results)}):")
for r in results:
    print(f"  - id={r.get('id')!r} section={r.get('section')!r} "
          f"title={r.get('title_english') or r.get('title')!r}")
print(f"commentary results (need >=1): {len(commentary_hits)}")
if commentary_hits:
    print(f"sample commentary result id: {commentary_hits[0].get('id')!r}")

# --- Check 4: pre-existing shared answer renders -----------------------------
print("\n=== Check 4: pre-existing shared answer ===")
try:
    status, body = get(f"/share/{SHARE_ID}", timeout=30)
    share = json.loads(body)
    print(f"status: {status}")
    print(f"share query: {share.get('query')!r}")
    print(f"share answer (first 200 chars): {(share.get('answer') or '')[:200]!r}")
    print(f"share context chunks: {len(share.get('context') or [])}")
    print("renders: yes (backend returned the stored answer + context)")
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} {e.reason} body={e.read()[:200]!r}")
except Exception as e:
    print(f"error: {e!r}")