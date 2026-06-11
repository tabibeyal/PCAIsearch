# Contact Developer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Contact" button to the Support Banner that opens a modal with Name + Email + Message fields, submitting via Resend to pcaisearch@atomicmail.io.

**Architecture:** A new `POST /contact` FastAPI endpoint calls Resend's API server-side (API key stays in backend env vars). The Next.js frontend proxies the request through a new `/api/contact` route, mirroring the existing feedback pattern. A new `ContactModal` component handles the form, success, and error states.

**Tech Stack:** Python `resend` package (backend), React + Tailwind (frontend modal), Next.js API route (proxy).

---

## File Map

| File | Action |
|------|--------|
| `backend/app/main.py` | Add `ContactBody` model + `POST /contact` endpoint |
| `Dockerfile` | Add `resend` to pip install block |
| `tests/backend/test_contact.py` | New — unit tests for /contact |
| `frontend/app/api/contact/route.ts` | New — Next.js proxy route to backend |
| `frontend/lib/api.ts` | Add `submitContact()` helper |
| `frontend/components/ContactModal.tsx` | New — modal component |
| `frontend/components/SupportBanner.tsx` | Add Contact button + render modal |

---

## Task 1: Backend — ContactBody model and /contact endpoint

**Files:**
- Modify: `backend/app/main.py`
- Modify: `Dockerfile`

- [ ] **Step 1: Add `resend` to the Dockerfile pip install block**

Open `Dockerfile`. Find the `RUN pip install --no-cache-dir \` block and append `resend==2.10.0` to it:

```dockerfile
RUN pip install --no-cache-dir \
    fastapi==0.136.1 \
    uvicorn==0.46.0 \
    openai==2.33.0 \
    httpx==0.28.1 \
    qdrant-client==1.17.1 \
    sentence-transformers==5.4.1 \
    fastembed==0.8.0 \
    slowapi==0.1.9 \
    rank-bm25==0.2.2 \
    resend==2.10.0
```

- [ ] **Step 2: Add `ContactBody` model to `backend/app/main.py`**

Add this import at the top of the file alongside the existing `re` import (add `import re` if not already there):

```python
import re
```

Then add the `ContactBody` class after the existing `FeedbackBody` class:

```python
class ContactBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=10, max_length=5000)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Invalid email address")
        return v
```

Also add `field_validator` to the existing pydantic import line:
```python
from pydantic import BaseModel, Field, field_validator
```

- [ ] **Step 3: Add `POST /contact` endpoint to `backend/app/main.py`**

Add this endpoint after the `POST /feedback` endpoint:

```python
@app.post("/contact")
@limiter.limit("5/hour")
async def contact(request: Request, body: ContactBody):
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY not set")
        return {"ok": False}, 500

    import resend as resend_client
    resend_client.api_key = api_key

    params: resend_client.Emails.SendParams = {
        "from": "PCAIsearch <onboarding@resend.dev>",
        "to": ["pcaisearch@atomicmail.io"],
        "reply_to": body.email,
        "subject": f"[PCAIsearch] Message from {body.name}",
        "text": f"Name: {body.name}\nEmail: {body.email}\n\nMessage:\n{body.message}",
    }
    resend_client.Emails.send(params)
    return {"ok": True}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py Dockerfile
git commit -m "feat: add POST /contact endpoint with Resend integration"
```

---

## Task 2: Backend tests for /contact

**Files:**
- Create: `tests/backend/test_contact.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/test_contact.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def contact_client(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-tests")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_fake_key")
    from unittest.mock import AsyncMock
    mock_qdrant = AsyncMock()
    mock_qdrant.create_payload_index = AsyncMock(return_value=None)
    with patch("backend.app.services.search_pipeline.AsyncQdrantClient", return_value=mock_qdrant):
        with TestClient(app) as c:
            yield c


def test_contact_sends_email(contact_client):
    mock_send = MagicMock(return_value={"id": "abc123"})
    with patch("resend.Emails.send", mock_send):
        r = contact_client.post("/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message from a user.",
        })
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    mock_send.assert_called_once()
    call_params = mock_send.call_args[0][0]
    assert call_params["to"] == ["pcaisearch@atomicmail.io"]
    assert call_params["reply_to"] == "test@example.com"
    assert "Test User" in call_params["subject"]
    assert "This is a test message" in call_params["text"]


