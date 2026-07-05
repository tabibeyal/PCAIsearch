# ADR-0006: Guardrail as Sole Citation Authority

**Status:** Accepted
**Date:** 2026-07-05

## Context

`SearchPipeline.synthesize`/`stream_synthesize` call `_strip_orphan_citations` on the LLM's raw output before returning, silently deleting any citation whose ID isn't in the retrieved context. `CitationGuardrail.process_response` then runs on that already-cleaned text, checking citations against the same retrieved-ID set `_strip_orphan_citations` already enforced. Every citation that reaches the Guardrail is therefore guaranteed valid — its `[Hallucinated]`/`[Unverified]` marker logic (`guardrail.py`) never fires. `hallucinations` and `canonical_misses` are structurally always empty; `is_faithful` is always `True`.

This isn't hypothetical: `tests/backend/test_e2e_pipeline.py::test_e2e_guardrail_catches_hallucinated_citation` already asserts the behavior this shadowing prevents, and is currently failing. It went unnoticed because e2e tests need live models and are skipped in normal runs.

## Decision

Remove `_strip_orphan_citations` from the pipeline. The Guardrail becomes the sole authority on citation validity: invalid citations are marked visibly in the answer text (`[Hallucinated]`, `[Unverified]`) instead of being silently deleted before the Guardrail ever sees them.

## Why

The project's core principle is accuracy over creativity — every answer must cite real passages. Silently deleting a bad citation leaves a sentence reading as clean, ungrounded prose with no signal that the model tried to claim something unsupported. A visible marker is the more honest failure mode. It's also not new complexity: `CitationGuardrail._replace` and the frontend's `AnswerText.renderCitation` "cannot verify" badge were already built for exactly this — both sides have been dead code since the pipeline's stripping made them unreachable. This change un-shadows existing behavior rather than adding any.

## Alternatives Considered

**Keep silent stripping, demote Guardrail to metrics-only:** Preserves today's "clean" answer text, but a reader would have no way to know a claim was ungrounded. Rejected — contradicts accuracy-over-creativity.

## Consequences

- User-visible UX change: some answers will now show `[Unverified]`/`[Hallucinated]` markers where today the citation is silently removed. Owner-approved 2026-07-05.
- `is_faithful`/`hallucinations`/`canonical_misses` become meaningful signals instead of structurally-vacuous ones — relevant to Gap Detector categories like "Made-up citation."
- Acceptance check: `test_e2e_guardrail_catches_hallucinated_citation` goes from red to green.
- Stream contract: in `/stream`, the Guardrail pass (and any marker substitution) happens only on the final `done` event — chunks streamed before it are raw, unverified LLM output. The frontend must treat `done.answer` as authoritative; if an `error` event follows instead, partial chunk text must be discarded, not trusted. `SynthesisLoader.tsx`'s `streamReducer` already conforms (chunk text is discarded once `done` arrives).
