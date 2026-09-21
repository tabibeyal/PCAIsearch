"""Prove the Jev-based scope guard (#198) beats the system-prompt guard it
is meant to replace.

Extends the harness from "Does Jev understand Buddhist and Pali text at
all?" (#196, PR #202) instead of rebuilding it: SCOPE_CASES is imported
straight from that probe, unchanged.

Runs the real production seam (backend.app.services.scope_guard.ScopeGuard),
not a re-implementation of it, so this proves what would actually ship.

Not a pytest test: it makes paid network calls. Run it by hand.

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
      && PYTHONPATH=. python3 tests/prototypes/jev_scope_guard_probe.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev_pali_probe import SCOPE_CASES, load_key  # noqa: E402

from backend.app.services.scope_guard import ScopeGuard  # noqa: E402

# The regression this ticket exists to fix ("adding the rule to the system
# prompt displaced the out-of-scope guard", #159): 4 runs of this exact
# question, 4/4 correct refusals on origin/master fell to 1/4 once the rule
# was added to _SYSTEM_PROMPT. Same question, same run count, reused as the
# pass/fail bar for the replacement.
REGRESSION_CASE = "what is 17 times 23?"
REGRESSION_RUNS = 4


async def probe_regression_case(guard: ScopeGuard) -> list[bool]:
    print(f"\n=== regression repro: {REGRESSION_RUNS}x {REGRESSION_CASE!r} ===")
    print("(system prompt on origin/master: 4/4 correct; after #159's prompt addition: 1/4)")
    runs = []
    for i in range(1, REGRESSION_RUNS + 1):
        in_scope = await guard.is_in_scope(REGRESSION_CASE)
        ok = "yes" if in_scope is False else "NO"
        print(f"  run {i}: in_scope={in_scope!s:>5}  correctly refused={ok}")
        runs.append(in_scope)
    correct = sum(1 for r in runs if r is False)
    print(f"--> {correct}/{REGRESSION_RUNS} correctly refused")
    return runs


async def probe_full_scope_set(guard: ScopeGuard) -> list[dict]:
    print(f"\n=== full scope set ({len(SCOPE_CASES)} cases, reused from #196 probe A) ===")
    print(f"{'in_scope':>8}  {'want':>5}  {'ok':>3}  question")
    rows = []
    for text, expected, note in SCOPE_CASES:
        in_scope = await guard.is_in_scope(text)
        ok = "yes" if in_scope == expected else "NO"
        print(f"{str(in_scope):>8}  {str(expected):>5}  {ok:>3}  {text}   [{note}]")
        rows.append({"case": text, "note": note, "expected": expected,
                     "in_scope": in_scope, "correct": in_scope == expected})
    right = sum(r["correct"] for r in rows)
    print(f"--> {right}/{len(rows)} correct")
    return rows


async def main() -> None:
    guard = ScopeGuard(api_key=load_key())
    regression_runs = await probe_regression_case(guard)
    scope_rows = await probe_full_scope_set(guard)

    regression_correct = sum(1 for r in regression_runs if r is False)
    scope_correct = sum(r["correct"] for r in scope_rows)
    print("\n=== summary ===")
    print(f"regression repro: {regression_correct}/{REGRESSION_RUNS}")
    print(f"full scope set:   {scope_correct}/{len(scope_rows)}")

    out = Path(__file__).with_suffix(".results.json")
    out.write_text(json.dumps({
        "regression_case": REGRESSION_CASE,
        "regression_runs": regression_runs,
        "scope_set": scope_rows,
    }, indent=2, ensure_ascii=False))
    print(f"raw answers written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
