# ADR-0005: Shared Answer Permalinks via Signed Receipt

**Status:** Accepted
**Date:** 2026-07-04

## Context

We're adding a "Share" button under the synthesized answer. It needs to hand the visitor a permalink that replays the exact answer (text + citations) the sharer saw — not a link that re-runs the query live, since LLM synthesis is non-deterministic and a fresh run could produce different text.

That means persisting a snapshot server-side. The snapshot is created by a new public endpoint, `POST /share`, triggered only when a user clicks Share (not on every synthesis call, to avoid storing 100% of traffic for a feature most queries never use).

A public write endpoint that stores arbitrary text forever and serves it back at a stable URL is, structurally, an anonymous pastebin. If `/share` accepts whatever `query`/`answer`/`context` the client POSTs, anyone can script requests directly at the endpoint (bypassing the UI) to store and host arbitrary spam/phishing text permanently under our domain.

## Decision

`/synthesize` (and the terminal payload of the streaming endpoint) returns a **signed receipt** alongside the answer: an HMAC computed server-side over `(query, answer, context)` using a server-held secret. The frontend must echo this receipt back unchanged when calling `POST /share`. The server recomputes the HMAC over the submitted payload and rejects the request if it doesn't match, before persisting anything.

This is stateless — no session, no server-side cache of in-flight answers, no second LLM call — and it structurally guarantees that anything persisted to the `shared_answers` table is byte-identical to something the pipeline actually generated for that query.

Snapshots are stored in a new Supabase table (same project as `feedback`, same env-var fallback to local SQLite in dev) and kept forever — no expiry, no cleanup job. A `/share/{id}` route renders the frozen answer read-only (clickable citations from the stored context, no live API calls, no `FeedbackBar`, no "try it live" CTA).

No rate limiting on `/share` for now: creating a valid receipt requires a real prior synthesis call, which is itself bottlenecked by the upstream NVIDIA free-tier 40rpm cap. Abuse would have to first pay that cost.

## Alternatives Considered

**Trust the client payload as-is:** Simplest, but anyone hitting `/share` directly (not through the UI) could store and permanently host arbitrary text under our domain. Rejected — this is a real, cheap-to-exploit hole for a public app.

**Re-run the pipeline server-side and compare to the submitted text:** Would prove the answer came from a real query, without needing a signing secret. Rejected because synthesis is non-deterministic — a fresh run for the same query can legitimately produce different text, so an exact-match comparison would spuriously reject valid shares.

**Session/request-ID based validation (server holds the last N answers in memory or a short-lived cache, share call references the ID):** Avoids needing a secret, but adds server-side state and a TTL/eviction policy to get right, for no real benefit over a stateless signature. Rejected in favor of the simpler signed-receipt approach.

**Expiring snapshots (e.g. 90-day TTL):** Bounds storage growth, but shared links would go dead, raising an unresolved question of what a dead link should show a visitor. Rejected for now given expected low traffic volume; revisit if storage becomes a real cost.

## Consequences

- Requires a new signing secret (e.g. `SHARE_RECEIPT_SECRET`) provisioned as a DigitalOcean App Platform secret — not yet done as of this ADR.
- Requires a new Supabase table (`shared_answers` or similar: id, query, answer, context, created_at) with the same production/local-SQLite fallback pattern as `feedback`.
- `SynthesisResponse` gains a `receipt` field; the frontend must round-trip it verbatim to `/share`, and it must survive the streaming endpoint's incremental-then-final payload shape unchanged.
- Every synthesized answer now needs a title attached to each `context`/`SearchResult` item (via the existing `SuttaTitleIndex.get_title_text()`) so the copy-button feature can render `[ID:Verse — Sutta Title]` — a related but separate small backend change bundled into the same work.
- Storage grows unbounded with no expiry; acceptable at current traffic levels but not revisited automatically.