def test_contact_rejects_missing_fields(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "test@example.com",
    })
    assert r.status_code == 422


def test_contact_rejects_invalid_email(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "not-an-email",
        "message": "This is a test message from a user.",
    })
    assert r.status_code == 422


def test_contact_rejects_short_message(contact_client):
    r = contact_client.post("/contact", json={
        "name": "Test User",
        "email": "test@example.com",
        "message": "Too short",
    })
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/test_contact.py -v
```

Expected: all 4 tests FAIL with import errors or 404s (endpoint doesn't exist yet — but actually Task 1 was done first, so they should pass. If Task 1 is already done, they should pass.)

- [ ] **Step 3: Run the full backend test suite to check for regressions**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/backend/test_contact.py
git commit -m "test: add /contact endpoint tests"
```

---

## Task 3: Frontend proxy route and API helper

**Files:**
- Create: `frontend/app/api/contact/route.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Create the Next.js proxy route**

Create `frontend/app/api/contact/route.ts` (mirror of the existing feedback route):

```typescript
import { NextRequest } from 'next/server';
import { BACKEND_URL } from '@/lib/backend';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response('Invalid JSON', { status: 400 });
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    console.error('Backend unreachable:', e);
    return new Response('Service temporarily unavailable', { status: 502 });
  }
  return new Response(null, { status: upstream.status });
}
```

- [ ] **Step 2: Add `submitContact` to `frontend/lib/api.ts`**

Append this function to the end of `frontend/lib/api.ts`:

```typescript
export async function submitContact(payload: {
  name: string;
  email: string;
  message: string;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw apiError('Contact submission failed', res.status);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/api/contact/route.ts frontend/lib/api.ts
git commit -m "feat: add contact API proxy route and submitContact helper"
```

---

## Task 4: ContactModal component

**Files:**
- Create: `frontend/components/ContactModal.tsx`

- [ ] **Step 1: Create the modal component**

Create `frontend/components/ContactModal.tsx`:

```typescript
'use client';

import React, { useEffect, useRef, useState } from 'react';
import { submitContact } from '@/lib/api';

interface ContactModalProps {
  onClose: () => void;
}

type ModalState = 'form' | 'loading' | 'success' | 'error';

export function ContactModal({ onClose }: ContactModalProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [state, setState] = useState<ModalState>('form');
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const isValidEmail = (v: string) => /[^@]+@[^@]+\.[^@]+/.test(v);
  const canSubmit = name.trim() && isValidEmail(email) && message.trim().length >= 10;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setState('loading');
    try {
      await submitContact({ name: name.trim(), email: email.trim(), message: message.trim() });
      setState('success');
    } catch {
      setState('error');
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl p-7">
        {state === 'success' ? (
          <div className="text-center py-6">
            <div className="text-4xl mb-4">✓</div>
            <h2 className="text-lg font-semibold text-gray-900 font-serif mb-2">Message sent</h2>
            <p className="text-sm text-gray-500">Thanks for reaching out. I'll get back to you soon.</p>
            <button
              onClick={onClose}
              className="mt-6 border border-gray-300 rounded-md px-5 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-start mb-5">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 font-serif">Contact the developer</h2>
                <p className="text-sm text-gray-500 mt-1">Questions, feedback, or bug reports welcome.</p>
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">✕</button>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Name</label>
                <input
                  ref={firstInputRef}
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Message</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="What's on your mind?"
                  rows={4}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                  required
                />
              </div>

              {state === 'error' && (
                <p className="text-sm text-red-600">
                  Something went wrong — please try again or email{' '}
                  <a href="mailto:pcaisearch@atomicmail.io" className="underline">pcaisearch@atomicmail.io</a> directly.
                </p>
              )}

              <button
                type="submit"
                disabled={!canSubmit || state === 'loading'}
                className="bg-[#2c1f14] text-white rounded-md py-2.5 text-sm font-medium hover:bg-[#3d2d1e] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {state === 'loading' ? 'Sending…' : 'Send message'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ContactModal.tsx
git commit -m "feat: add ContactModal component"
```

---

## Task 5: Wire Contact button into SupportBanner

**Files:**
- Modify: `frontend/components/SupportBanner.tsx`

- [ ] **Step 1: Update SupportBanner to include the Contact button and modal**

Replace the entire contents of `frontend/components/SupportBanner.tsx` with:

```typescript
'use client';

import React, { useState, useEffect } from 'react';
import { useSupportBanner } from './SupportBannerContext';
import { ContactModal } from './ContactModal';

export function SupportBanner() {
  const [visible, setVisible] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);
  const { deepDiveOpen } = useSupportBanner();

  // On mobile: show when the sentinel below FeedbackBar scrolls into view,
  // hide when it scrolls back out. Sentinel size comes from
  // SUPPORT_BANNER_SENTINEL_HEIGHT_PX in lib/banner.ts — keep the rendered
  // spacer in SynthesisView aligned with that value.
  useEffect(() => {
    if (typeof window === 'undefined' || window.innerWidth >= 768) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (deepDiveOpen) return;
        setVisible(entries.some((e) => e.isIntersecting));
      },
      { threshold: 0 }
    );

    const attach = () =>
      document.querySelectorAll('[data-support-trigger]').forEach((el) => observer.observe(el));

    attach();

    // Re-attach when sentinels mount after initial render (route changes, lazy
    // content). Coalesce with rAF so a burst of mutations — e.g. answer text
    // streaming in token by token — triggers at most one querySelectorAll per
    // frame instead of one per token.
    let rafId = 0;
    const scheduleAttach = () => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => { rafId = 0; attach(); });
    };
    const mo = new MutationObserver(scheduleAttach);
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      observer.disconnect();
      mo.disconnect();
    };
  }, [deepDiveOpen]);

  const showBanner = visible && !deepDiveOpen;

  return (
    <>
      {contactOpen && <ContactModal onClose={() => setContactOpen(false)} />}
      <footer
        className={[
          'w-full bg-white border-t border-gray-200 py-4',
          // Mobile: fixed at bottom, slide in/out
          'fixed bottom-0 left-0 right-0 z-50 transition-transform duration-300',
          // Desktop: normal flow, always visible
          'md:static md:transform-none',
          showBanner ? 'translate-y-0' : 'translate-y-full',
        ].join(' ')}
        style={{ transitionTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)' }}
      >
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 px-6 text-sm text-gray-500">
          <p className="text-center sm:text-left">
            This tool runs on a free AI model, but server hosting still costs money.
            If this tool is useful to you, consider supporting it.
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href="https://paypal.me/EyalTabib50"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2 transition-colors"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
              </svg>
              Support this project
            </a>
            <button
              onClick={() => setContactOpen(true)}
              className="inline-flex items-center rounded-md border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 font-medium px-4 py-2 transition-colors"
            >
              Contact
            </button>
          </div>
        </div>
      </footer>
    </>
  );
}
```

- [ ] **Step 2: Run the backend tests to confirm nothing is broken**

```bash
PYTHONPATH=. python3 -m pytest tests/backend/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SupportBanner.tsx
git commit -m "feat: wire Contact button into SupportBanner"
```

---

## Task 6: Add RESEND_API_KEY to DigitalOcean App Platform

> This task is manual — no code changes needed.

- [ ] **Step 1: Sign up for Resend**

Go to resend.com and create a free account. On the free tier, you can send up to 100 emails/day.

- [ ] **Step 2: Get your API key**

In the Resend dashboard, go to API Keys → Create API Key. Copy the key (it starts with `re_`).

- [ ] **Step 3: Note on the sender address**

On Resend's free tier without a verified domain, the `from` address must be `onboarding@resend.dev`. To use a custom from address (e.g. `noreply@pcaisearch.app`), you need to verify a domain in the Resend dashboard under Domains. This is optional — the email will still deliver correctly either way, and the Reply-To will point to the user's address so you can reply normally.

- [ ] **Step 4: Add the env var in DigitalOcean**

In the DigitalOcean App Platform dashboard, go to your backend app → Settings → Environment Variables → Add:

```
RESEND_API_KEY = re_your_key_here
```

Save and redeploy.
