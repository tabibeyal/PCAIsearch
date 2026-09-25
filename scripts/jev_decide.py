#!/usr/bin/env python3
"""jev_decide.py - ask Jev (TypeSafe System One) one of the fixed wayfinder
decision questions and apply the threshold gates.

Standard library only. Requires TYPESAFE_API_KEY in the environment.

Usage:
  python3 scripts/jev_decide.py classify --destination "..." --ticket "..."
  python3 scripts/jev_decide.py fog      --destination "..." --question "..." --open-ticket "#14 ..."
  python3 scripts/jev_decide.py next     --destination "..." --frontier "12=Add BM25 fallback" --frontier "15=..."
  python3 scripts/jev_decide.py resolved --ticket "..." --evidence "..."
  python3 scripts/jev_decide.py risk     --change "..." --closed-decision "..."
  gh issue list --json number,title,labels | jq '{frontier: .}' \
    | python3 scripts/jev_decide.py next --state -

Output: JSON on stdout with `decision` = act | ask_human | fall_back_to_default.
Exit codes: 0 act, 10 ask_human, 20 fall_back_to_default, 2 usage error.
Add --dry-run to print the request body without calling the API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.typesafe.ai/v1/systemone"
REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / ".claude" / "skills" / "jev-decisions" / "questions.json"
FRONTIER_PLACEHOLDER = "{{FRONTIER}}"
# The API docs ask callers to back off and retry on these two statuses.
RETRY_STATUSES = {429, 529}
RETRY_DELAYS = (2.0, 5.0)

EXIT = {"act": 0, "ask_human": 10, "fall_back_to_default": 20}


def load_config() -> dict:
    with QUESTIONS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_model(config: dict) -> str:
    # MODEL PINNING: "jev-latest" is an alias that can move to a new model.
    # Once results look right, pin the concrete version the API echoes back in
    # the response `model` field (e.g. "jev-1.13.0"): either set JEV_MODEL in
    # the environment or change "model" in questions.json.
    return os.environ.get("JEV_MODEL") or config.get("model") or "jev-latest"


def build_state(args: argparse.Namespace) -> dict:
    state: dict = {}
    if args.state:
        raw = sys.stdin.read() if args.state == "-" else Path(args.state).read_text(encoding="utf-8")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("--state must be a JSON object")
        state.update(loaded)
    if args.destination:
        state["map_destination"] = args.destination
    if args.notes:
        state["notes"] = args.notes
    if isinstance(state.get("closed_decisions"), str):
        state["closed_decisions"] = [state["closed_decisions"]]
    if args.closed_decision:
        state.setdefault("closed_decisions", []).extend(args.closed_decision)
    if args.ticket:
        state["ticket"] = args.ticket
    if args.question:
        state["open_question"] = args.question
    if args.open_ticket:
        state.setdefault("open_tickets", []).extend(args.open_ticket)
    if args.evidence:
        state["evidence"] = args.evidence
    if args.change:
        state["change"] = args.change
    for item in args.frontier or []:
        issue_id, _, summary = item.partition("=")
        state.setdefault("frontier", []).append(
            {"id": issue_id.strip().lstrip("#"), "summary": summary.strip(), "labels": []}
        )
    return state


def filter_frontier(state: dict, exclude_labels: list[str]) -> list[dict]:
    """Drop claimed issues. Backstop: the caller should already have filtered.

    Accepts our own shape ({id, summary, labels: [str]}) and `gh issue list
    --json number,title,labels` output, where labels are {"name": ...} objects.
    """
    kept = []
    for entry in state.get("frontier", []):
        if isinstance(entry, (str, int)):
            entry = {"id": str(entry)}
        labels = {lab["name"] if isinstance(lab, dict) else lab for lab in entry.get("labels") or []}
        if labels & set(exclude_labels):
            continue
        issue_id = str(entry.get("id", entry.get("number", ""))).lstrip("#")
        if not issue_id:
            raise ValueError(f"frontier entry has no id or number: {entry}")
        kept.append({"id": issue_id,
                     "summary": entry.get("summary") or entry.get("title") or "",
                     "labels": sorted(labels)})
    return kept


def inject_frontier(questions: dict, frontier: list[dict]) -> dict:
    criteria = {e["id"]: (e.get("summary") or f"Issue #{e['id']}") for e in frontier}
    out = json.loads(json.dumps(questions))
    for q in out.values():
        if q.get("criteria") == FRONTIER_PLACEHOLDER:
            q["criteria"] = criteria
    return out


def call_jev(body: dict, timeout: float) -> dict:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is not set")
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for delay in (*RETRY_DELAYS, None):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUSES and delay is not None:
                time.sleep(delay)
                continue
            detail = e.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e


def issue_sort_key(issue_id: str):
    m = re.search(r"\d+", issue_id)
    return (0, int(m.group())) if m else (1, issue_id)


def default_value(gate: dict, frontier: list[dict]):
    d = gate.get("default")
    if d == "lowest_issue_number":
        return min((e["id"] for e in frontier), key=issue_sort_key) if frontier else None
    return d


def apply_gate(point: str, gate: dict, answers: dict, frontier: list[dict]) -> dict:
    kind = gate["kind"]

    if kind == "choice_confidence":
        a = answers[gate["question"]]
        choice, conf = a.get("choice"), float(a.get("confidence", 0.0))
        if conf >= gate["min_confidence"]:
            return with_pairing(gate, {"decision": "act", "value": choice,
                                       "reason": f"confidence {conf:.2f} >= {gate['min_confidence']}"})
        fallback = gate["on_low_confidence"]
        return with_pairing(gate, {
            "decision": fallback,
            "value": default_value(gate, frontier) if fallback == "fall_back_to_default" else None,
            "top_answer": choice,
            "reason": f"confidence {conf:.2f} < {gate['min_confidence']}"})

    if kind == "noul_bands":
        p = float(answers[gate["question"]]["noul"])
        if p >= gate["yes_at_or_above"]:
            return {"decision": "act", "value": True, "reason": f"noul {p:.2f} >= {gate['yes_at_or_above']}"}
        if p < gate["no_below"]:
            return {"decision": "act", "value": False, "reason": f"noul {p:.2f} < {gate['no_below']}"}
        return {"decision": gate["on_middle"], "value": None,
                "reason": f"noul {p:.2f} in the uncertain band"}

    if kind == "risk":
        s = answers[gate["score_question"]]
        level, conf = float(s.get("score", 99)), float(s.get("confidence", 0.0))
        contra = float(answers[gate["contradiction_question"]]["noul"])
        problems = []
        if level > gate["max_level"]:
            problems.append(f"risk level {level:g} > {gate['max_level']}")
        if conf < gate["min_confidence"]:
            problems.append(f"score confidence {conf:.2f} < {gate['min_confidence']}")
        if contra >= gate["max_contradiction"]:
            problems.append(f"contradicts_decision {contra:.2f} >= {gate['max_contradiction']}")
        if problems:
            return {"decision": gate["on_fail"], "value": level, "reason": "; ".join(problems)}
        return {"decision": "act", "value": level,
                "reason": f"level {level:g}, confidence {conf:.2f}, contradiction {contra:.2f}"}

    raise ValueError(f"unknown gate kind: {kind}")


def with_pairing(gate: dict, result: dict) -> dict:
    # Grilling pairs with domain-modeling whether Jev chose it or it is the fallback.
    pair = (gate.get("pair_with") or {}).get(result["value"])
    if pair:
        result["pair_with"] = pair
    return result


def error_result(gate: dict, frontier: list[dict], reason: str) -> dict:
    decision = gate.get("on_error", "fall_back_to_default")
    value = default_value(gate, frontier) if decision == "fall_back_to_default" else None
    if decision == "fall_back_to_default" and value is None:
        # e.g. `next` failed before the frontier was known: there is no default to fall back to.
        decision = "ask_human"
    return with_pairing(gate, {"decision": decision, "value": value, "reason": reason})


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ask Jev a fixed wayfinder decision question.")
    p.add_argument("point", choices=["classify", "fog", "next", "resolved", "risk"])
    p.add_argument("--state", help="JSON object state file, or - for stdin. Flags below are merged on top.")
    p.add_argument("--destination", help="Current wayfinder:map destination.")
    p.add_argument("--notes", help="Relevant map notes.")
    p.add_argument("--closed-decision", action="append", help="A closed decision. Repeatable.")
    p.add_argument("--ticket", help="Ticket title/body (classify, resolved).")
    p.add_argument("--question", help="Open question or idea (fog).")
    p.add_argument("--open-ticket", action="append", help="An open map ticket as '#id title' (fog). Repeatable.")
    p.add_argument("--frontier", action="append", help="Frontier issue as id=summary (next). Repeatable.")
    p.add_argument("--evidence", help="Evidence of completion (resolved).")
    p.add_argument("--change", help="Proposed change (risk).")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--dry-run", action="store_true", help="Print the request body and exit.")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        config = load_config()
        gate = config["decisions"][args.point]["gate"]
        state = build_state(args)
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}), file=sys.stderr)
        return 2

    # Any unexpected failure still has to end in one of the three documented
    # decisions, or the agent reads a traceback instead of an instruction.
    try:
        return decide(args, config, gate, state)
    except Exception as e:
        out = {"decision_point": args.point, "thresholds": gate}
        out.update(error_result(gate, [], f"jev_decide failed: {type(e).__name__}: {e}"))
        print(json.dumps(out, indent=2))
        return EXIT[out["decision"]]


def decide(args: argparse.Namespace, config: dict, gate: dict, state: dict) -> int:
    questions = config["decisions"][args.point]["questions"]
    frontier: list[dict] = []
    out: dict = {"decision_point": args.point, "thresholds": gate}

    if args.point == "next":
        frontier = filter_frontier(state, gate.get("exclude_labels", []))
        state["frontier"] = frontier
        if not frontier:
            out.update({"decision": "ask_human", "value": None,
                        "reason": "frontier is empty after excluding claimed issues"})
            print(json.dumps(out, indent=2))
            return EXIT["ask_human"]
        if len(frontier) == 1:
            out.update({"decision": "act", "value": frontier[0]["id"],
                        "reason": "only one unclaimed frontier issue; no API call"})
            print(json.dumps(out, indent=2))
            return EXIT["act"]
        questions = inject_frontier(questions, frontier)

    body = {"state": state, "model": resolve_model(config), "questions": questions}
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0

    try:
        resp = call_jev(body, args.timeout)
        answers = resp["answers"]
        out["model"] = resp.get("model")  # concrete version actually used - pin this
        out["answers"] = answers
        out.update(apply_gate(args.point, gate, answers, frontier))
    except (RuntimeError, OSError, KeyError, TypeError, ValueError) as e:
        out.update(error_result(gate, frontier, f"Jev call failed: {e}"))

    print(json.dumps(out, indent=2))
    return EXIT[out["decision"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
