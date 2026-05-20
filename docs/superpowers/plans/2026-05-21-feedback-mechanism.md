# Feedback Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thumbs-up / thumbs-down feedback bar below every synthesis answer, storing each submission (query, full answer, rating, optional category + comment) in a SQLite database on the backend server.

**Architecture:** A new `FeedbackBar` React component renders below the answer text in `SynthesisView`. It POSTs to a new `POST /feedback` FastAPI endpoint, which writes to a SQLite file (`feedback.db`) initialized at app startup. No new dependencies — `sqlite3` is part of Python's standard library.

**Tech Stack:** FastAPI (Python), SQLite (sqlite3 stdlib), React/Next.js (TypeScript), Tailwind CSS

---

## File Map

| Action | Path | What changes |
|---|---|---|
| Modify | `backend/app/main.py` | Add `FeedbackBody` model, `_FEEDBACK_DB` path, `_init_feedback_db()`, call in lifespan, `POST /feedback` endpoint, add `POST` to CORS |
| Create | `tests/backend/test_feedback.py` | Tests for the `/feedback` endpoint and DB writes |
| Modify | `frontend/lib/api.ts` | Add `submitFeedback()` fetch function |
| Create | `frontend/components/deep-dive/FeedbackBar.tsx` | New feedback UI component |
| Modify | `frontend/components/deep-dive/SynthesisView.tsx` | Destructure `query` from `data`, import and render `FeedbackBar` |

---

## Task 1: Backend — feedback endpoint + SQLite storage

**Files:**
- Modify: `backend/app/main.py`
- Create: `tests/backend/test_feedback.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/test_feedback.py` with this content:

```python
import sqlite3
import pytest
from fastapi.testclient import TestClient
import backend.app.main as m
from backend.app.main import app


@pytest.fixture
def feedback_client(tmp_path, monkeypatch):
    db = tmp_path / "feedback.db"
    monkeypatch.setattr(m, "_FEEDBACK_DB", db)
    with TestClient(app) as c:
        yield c, db


def test_feedback_thumbs_up_stored(feedback_client):
    client, db = feedback_client
    r = client.post("/feedback", json={
        "query": "What is dukkha?",
        "answer": "Dukkha means suffering.",
        "rating": "up",
        "category": None,
        "comment": None,
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    con = sqlite3.connect(db)
    rows = con.execute("SELECT query, rating, category FROM feedback").fetchall()
    con.close()
    assert rows == [("What is dukkha?", "up", None)]


def test_feedback_thumbs_down_with_category_stored(feedback_client):
    client, db = feedback_client
    r = client.post("/feedback", json={
        "query": "What is nibbana?",
        "answer": "Nibbana is the cessation of craving.",
        "rating": "down",
        "category": "Too vague",
        "comment": "Needs more depth",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    con = sqlite3.connect(db)
    rows = con.execute("SELECT rating, category, comment FROM feedback").fetchall()
    con.close()
    assert rows == [("down", "Too vague", "Needs more depth")]


def test_feedback_missing_required_field(feedback_client):
    client, _ = feedback_client
    r = client.post("/feedback", json={"query": "test"})
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_feedback.py -v
```

Expected: 3 failures — `POST /feedback` route does not exist yet, so you'll see 405 or 404 errors and fixture errors.

- [ ] **Step 3: Implement the backend changes**

In `backend/app/main.py`, make these additions:

**Add imports** at the top (after existing imports):
```python
import sqlite3
from datetime import datetime
from pydantic import BaseModel
```

**Add the DB path and model** after the `_DUMPS_DIR` line:
```python
_FEEDBACK_DB = Path(__file__).parent.parent.parent / "feedback.db"

class FeedbackBody(BaseModel):
    query: str
    answer: str
    rating: str
    category: Optional[str] = None
    comment: Optional[str] = None


def _init_feedback_db() -> None:
    con = sqlite3.connect(_FEEDBACK_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            query      TEXT NOT NULL,
            answer     TEXT NOT NULL,
            rating     TEXT NOT NULL,
            category   TEXT,
            comment    TEXT,
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()
```

**Call `_init_feedback_db()` in the lifespan** — add it as the first line inside the `async with lifespan` body, before the `oracle = CitationOracle(...)` line:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_feedback_db()
    oracle = CitationOracle(_DUMPS_DIR)
    ...
