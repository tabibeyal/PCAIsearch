---
name: jev-decisions
description: Route wayfinder's recurring judgment calls (ticket type, fog vs ticket, next ticket, is-it-resolved, risk gate) through Jev typed questions instead of free-text reasoning. Use whenever wayfinder or you are about to make one of these five decisions on a PCAIsearch GitHub issue.
---

# Jev decisions

PCAIsearch ("Ask the Pali Canon", FastAPI backend + Next.js frontend) runs its roadmap through wayfinder on GitHub issues. Five judgment calls come up again and again. Don't make them in free text. Ask Jev a typed question with `scripts/jev_decide.py`, read the `decision` field, and do what it says.

Jev returns calibrated probabilities. Your code (the gates in the script) decides whether to act. You don't override a gate because you feel sure.

## When to call Jev

Call it when you are about to:

1. **Classify a ticket** - decide which wayfinder label a new or unlabeled issue gets.
2. **Decide fog or ticket** - decide whether something from a conversation or a note becomes an issue.
3. **Pick the next ticket** - choose which open frontier issue to work on.
4. **Decide if a ticket is resolved** - decide whether an issue can be closed.
5. **Gate risk** - decide whether a change is safe to make without asking the human.

Don't call it for anything else. Implementation, code review, writing, and debugging stay with you.

## How to call it

```bash
python3 scripts/jev_decide.py <decision-point> \
  --destination "<current wayfinder:map destination>" \
  --notes "<short relevant notes>" \
  --closed-decision "<one closed decision>"  # repeat for each
  [point-specific flags, see below]
```

Or pipe a full state object on stdin with `--state -` (see `--help`).

Always pass the map destination and the closed decisions that touch the subject. Jev only knows what is in the state. Thin state gives confident wrong answers.

The script prints JSON. Read these fields:

- `decision`: `act`, `ask_human`, or `fall_back_to_default`
- `value`: the answer to use when `decision` is `act`
- `reason`: why the gate passed or failed
- `pair_with`: extra skill to load (see grilling below)

Exit codes match: `0` act, `10` ask_human, `20` fall_back_to_default, `2` usage error.

What to do with each decision:

- `act`: use `value`. Don't second-guess it.
- `ask_human`: stop and ask Eyal. Show him the question, Jev's top answer, and the probabilities.
- `fall_back_to_default`: use the default listed for that decision point below. Say in your output that you fell back and why.

## The five decision points

### 1. `classify` - ticket type

- Type: Choice over `research`, `prototype`, `grilling`, `task`, with the same meanings as wayfinder's Ticket Types. `task` means manual work with nothing to decide (moving data, signing up, provisioning access), not building a feature.
- Flags: `--ticket "<title and body>"`
- Gate: act if confidence >= 0.70
- Default: `grilling`, wayfinder's usual case. On low confidence or an error, the script returns `fall_back_to_default` with `value: "grilling"`.
- Apply the matching `wayfinder:<type>` label on `act` and on `fall_back_to_default`.

**Grilling tickets always pair with domain-modeling.** When the value is `grilling`, whether Jev picked it or it is the fallback, the script sets `pair_with: "domain-modeling"`. Load the domain-modeling skill before you start the grilling session, and keep its glossary open while you question. This rule is code, not a Jev question. Never ask Jev whether to pair.

### 2. `fog` - fog or ticket

- Type: Choice over `ticket`, `fog`, `already-a-ticket`, `already-decided`, `out-of-scope`
- The test is wayfinder's: can the question be stated precisely now? Not: can someone work on it now. A sharp question that is blocked is still a `ticket`.
- Flags: `--question "<the idea, request, or open question>"` and `--open-ticket "#<id> <title>"` for every open ticket on the map (repeat). Without the open tickets, Jev cannot see duplicates.
- Gate: act if confidence >= 0.70
- Default: `fog` (write it into the map's Fog section, don't open an issue)
- On `already-a-ticket`: add anything new to that issue as a comment instead of opening another one.
- On `already-decided`: link the closed decision instead of opening an issue.
- On `out-of-scope`: drop it and mention it once in your summary.

### 3. `next` - pick next ticket

- Type: Choice over the frontier issue ids, injected at call time
- Flags: `--frontier "<id>=<title / one-line summary>"` (repeat), or a `frontier` array in the stdin state. The array can be `gh issue list --json number,title,labels` output as-is.
- Gate: act if confidence >= 0.60
- Default: the lowest issue number in the frontier

**Exclude `wayfinder:claimed` issues from the frontier.** Someone else is on them. Filter them out before you call. The script also drops any frontier entry whose `labels` include `wayfinder:claimed`, as a backstop. If the frontier is empty after filtering, the script returns `ask_human`.

With exactly one unclaimed issue, the script skips the API call and returns it.

### 4. `resolved` - is the ticket resolved

- Type: Noul
- Flags: `--ticket "<issue title, body, and acceptance criteria>"` and `--evidence "<what was done: PR, test output, notes>"`
- Bands: `noul >= 0.85` means resolved, `act` with `value: true` (close it). `noul < 0.15` means not resolved, `act` with `value: false` (keep working). Anything in between means `ask_human`.
- Noul has no confidence field. The bands do that job.
- Default on API failure: not resolved. Keep the issue open.

### 5. `risk` - risk gate

- Type: Score with 4 levels plus a Noul `contradicts_decision`
- Flags: `--change "<what you are about to do>"`
- Levels: 0 trivial and reversible, 1 local and easy to revert, 2 touches shared behavior (API contract, search ranking, index, data), 3 destructive, irreversible, or affects prod / secrets / canon data
- Gate: act only if score is 0 or 1, score confidence >= 0.80, and `contradicts_decision` < 0.15. Otherwise `ask_human`.
- Default on API failure: `ask_human`. The risk gate fails closed.

## Thresholds are starting guesses

Every number above (0.70, 0.60, 0.85 / 0.15, 0.80) is a first guess. They live in `questions.json` under each decision's `gate`. Change them there, not in this file or in the script. When Eyal overrides a result, note the case in the map so the thresholds can be tuned later.

## Failures

The script already retries twice, with a short wait, when Jev is rate-limited or overloaded. If `TYPESAFE_API_KEY` is missing, the network fails, the response is malformed, or the script hits any other error, it returns `fall_back_to_default` (or `ask_human` for the risk gate) with the error in `reason`. Don't retry in a loop. Fall back, say so, and move on.

## Model

`questions.json` uses `jev-latest`, an alias. The script prints the concrete model version Jev actually ran (for example `jev-1.13.0`) in `model`. Once results look right, pin that version in `questions.json` or set `JEV_MODEL`.
