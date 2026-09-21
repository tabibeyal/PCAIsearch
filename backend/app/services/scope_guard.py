"""Jev (TypeSafe System One) scope guard: is this query about the Pali Canon?

Injectable seam in the style of Retriever (retriever.py) — the pieces that
vary (api key, endpoint, model) are constructor arguments, so tests can swap
in a fake transport instead of hitting the network.

Wired into the answer flow by default since #217; set SCOPE_GUARD_ENABLED to
"false" to switch it off (main.py).
"""

import httpx

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

# Probe A ("Does Jev understand Buddhist and Pali text at all?", #196, PR
# #202): off-topic questions scored 0.00-0.03, on-topic 0.56-0.92 — a wide
# gap. No case observed has landed near this line; a question that did would
# read as in-scope, since letting an off-topic question through search is a
# cheaper mistake than blocking a real user's question.
IN_SCOPE_THRESHOLD = 0.5

# Same wording the out-of-scope block in _SYSTEM_PROMPT used
# (search_pipeline.py) — kept identical so the user-facing behavior doesn't
# change when the guard replaces it.
OUT_OF_SCOPE_MESSAGE = (
    "This question is outside the scope of this search engine, which covers "
    "the Pali Canon and Buddhist teachings."
)

_SCOPE_QUESTION = {
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


class ScopeGuardError(RuntimeError):
    """Jev call failed, timed out, or returned an unparseable response.

    Raised rather than swallowed — this module takes no position on whether
    a failure should let the question through or block it. The caller
    decides (answer_composer.py: fails open, #198).
    """


class ScopeGuard:
    """Asks Jev whether a query is in scope for a Pali Canon search engine."""

    def __init__(
        self,
        api_key: str,
        endpoint: str = ENDPOINT,
        model: str = MODEL,
        # The guard blocks the front of every search, before retrieval starts,
        # and the caller fails open (#198). An observed call takes ~0.85s, so
        # anything past 2s is a bad day at TypeSafe: giving up then costs one
        # unguarded search, while waiting costs every user the full delay
        # (#217).
        timeout: float = 2.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def is_in_scope(self, query: str) -> bool:
        try:
            resp = await self._client.post(
                self._endpoint,
                json={
                    "state": query,
                    "model": self._model,
                    "questions": {"in_scope": _SCOPE_QUESTION},
                },
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload["answers"]["in_scope"]["noul"] >= IN_SCOPE_THRESHOLD
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ScopeGuardError(str(exc)) from exc
