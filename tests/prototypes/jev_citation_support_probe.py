"""Throwaway probe: does the live citation support check (#208) flag good
citations by mistake?

Calls the real CitationSupportCheck.check() (backend/app/services/
citation_support_check.py) against real Thanissaro passages from
data/dumps, so the probe exercises exactly the code that would ship, not a
hand-rolled copy of it. Not a pytest test: it makes paid network calls.

    cd ~/PCAIsearch && set -a && . ./.env && set +a \
      && PYTHONPATH=. python3 tests/prototypes/jev_citation_support_probe.py

Two probes:
  A  false-flag rate  - GOOD_CASES: real (claim, passage) pairs where the
     claim genuinely IS supported by the passage. Every relation that comes
     back as anything other than "supports" is a false flag — the number
     that decides whether #208 should ship, because a false amber on a good
     citation is worse than a missed bad one (#199, #207).
  B  sanity controls   - BAD_CASES: pairs deliberately mismatched (wrong
     claim for the passage), so a check that always said "supports" would
     still pass probe A with a perfect score. Probe B catches that: it
     should mostly NOT say "supports".
  C  batching latency  - the same 5 citations sent as 1 batched call vs. as
     5 separate single-citation calls, measuring real wall-clock added
     latency against the ~0.85s/call baseline from #196.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev_pali_probe import load_key, verse  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.services.citation_support_check import CitationSupportCheck  # noqa: E402

# --- Probe A: real (claim, passage) pairs where the claim is genuinely supported ---

GOOD_CASES = [
    ("DN9", 18, "The monk sets aside sensual desire and unskillful states, then enters "
     "a state of rapture and pleasure born of that withdrawal.",
     "direct paraphrase, no jhāna word"),
    ("AN10.17", 4, "A virtuous monk lives by the code of monastic training rules, "
     "careful even about minor faults.",
     "direct paraphrase, no Pāṭimokkha word"),
    ("AN3.101", 3, "One who holds that the result of an action is shaped by how the "
     "deed was done can live the holy life and end suffering.",
     "indirect: the passage states this as one side of a contrast"),
    ("AN10.15", 3, "Heedfulness is said to be the root and the highest of every "
     "skillful quality.",
     "direct restatement of the passage's second half"),
    ("THIG9", 6, "The speaker was startled into urgent spiritual effort by words "
     "from their mother.",
     "paraphrase of saṁvega, Pali hinge word untranslated in source"),
    ("MN61", 7, "Telling a deliberate lie without any shame shows someone is "
     "barely a contemplative at all.",
     "near-verbatim restatement"),
    ("AN10.71", 6, "Monks are instructed to keep their conduct impeccable under "
     "the code of monastic rules, mindful of even trivial faults.",
     "direct paraphrase, no Pāṭimokkha word"),
    ("AN2.35", 7, "A monk who keeps the precepts carefully but is reborn among "
     "the devas, then returns to this world, is called one 'fettered inside.'",
     "long passage, claim covers its whole arc"),
    ("DHP1", 3, "An unwholesome state of mind brings suffering the way a cart "
     "wheel follows the ox that pulls it.",
     "short verse, simile-heavy"),
    ("DHP1", 4, "A calm and bright state of mind is followed by happiness, the "
     "way a shadow never leaves its owner.",
     "short verse, simile-heavy"),
    ("MN10", 12, "In the first stage of this practice, a monk stays mindfully "
     "aware of the body, working to set aside craving and aversion toward "
     "the world.",
     "single-sentence list-style passage (project's known weak chunk type)"),
    ("SN1.2", 3, "A deity radiant enough to light up the entire grove approached "
     "the Buddha at night and asked him about liberation.",
     "narrative passage, claim covers the frame story not the teaching"),
]

# --- Probe B: deliberately mismatched claim/passage pairs (bad-citation controls) ---

BAD_CASES = [
    ("DN9", 18, "The monk breaks the precept against killing.",
     "unrelated claim, same passage"),
    ("MN61", 7, "The Buddha praised lying as a skillful quality.",
     "states the opposite of the passage"),
    ("AN10.15", 3, "The best way to cook rice is to steam it slowly.",
     "wholly unrelated claim"),
    ("THIG9", 6, "Jhāna is the ultimate goal described in this passage.",
     "topically adjacent (meditation), but the passage never says this"),
    ("DHP1", 3, "A pure heart leads to happiness.",
     "true of the very next verse (DHP1:4), not this one — same source, wrong verse"),
    ("AN2.35", 7, "This passage describes someone who has fully ended the "
     "cycle of rebirth.",
     "related vocabulary (rebirth), wrong outcome: a returner, not an arahant"),
]


def _pair(sutta, number, claim):
    return {"claim": claim, "passage": verse(sutta, number)}


async def probe_a(checker):
    print("\n=== PROBE A — false-flag rate on genuinely-supported citations ===")
    citations = [_pair(s, n, c) for s, n, c, _ in GOOD_CASES]
    started = time.monotonic()
    relations = await checker.check(citations)
    elapsed = time.monotonic() - started
    rows = []
    false_flags = 0
    for (sutta, number, claim, note), relation in zip(GOOD_CASES, relations):
        flagged = relation != "supports"
        false_flags += flagged
        mark = "FALSE FLAG" if flagged else "ok"
        print(f"  {mark:>10}  {relation:>12}  {sutta}:{number}  [{note}]")
        rows.append({"passage": f"{sutta}:{number}", "claim": claim, "note": note,
                      "relation": relation, "false_flag": flagged})
    rate = false_flags / len(GOOD_CASES)
    print(f"--> {false_flags}/{len(GOOD_CASES)} false flags ({rate:.0%}) in one {elapsed:.2f}s batched call")
    return rows, rate


async def probe_b(checker):
    print("\n=== PROBE B — sanity controls (mismatched claim/passage pairs) ===")
    citations = [_pair(s, n, c) for s, n, c, _ in BAD_CASES]
    relations = await checker.check(citations)
    rows = []
    caught = 0
    for (sutta, number, claim, note), relation in zip(BAD_CASES, relations):
        is_caught = relation != "supports"
        caught += is_caught
        mark = "caught" if is_caught else "MISSED"
        print(f"  {mark:>7}  {relation:>12}  {sutta}:{number}  [{note}]")
        rows.append({"passage": f"{sutta}:{number}", "claim": claim, "note": note,
                      "relation": relation, "caught": is_caught})
    print(f"--> {caught}/{len(BAD_CASES)} mismatches correctly not marked 'supports'")
    return rows


async def probe_c(checker):
    print("\n=== PROBE C — batching latency: 1 call for 5 vs. 5 separate calls ===")
    subset = GOOD_CASES[:5]
    citations = [_pair(s, n, c) for s, n, c, _ in subset]

    started = time.monotonic()
    await checker.check(citations)
    batched_elapsed = time.monotonic() - started
    print(f"  batched:    1 call, {len(citations)} citations, {batched_elapsed:.2f}s total "
          f"({batched_elapsed / len(citations):.2f}s/citation)")

    started = time.monotonic()
    for c in citations:
        await checker.check([c])
    sequential_elapsed = time.monotonic() - started
    print(f"  sequential: {len(citations)} calls, {sequential_elapsed:.2f}s total "
          f"({sequential_elapsed / len(citations):.2f}s/citation)")
    print(f"  --> baseline from #196 was ~0.85s/call; batching saves "
          f"{sequential_elapsed - batched_elapsed:.2f}s over {len(citations)} citations")
    return {"batched_seconds": batched_elapsed, "sequential_seconds": sequential_elapsed,
            "n_citations": len(citations)}


async def main():
    checker = CitationSupportCheck(api_key=load_key())
    a_rows, false_flag_rate = await probe_a(checker)
    b_rows = await probe_b(checker)
    c_result = await probe_c(checker)

    print("\n=== summary ===")
    print(f"false-flag rate on {len(GOOD_CASES)} known-good citations: {false_flag_rate:.0%}")

    out = Path(__file__).with_suffix(".results.json")
    out.write_text(json.dumps({
        "false_flag_rate": false_flag_rate,
        "good_cases": a_rows,
        "bad_case_controls": b_rows,
        "batching_latency": c_result,
    }, indent=2, ensure_ascii=False))
    print(f"raw answers written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
