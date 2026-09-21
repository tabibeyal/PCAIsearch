"""Throwaway probe: can Jev (TypeSafe System One) pick the right triage label?

Answers wayfinder ticket "Pick GitHub triage labels with Jev" (#201).
Not a pytest test: makes paid network calls and shells out to `gh`. Run by hand.

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
        && PYTHONPATH=. python3 tests/prototypes/jev_triage_probe.py

Ground truth: this repo's own closed issues that carry exactly one of the five
canonical triage labels (docs/agents/triage-labels.md). Ambiguous issues (more
than one canonical label, e.g. #119 carries both wontfix and ready-for-agent)
are excluded — there is no single right answer to score against.

Jev is asked to label from title + body alone, as if triaging on arrival,
because that's when a real bot would run: before any comments exist.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
REPO_DIR = Path(__file__).resolve().parents[2]

# Closed issues carrying exactly one canonical triage label, found via:
#   gh issue list --state closed --json number,title,labels
# then filtering to issues whose labels include exactly one of the five.
# #119 (wontfix + ready-for-agent) is excluded as ambiguous ground truth.
GROUND_TRUTH_NUMBERS = [
    163, 161, 156, 152, 151, 147, 144, 143, 139, 129, 128, 105, 104, 103, 102,
    101, 100, 98, 89, 80, 79, 77, 76, 74, 73, 72, 70, 69, 68, 67, 64, 63, 62,
    60, 59, 58, 57, 53, 52, 51,
]

# The docs' no-match convention for Choice: no dedicated "none" mechanism,
# add an explicit escape-hatch option instead.
NO_MATCH = "unclear"

LABEL_QUESTION = {
    "type": "choice",
    "instructions": (
        "You are triaging a GitHub issue for a software repository the moment "
        "it is filed, before any comments or discussion exist. Based only on "
        "`issue.title` and `issue.body`, pick the label that fits best. Most "
        "issues in this repository arrive already scoped into a concrete, "
        "actionable work item by the maintainer or a previous agent session — "
        "lean toward ready-for-agent unless the text clearly needs reporter "
        "clarification, a subjective product/design call, or access an agent "
        "does not have."
    ),
    "criteria": {
        "needs-triage": (
            "Nobody has evaluated this yet, or the report is vague, "
            "underspecified, or its validity is unclear. The default when "
            "nothing below clearly fits better."
        ),
        "needs-info": (
            "The issue is missing information only the reporter can supply "
            "before anyone could act on it — reproduction steps, examples, "
            "or specifics."
        ),
        "ready-for-agent": (
            "The problem and the fix are specific enough that an autonomous "
            "coding agent, working alone with no further clarification, "
            "could carry it out."
        ),
        "ready-for-human": (
            "The work clearly needs doing, but requires something only a "
            "person can provide: a judgment call, a design or product "
            "decision, or access an agent doesn't have."
        ),
        "wontfix": (
            "The issue text itself says or clearly implies the work will "
            "not be done — rejected, out of scope, duplicate, superseded."
        ),
        NO_MATCH: "None of the above fits this issue confidently.",
    },
}

usage_totals = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
API_KEY = None


def load_key():
    """TYPESAFE_API_KEY from environment, else nearest .env above us."""
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
    sys.exit("TYPESAFE_API_KEY not set and no .env file defines it.")


def ask(state, questions):
    body = json.dumps({"state": state, "model": MODEL, "questions": questions})
    req = urllib.request.Request(
        ENDPOINT, data=body.encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    seconds = time.monotonic() - started
    usage = payload.get("usage", {})
    usage_totals["input_tokens"] += usage.get("input_tokens", 0)
    usage_totals["output_tokens"] += usage.get("output_tokens", 0)
    usage_totals["requests"] += 1
    return payload["answers"], seconds


def fetch_ground_truth(numbers):
    """Pull title/body/labels for each issue via `gh`, keep the one canonical label."""
    canonical = {"needs-triage", "needs-info", "ready-for-agent", "ready-for-human", "wontfix"}
    issues = []
    for number in numbers:
        result = subprocess.run(
            ["gh", "issue", "view", str(number), "--json", "number,title,body,labels"],
            cwd=REPO_DIR, capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        labels = [l["name"] for l in data["labels"]]
        hits = [l for l in labels if l in canonical]
        if len(hits) != 1:
            continue  # ambiguous or unlabelled — not usable ground truth
        issues.append({"number": data["number"], "title": data["title"],
                        "body": data["body"] or "", "true_label": hits[0]})
    return issues


def classify(issue):
    state = {"issue": {"title": issue["title"], "body": issue["body"]}}
    answers, seconds = ask(state, {"label": LABEL_QUESTION})
    answer = answers["label"]
    return {
        "number": issue["number"], "title": issue["title"],
        "true_label": issue["true_label"], "predicted": answer["choice"],
        "confidence": answer["confidence"], "probabilities": answer["probabilities"],
        "correct": answer["choice"] == issue["true_label"], "seconds": seconds,
    }


def summarize(results):
    total = len(results)
    correct = sum(r["correct"] for r in results)
    no_match = sum(r["predicted"] == NO_MATCH for r in results)
    by_true_label = {}
    for r in results:
        bucket = by_true_label.setdefault(r["true_label"], {"n": 0, "correct": 0})
        bucket["n"] += 1
        bucket["correct"] += r["correct"]
    return {"total": total, "correct": correct, "accuracy": correct / total,
            "no_match_count": no_match, "by_true_label": by_true_label}


def main():
    global API_KEY
    API_KEY = load_key()
    print("Fetching ground truth from closed, single-labelled issues...")
    issues = fetch_ground_truth(GROUND_TRUTH_NUMBERS)
    print(f"{len(issues)} usable ground-truth issues "
          f"(of {len(GROUND_TRUTH_NUMBERS)} candidates)")

    print(f"\n{'ok':>3} {'true':>16} {'predicted':>16} {'conf':>5} issue")
    results = []
    for issue in issues:
        result = classify(issue)
        results.append(result)
        mark = "yes" if result["correct"] else "NO"
        print(f"{mark:>3} {result['true_label']:>16} {result['predicted']:>16} "
              f"{result['confidence']:5.2f} #{result['number']} {result['title']}")

    summary = summarize(results)
    print(f"\n--> {summary['correct']}/{summary['total']} correct "
          f"({summary['accuracy']:.0%})")
    print(f"--> {summary['no_match_count']} answered '{NO_MATCH}' (no confident pick)")
    print("\nper true label:")
    for label, bucket in sorted(summary["by_true_label"].items()):
        print(f"  {label:>16}: {bucket['correct']}/{bucket['n']}")

    cost = usage_totals["input_tokens"] / 1_000_000 * 0.042
    print("\n=== cost ===")
    print(f"requests: {usage_totals['requests']}  "
          f"input tokens: {usage_totals['input_tokens']}  "
          f"estimated cost: ${cost:.5f}")

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_suffix(".results.json")
    out.write_text(json.dumps({"results": results, "summary": summary,
                                "usage": usage_totals}, indent=2, ensure_ascii=False))
    print(f"raw answers written to {out}")


if __name__ == "__main__":
    main()
