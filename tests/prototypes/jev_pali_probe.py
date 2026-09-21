"""Throwaway probe: does Jev (TypeSafe System One) cope with our subject matter?

Answers wayfinder ticket "Does Jev understand Buddhist and Pali text at all?" (#196).
Not a pytest test: it makes paid network calls. Run it by hand.

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
      && PYTHONPATH=. python3 tests/prototypes/jev_pali_probe.py

Three probes, all against cases whose right answer we already know:
  A  scope guard   - Noul "is this question about the Pali Canon?" on on- and off-topic asks
  B  Pali terms    - Noul on real corpus passages whose hinge word is an untranslated Pali term
  C  reranking     - Noul + Score over a gold passage plus keyword-plausible decoys
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
DUMPS = Path(__file__).resolve().parents[2] / "data" / "dumps"

usage_totals = {"input_tokens": 0, "output_tokens": 0, "requests": 0}


def load_key():
    """TYPESAFE_API_KEY from the environment, else from the nearest .env above us."""
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
    sys.exit("TYPESAFE_API_KEY is not set and no .env above this file defines it.")


def ask(state, questions):
    body = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {load_key()}",
            "Content-Type": "application/json",
        },
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    elapsed = time.monotonic() - started
    usage = payload.get("usage", {})
    usage_totals["input_tokens"] += usage.get("input_tokens", 0)
    usage_totals["output_tokens"] += usage.get("output_tokens", 0)
    usage_totals["requests"] += 1
    return payload["answers"], elapsed


def verse(sutta_id, number):
    """Pull one real passage out of the local Thanissaro dumps."""
    data = json.loads((DUMPS / f"{sutta_id.lower().replace(' ', '')}.json").read_text())
    for v in data["verses"]:
        if v["number"] == number:
            return v["english"]
    raise KeyError(f"{sutta_id}:{number}")


# --- Probe A: is this question in scope for a Pali Canon search engine? ---------

SCOPE_QUESTION = {
    "type": "noul",
    "instructions": (
        "Is this user question asking about the teachings, stories or monastic rules "
        "of early Buddhism as recorded in the Pali Canon (the discourses of the "
        "Buddha collected in the Digha, Majjhima, Samyutta, Anguttara and Khuddaka "
        "Nikayas)?"
    ),
    "criteria": {
        "true": (
            "A search over the Pali Canon could answer it, even if the wording uses "
            "no Buddhist vocabulary at all."
        ),
        "false": (
            "Nothing in the Pali Canon answers it. This includes other religions' "
            "scriptures, later Buddhist traditions such as Tibetan or Zen, and "
            "everyday questions unrelated to the Buddha's teaching."
        ),
    },
}

SCOPE_CASES = [
    ("what did the Buddha say about anger", True, "plain on-topic"),
    ("what were the Buddha's last words before he died", True, "on-topic, narrative"),
    ("is having a good spiritual friend the whole of the holy life", True,
     "on-topic with zero Buddhist marker words"),
    ("why does loving someone lead to grief and suffering", True,
     "on-topic, reads like a self-help question"),
    ("how should one breathe mindfully during sitting meditation", True, "on-topic"),
    ("what is anatta", True, "on-topic, bare Pali term"),
    ("what is the best way to cook rice", False, "plainly off-topic"),
    ("write me a python function that reverses a list", False, "plainly off-topic"),
    ("how do I cancel my Netflix subscription", False, "plainly off-topic"),
    ("what does the Bible say about forgiveness", False,
     "near miss: scripture, wrong canon"),
    ("what does the Dalai Lama teach about compassion", False,
     "near miss: Buddhist, but not the Pali Canon"),
    ("which meditation app should I install", False,
     "near miss: meditation, but not the Canon"),
]


def probe_a():
    print("\n=== PROBE A - scope guard (Noul: is this about the Pali Canon?) ===")
    print(f"{'noul':>6}  {'want':>5}  {'ok':>3}  question")
    rows = []
    for text, expected, note in SCOPE_CASES:
        answers, secs = ask(text, {"in_scope": SCOPE_QUESTION})
        noul = answers["in_scope"]["noul"]
        got = noul >= 0.5
        ok = "yes" if got == expected else "NO"
        print(f"{noul:6.2f}  {str(expected):>5}  {ok:>3}  {text}   [{note}]")
        rows.append({"case": text, "note": note, "expected": expected,
                     "noul": noul, "correct": got == expected, "seconds": secs})
    right = sum(r["correct"] for r in rows)
    print(f"--> {right}/{len(rows)} correct at a 0.5 cut")
    return rows


# --- Probe B: passages whose hinge word is an untranslated Pali term ------------

PALI_CASES = [
    ("DN9", 18, "jhāna",
     "Does this passage describe entering a state of deep meditative absorption?", True),
    ("AN10.17", 4, "Pāṭimokkha",
     "Is this passage about the code of monastic rules that a monk keeps?", True),
    ("AN3.101", 3, "kamma",
     "Is this passage about how a person's intentional actions produce results they "
     "later experience?", True),
    ("AN10.15", 3, "Tathāgata",
     "Does this passage say that the Buddha is the foremost of all beings?", True),
    ("THIG9", 6, "saṁvega",
     "Does the speaker describe a shock or urgency that drove them to practise?", True),
    ("AN1.140", 3, "(control - no Pali hinge)",
     "Does this passage describe entering a state of deep meditative absorption?", False),
]


def probe_b():
    print("\n=== PROBE B - untranslated Pali terms inside English passages ===")
    print(f"{'noul':>6}  {'want':>5}  {'ok':>3}  passage / hinge word")
    rows = []
    for sutta, number, hinge, question, expected in PALI_CASES:
        text = verse(sutta, number)
        answers, secs = ask(
            text, {"holds": {"type": "noul", "instructions": question}}
        )
        noul = answers["holds"]["noul"]
        got = noul >= 0.5
        ok = "yes" if got == expected else "NO"
        print(f"{noul:6.2f}  {str(expected):>5}  {ok:>3}  {sutta}:{number}  hinge={hinge}")
        rows.append({"passage": f"{sutta}:{number}", "hinge": hinge,
                     "question": question, "expected": expected, "noul": noul,
                     "correct": got == expected, "seconds": secs})
    right = sum(r["correct"] for r in rows)
    print(f"--> {right}/{len(rows)} correct at a 0.5 cut")
    return rows


# --- Probe C: reranking a gold passage against keyword-plausible decoys ---------

RERANK_QUESTION = {
    "type": "noul",
    "instructions": {
        "question": "Does the passage in `candidate` directly answer the user's `query`?",
    },
    "criteria": {
        "true": "The passage states the answer the query is looking for.",
        "false": "The passage is merely on a related topic, or repeats similar wording "
                 "without answering the query.",
    },
}

RERANK_SCORE = {
    "type": "score",
    "instructions": {
        "question": "How well does the passage in `candidate` answer the user's `query`?",
    },
    "criteria": [
        "Unrelated to the query.",
        "Same general subject, but does not address what was asked.",
        "Touches on the answer but leaves the key point implicit or partial.",
        "States the answer the query is asking for.",
    ],
}

RERANK_CASES = [
    {
        "query": "what is the one precept you should never break",
        "gold": ("MN61", 7),
        "decoys": [("AN10.71", 7), ("AN10.17", 4), ("AN2.35", 7), ("DN9", 18)],
        "note": "the cross-encoder needs a Pali-dictionary hint to get this one",
    },
    {
        "query": "how do I reach a state of deep meditative absorption",
        "gold": ("DN9", 18),
        "decoys": [("MN61", 7), ("AN10.71", 6), ("AN2.35", 7), ("AN3.101", 3)],
        "note": "answer hinges on the word jhāna, which the query never says",
    },
]


def probe_c():
    print("\n=== PROBE C - reranking a gold passage against plausible decoys ===")
    rows = []
    for case in RERANK_CASES:
        print(f"\nquery: {case['query']}")
        print(f"note:  {case['note']}")
        scored = []
        for sutta, number in [case["gold"], *case["decoys"]]:
            state = {"query": case["query"], "candidate": verse(sutta, number)}
            answers, secs = ask(
                state, {"answers_it": RERANK_QUESTION, "how_well": RERANK_SCORE}
            )
            scored.append({
                "passage": f"{sutta}:{number}",
                "is_gold": (sutta, number) == case["gold"],
                "noul": answers["answers_it"]["noul"],
                "score": answers["how_well"]["score"],
                "score_confidence": answers["how_well"]["confidence"],
                "seconds": secs,
            })
        scored.sort(key=lambda r: r["noul"], reverse=True)
        print(f"  {'noul':>6}  {'score':>6}  {'conf':>5}  passage")
        for r in scored:
            mark = " <- gold" if r["is_gold"] else ""
            print(f"  {r['noul']:6.2f}  {r['score']:6.2f}  "
                  f"{r['score_confidence']:5.2f}  {r['passage']}{mark}")
        rank = next(i for i, r in enumerate(scored, 1) if r["is_gold"])
        print(f"  --> gold ranked #{rank} of {len(scored)} by noul")
        rows.append({"query": case["query"], "note": case["note"],
                     "gold_rank_by_noul": rank, "candidates": scored})
    return rows


def main():
    load_key()
    started = time.monotonic()
    results = {"scope": probe_a(), "pali_terms": probe_b(), "rerank": probe_c()}
    results["usage"] = dict(usage_totals)
    wall = time.monotonic() - started

    cost = usage_totals["input_tokens"] / 1_000_000 * 0.042
    print("\n=== cost and speed ===")
    print(f"requests: {usage_totals['requests']}  "
          f"input tokens: {usage_totals['input_tokens']}  "
          f"output tokens: {usage_totals['output_tokens']}")
    print(f"estimated cost: ${cost:.5f}   wall clock: {wall:.1f}s")

    out = Path(__file__).with_suffix(".results.json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"raw answers written to {out}")


if __name__ == "__main__":
    main()
