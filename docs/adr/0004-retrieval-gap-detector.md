# ADR-0004: Retrieval Gap Detector

**Status:** Accepted
**Date:** 2026-07-03

## Context

Retrieval gaps — queries where the pipeline fails to surface a relevant sutta/passage — have so far been found only when the owner happens to notice a bad answer (e.g. commit 0ba8b6f, the AN 7.63:23 gatekeeper simile fix). This is manual and unsystematic; a gap in an infrequently-asked corner of the corpus can sit unfixed indefinitely. We want a tool that surfaces candidate gaps proactively instead of waiting for the owner to stumble on one.

The `feedback` table (Supabase in production, SQLite locally) already captures `query, answer, rating, category, comment` from the thumbs-up/down widget. It does **not** capture what the pipeline actually retrieved for that query — only the synthesized answer.

## Decision

Build a **Gap Detector**: a daily scheduled Claude Code cloud agent that:

1. Queries `feedback` for `rating='down'` AND `category IN ('Not relevant to my question', 'Missing important nuance')` AND `gap_issue_url IS NULL`. The other three down-vote categories (doctrinally inaccurate, sources don't support the answer, too vague) point at synthesis/guardrail problems, not retrieval, and are excluded to avoid false positives.
2. For each candidate row, re-runs the query live through `SearchPipeline.search()` to capture the current top retrieval candidates as diagnostic context — the feedback table has no other record of what was retrieved.
3. Searches open GitHub issues for the same query text first. If one exists, comments on it instead of filing a duplicate. Otherwise files a new issue labeled `needs-triage`, containing query, answer, category, comment, and the live candidate list.
4. Caps the number of new issues filed per run, so an initial backlog (or a future spike of down-votes) trickles in rather than flooding the tracker in one run.
5. Sets `gap_issue_url` on the feedback row in both the "filed" and "commented on existing issue" cases, so the row is never reprocessed.

Issues are filed as `needs-triage`, not `ready-for-agent` — a down-vote is a hint, not a confirmed diagnosis. A human (or a later triage pass) decides whether it's really a dictionary-fixable retrieval gap before an agent attempts the well-established fix pattern (add a `pali_dictionary` entry with keywords/pali/english_hint, plus a test).

## Alternatives Considered

**Recall@10 benchmark regressions as the trigger:** Rejected as the sole signal — the benchmark only covers its fixed 15-query set, so it can't catch gaps on novel queries real users actually ask. It remains a separate, complementary check.

**File with feedback-row data only, no live pipeline re-run:** Simpler and avoids a live pipeline call per candidate, but leaves every triage starting from scratch — the human/agent would have to re-run the query themselves to see what was retrieved. Rejected because the diagnostic value of showing the actual candidate set outweighs the extra call.

**GitHub Actions scheduled workflow instead of a Claude Code cloud agent:** Would keep execution inside the repo's own CI, but requires provisioning Supabase/NVIDIA/Qdrant secrets in Actions from scratch. Rejected in favor of reusing the `/schedule` skill's existing cloud-agent infrastructure.

**Separate watermark instead of a `gap_issue_url` column:** A last-processed timestamp/id would avoid a schema change, but state would live apart from the data it describes and could drift or get lost across differently-scheduled runs. Rejected in favor of a nullable column on `feedback` itself.

## Consequences

- Requires a new nullable `gap_issue_url` column on the Supabase `feedback` table.
- Requires `NVIDIA_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and Supabase credentials to be provisioned in the scheduled agent's environment — not yet done as of this ADR.
- Couples gap detection to the existing GitHub issue tracker and `needs-triage` triage-label convention (`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`).
- Every flagged candidate costs one live `SearchPipeline.search()` call (NVIDIA + Qdrant round-trip) at detection time, on top of whatever the original user query already cost.
