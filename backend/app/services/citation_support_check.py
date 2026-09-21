"""Jev (TypeSafe System One) citation support check: does the cited passage
actually support the sentence it is attached to?

Injectable seam in the style of ScopeGuard (scope_guard.py) — api key,
endpoint, model are constructor args so tests can swap in a fake transport
instead of hitting the network.

Scoped narrowly: CitationGuardrail.verify_citations (guardrail.py) has two
branches — a citation whose ID exists but wasn't retrieved this turn
([Unverified]), and one whose ID doesn't exist at all ([Hallucinated]).
Neither branch is this module's business. This module extends the *third*
case: a citation whose ID was retrieved this turn, which guardrail.py leaves
completely untouched today because the exact-ID lookup that both branches
share has nothing left to check. Untouched doesn't mean unproblematic — the
ID being real and retrieved says nothing about whether the passage actually
backs the sentence it's attached to. That's a reading-comprehension
judgment, not a lookup, which is what this module asks Jev to make.

Not wired into the answer flow by default. AnswerComposer only builds one
when CITATION_SUPPORT_CHECK_ENABLED is set, so nothing changes for users
until then (#208).
"""

import re
from typing import Any

import httpx

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

# Mirrors the TypeSafe citation_check cookbook's three-way relation exactly
# (https://docs.typesafe.ai/cookbooks/citation_check) — supports/contradicts/
# says_nothing, not a binary yes/no, because "the passage is on-topic but
# never actually states the claim" is a real, distinct failure mode from
# "the passage says the opposite."
_RELATION_CRITERIA = {
    "supports": "The passage states the claim, or directly implies it is true.",
    "contradicts": "The passage states the opposite of the claim, or implies it is false.",
    "says_nothing": "The passage does not address the claim, either way.",
}

# Same pattern CitationGuardrail.citation_pattern uses (guardrail.py). This
# module only ever looks at text guardrail has already produced, and only
# cares about the single-ID brackets guardrail's own regex recognizes as a
# citation — a multi-ID bracket ("[DN 1:1, MN 1:1]") already sails past
# guardrail's exact-ID check unexamined, so it's out of scope here too.
_CITATION_RE = re.compile(r"\[([A-Z\s]+ [\d.]+:\d+)\]")

_SENTENCE_END_RE = re.compile(r"[.!?]\s+")

# Appended inside the bracket, after the ID, so the citation stays exactly
# byte-for-byte clickable — frontend/components/deep-dive/AnswerText.tsx
# strips it back off before handing the ref to onCitationClick. Chosen to
# use only whitespace and letters so it can never be mistaken for one of the
# comma-separated multi-citation refs that component already splits on.
UNSUPPORTED_MARKER = " unsupported"


class CitationSupportCheckError(RuntimeError):
    """Jev call failed, timed out, or returned an unparseable response.

    Raised rather than swallowed — this module takes no position on whether
    a failure should publish the citation unmarked or flag it. The caller
    decides (answer_composer.py). ScopeGuard fails open on this same kind of
    error, but that choice doesn't transfer here without re-checking it:
    failing open there means letting a maybe-off-topic question through,
    which the module's own docstring already calls the cheaper mistake.
    Failing open here means publishing a citation this check could not
    judge — see answer_composer.py's _check_citation_support for the
    reasoning (#208).
    """


class CitationSupportCheck:
    """Asks Jev whether each cited passage supports the sentence it's
    attached to.

    2-5 citations from one answer are independent judgments over the same
    kind of question, so check() sends them as one batched request — one
    Choice question per citation, evaluated in parallel by TypeSafe — rather
    than one round trip per citation (#208).
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str = ENDPOINT,
        model: str = MODEL,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def check(self, citations: list[dict[str, str]]) -> list[str]:
        """citations: ordered [{"claim": <sentence>, "passage": <passage text>}, ...].

        Returns the winning relation ("supports" | "contradicts" |
        "says_nothing") for each citation, in the same order.
        """
        if not citations:
            return []
        state = {"citations": [{"claim": c["claim"], "passage": c["passage"]} for c in citations]}
        questions = {
            f"c{i}": {
                "type": "choice",
                "instructions": (
                    f"How does the passage in `citations[{i}].passage` relate to "
                    f"the claim in `citations[{i}].claim`?"
                ),
                "criteria": _RELATION_CRITERIA,
            }
            for i in range(len(citations))
        }
        try:
            resp = await self._client.post(
                self._endpoint,
                json={"state": state, "model": self._model, "questions": questions},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            payload = resp.json()
            return [payload["answers"][f"c{i}"]["choice"] for i in range(len(citations))]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise CitationSupportCheckError(str(exc)) from exc


def _claim_before(text: str, bracket_start: int) -> str:
    """The sentence a citation bracket is attached to: text back to the
    previous sentence boundary, or the start of the paragraph/bullet.

    Matches the system prompt's citation contract (search_pipeline.py
    _SYSTEM_PROMPT): "insert the citation ID in square brackets directly
    after the sentence."
    """
    preceding = text[:bracket_start]
    boundary = 0
    for m in _SENTENCE_END_RE.finditer(preceding):
        boundary = m.end()
    return preceding[boundary:].strip().lstrip("*-• ")


def find_checkable_citations(
    text: str, retrieved_ids: set[str], passage_by_id: dict[str, str]
) -> list[dict[str, Any]]:
    """Every citation bracket in `text` whose ID was retrieved this turn (the
    CitationGuardrail branch this check extends) and whose passage text is
    available — i.e. exactly the citations guardrail.py leaves untouched.

    Each entry carries the bracket's (start, end) span so the result can be
    spliced back into this same text later, and is returned in the order the
    citations appear, since that's also the order sent to CitationSupportCheck.
    """
    found = []
    for m in _CITATION_RE.finditer(text):
        cid = m.group(1)
        if cid not in retrieved_ids or cid not in passage_by_id:
            continue
        found.append({
            "id": cid,
            "claim": _claim_before(text, m.start()),
            "passage": passage_by_id[cid],
            "start": m.start(),
            "end": m.end(),
        })
    return found


def mark_unsupported(
    text: str, citations: list[dict[str, Any]], relations: list[str]
) -> str:
    """Splice UNSUPPORTED_MARKER inside every bracket whose relation isn't
    "supports" — "[DN 15:3]" -> "[DN 15:3 unsupported]" — leaving the ID
    itself untouched so the citation stays genuinely clickable, per #207's
    amber tag. `contradicts` and `says_nothing` get the same marker: #207
    settled on one amber tag for both, not two.
    """
    flagged_ends = sorted(
        c["end"] for c, relation in zip(citations, relations) if relation != "supports"
    )
    if not flagged_ends:
        return text
    out = []
    last = 0
    for end in flagged_ends:
        out.append(text[last:end - 1])  # up to, but not including, the closing "]"
        out.append(UNSUPPORTED_MARKER)
        out.append("]")
        last = end
    out.append(text[last:])
    return "".join(out)