```

**Update CORS** to allow POST (change `allow_methods`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Add the endpoint** after the `/health` route:
```python
@app.post("/feedback")
async def post_feedback(body: FeedbackBody):
    con = sqlite3.connect(_FEEDBACK_DB)
    con.execute(
        "INSERT INTO feedback (query, answer, rating, category, comment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (body.query, body.answer, body.rating, body.category, body.comment, datetime.utcnow().isoformat()),
    )
    con.commit()
    con.close()
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_feedback.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Expected: all tests pass (same count as before + 3 new).

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py tests/backend/test_feedback.py
git commit -m "feat: add POST /feedback endpoint with SQLite storage"
```

---

## Task 2: Frontend API function

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add `submitFeedback` to `api.ts`**

Append this function to the end of `frontend/lib/api.ts`:

```typescript
export async function submitFeedback(payload: {
  query: string;
  answer: string;
  rating: 'up' | 'down';
  category: string | null;
  comment: string | null;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw apiError('Feedback submission failed', res.status);
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add submitFeedback API function"
```

---

## Task 3: FeedbackBar component

**Files:**
- Create: `frontend/components/deep-dive/FeedbackBar.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/components/deep-dive/FeedbackBar.tsx` with this content:

```tsx
'use client';

import React from 'react';
import { submitFeedback } from '@/lib/api';

const CATEGORIES = [
  'Doctrinally inaccurate',
  'Missing important nuance',
  'Not relevant to my question',
  "Sources don't support the answer",
  'Too vague',
] as const;

interface FeedbackBarProps {
  query: string;
  answer: string;
}

export function FeedbackBar({ query, answer }: FeedbackBarProps) {
  const [rating, setRating] = React.useState<'up' | 'down' | null>(null);
  const [panelOpen, setPanelOpen] = React.useState(false);
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null);
  const [comment, setComment] = React.useState('');
  const [submitted, setSubmitted] = React.useState(false);

  const handleThumbsUp = async () => {
    if (submitted) return;
    setRating('up');
    setSubmitted(true);
    await submitFeedback({ query, answer, rating: 'up', category: null, comment: null });
  };

  const handleThumbsDown = () => {
    if (submitted) return;
    setRating('down');
    setPanelOpen(true);
  };

  const handleSubmit = async () => {
    await submitFeedback({
      query,
      answer,
      rating: 'down',
      category: selectedCategory,
      comment: comment || null,
    });
    setSubmitted(true);
    setPanelOpen(false);
  };

  if (submitted) {
    return (
      <div className="border-t border-[#e8e4dc] pt-3 mt-6 flex items-center gap-3">
        <span className="text-xs text-[#999] font-sans">Thank you for your feedback.</span>
        <button
          disabled
          className="border rounded-md px-2.5 py-1.5 text-base opacity-60 cursor-default bg-[#4a3728] border-[#4a3728] text-white"
        >
          {rating === 'up' ? '👍' : '👎'}
        </button>
      </div>
    );
  }

  return (
    <div className="border-t border-[#e8e4dc] pt-3 mt-6">
      <div className="flex items-center gap-3 mb-1.5">
        <span className="text-xs text-[#999] font-sans">Was this helpful?</span>
        <button
          onClick={handleThumbsUp}
          className={`border rounded-md px-2.5 py-1.5 text-base transition-colors ${
            rating === 'up'
              ? 'bg-[#4a3728] border-[#4a3728] text-white'
              : 'bg-white border-[#e8e4dc] text-[#6b4e35] hover:bg-[#ede8df]'
          }`}
        >
          👍
        </button>
        <button
          onClick={handleThumbsDown}
          className={`border rounded-md px-2.5 py-1.5 text-base transition-colors ${
            rating === 'down'
              ? 'bg-[#4a3728] border-[#4a3728] text-white'
              : 'bg-white border-[#e8e4dc] text-[#6b4e35] hover:bg-[#ede8df]'
          }`}
        >
          👎
        </button>
      </div>
      <p className="text-[11px] text-[#bbb] font-sans italic mb-3">
        Feedback includes your question and this full answer.
      </p>

      {panelOpen && (
        <div className="bg-white border border-[#e8e4dc] rounded-lg p-4 font-sans">
          <p className="text-xs font-semibold text-[#4a3728] mb-2.5">What was the problem?</p>
          <div className="flex flex-wrap gap-2 mb-3.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                className={`border rounded-full px-3 py-1 text-xs transition-colors ${
                  selectedCategory === cat
                    ? 'bg-[#ede8df] border-[#c8b89a] text-[#6b4e35]'
                    : 'bg-white border-[#c8b89a] text-[#6b4e35] hover:bg-[#f5f0e8]'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Add a comment (optional)"
            className="w-full border border-[#e8e4dc] rounded-md p-2 text-xs text-[#4a3728] resize-none h-14 font-sans"
          />
          <div className="flex justify-end mt-2.5">
            <button
              onClick={handleSubmit}
              className="bg-[#4a3728] text-white border-none rounded-md p-2 flex items-center justify-center hover:bg-[#6b4e35] transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/deep-dive/FeedbackBar.tsx
git commit -m "feat: add FeedbackBar component"
```

---

## Task 4: Wire FeedbackBar into SynthesisView

**Files:**
- Modify: `frontend/components/deep-dive/SynthesisView.tsx`

`SynthesisResponse` already contains both `query` and `answer`, and `SynthesisView` already receives `data: SynthesisResponse`. No prop changes needed in `DualPaneContainer` or `SynthesisLoader`.

- [ ] **Step 1: Add import to SynthesisView**

At the top of `frontend/components/deep-dive/SynthesisView.tsx`, add the import after the existing React import:

```tsx
import { FeedbackBar } from './FeedbackBar';
```

- [ ] **Step 2: Destructure `query` from `data`**

Find this line in `SynthesisView`:
```tsx
const { answer, is_faithful } = data;
```

Change it to:
```tsx
const { answer, is_faithful, query } = data;
```

- [ ] **Step 3: Render FeedbackBar below the answer text**

Find the answer text div:
```tsx
<div
  className="text-[17px] leading-[1.85] text-[#1a1a1a]"
  style={{ fontFamily: 'Georgia, serif' }}
>
  {renderText(answer)}
</div>
```

Add `<FeedbackBar>` immediately after it (still inside the `max-w-2xl` div):
```tsx
<div
  className="text-[17px] leading-[1.85] text-[#1a1a1a]"
  style={{ fontFamily: 'Georgia, serif' }}
>
  {renderText(answer)}
</div>
<FeedbackBar query={query} answer={answer} />
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Build to confirm no runtime errors**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/deep-dive/SynthesisView.tsx
git commit -m "feat: render FeedbackBar in SynthesisView"
```
