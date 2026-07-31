# User-Facing Notice for the Passages Tab Removal

We removed the Passages tab (the raw list-of-retrieved-passages view, replaced by the synthesized answer) without adding any explanatory messaging for users who land where it used to be — no banner, no one-time notice, nothing. Stale `?view=results` links just redirect silently to the synthesized answer (#147, PR #149).

## Why out of scope

An explanatory notice is owed to users who had an expectation the change violates. PCAIsearch has not launched publicly — there is no user base that ever relied on the Passages tab, so there's no one to explain the removal to. Building a dismissible banner or first-visit notice for a feature nobody outside the project actually used is effort spent on a UX problem that doesn't exist yet.

This reasoning is scoped to *this* removal, not a blanket policy against ever building migration messaging. If PCAIsearch goes public and a similarly disruptive UI removal happens afterward, that's a fresh decision — real users would have real expectations by then, and the tradeoff should be re-evaluated on its own terms rather than assumed closed by this entry.

## Prior requests

- #156 — "Is user-facing messaging owed for the Passages tab removal?"
