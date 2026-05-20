# Feedback Mechanism Design

**Date:** 2026-05-21  
**Status:** Approved

## Overview

A Claude.ai-style thumbs up / thumbs down feedback mechanism attached to every synthesis answer. The primary purpose is to let users flag when an answer feels doctrinally wrong, incomplete, or off-target — not analytics. Feedback is stored server-side in a SQLite database for later review.

---

## User Flow

1. After the synthesis answer finishes streaming, a "Was this helpful?" row appears below the answer text (above the answer body's bottom edge, separated by a thin divider).
2. Two buttons are shown: 👍 and 👎.
3. **Thumbs up:** clicking immediately registers a positive signal. The button turns active (dark brown fill, white icon). The label changes to "Thank you for your feedback." No panel opens.
4. **Thumbs down:** clicking highlights the 👎 button (dark brown fill) and opens a panel directly below the buttons containing:
   - A "What was the problem?" heading
   - Five selectable category chips (toggle, one at a time):
     - Doctrinally inaccurate
     - Missing important nuance
     - Not relevant to my question
     - Sources don't support the answer
     - Too vague
   - An optional free-text textarea ("Add a comment (optional)")
   - A send button with a paper airplane SVG icon (no text label)
5. After submitting, the panel collapses. The 👎 button stays highlighted (dimmed active state). The label changes to "Thank you for your feedback."
6. Once a rating is submitted, both buttons are disabled — no re-rating in the same session.

---

## Frontend

### New component: `FeedbackBar`

Location: `frontend/components/deep-dive/FeedbackBar.tsx`

Props:
- `query: string` — the search query that produced this answer
- `answer: string` — the full answer text (stored alongside feedback for context)

Internal state:
- `rating: 'up' | 'down' | null`
- `panelOpen: boolean`
- `selectedCategory: string | null`
- `comment: string`
- `submitted: boolean`

On submit, the component POSTs to `POST /feedback` with the payload described in the backend section. On success, sets `submitted: true` and collapses the panel.

### Integration point

`FeedbackBar` is rendered inside `SynthesisView.tsx`, below the answer text block, inside the scrollable content div. It only appears once `data` is available (i.e., streaming is complete).

`query` must be threaded down the component tree:
- `SynthesisLoader` already receives `query` — pass it to `DualPaneContainer` as a new prop
- `DualPaneContainer` passes it to `SynthesisView` as a new prop
- `SynthesisView` passes it to `FeedbackBar`

---

## Backend

### New endpoint: `POST /feedback`

Location: `backend/app/main.py`

Request body (JSON):
```
{
  "query": string,
  "answer": string,
  "rating": "up" | "down",
  "category": string | null,
  "comment": string | null
}
```

Response: `{"ok": true}` on success.

### Storage: SQLite

File: `feedback.db` at the repo root on the DigitalOcean server.

Table schema:
```sql
CREATE TABLE IF NOT EXISTS feedback (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  query     TEXT NOT NULL,
  answer    TEXT NOT NULL,
  rating    TEXT NOT NULL,
  category  TEXT,
  comment   TEXT,
  created_at TEXT NOT NULL
);
```

`created_at` is stored as an ISO 8601 UTC string (`datetime.utcnow().isoformat()`).

The database is initialized at app startup inside the existing `lifespan` context manager in `main.py`. Uses Python's built-in `sqlite3` module — no new dependencies.

---

## Data stored per submission

| Field | Source |
|---|---|
| `query` | Passed from frontend (the user's search query) |
| `answer` | Passed from frontend (full synthesized answer text) |
| `rating` | `"up"` or `"down"` |
| `category` | Selected chip label, or `null` |
| `comment` | Free-text input, or `null` |
| `created_at` | Server-side UTC timestamp |

---

## Out of scope

- No admin UI for reviewing feedback (review via SQLite CLI or file download)
- No email/notification on submission
- No rate limiting on `/feedback` beyond existing app-level limits
- No per-user identification
