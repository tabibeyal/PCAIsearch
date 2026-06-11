# Contact the Developer — Design Spec

**Date:** 2026-06-11
**Branch:** feat/contact-developer (to be created)

## Overview

Add a "Contact" button to the existing Support Banner. Clicking it opens a modal with a Name + Email + Message form. On submit, the backend calls Resend's API to deliver the message to pcaisearch@atomicmail.io.

## Placement

The "Contact" button lives inside `SupportBanner.tsx`, to the right of the existing "Support this project" button. It is a secondary-style button (white background, gray border) so it doesn't compete visually with the donate CTA.

The banner already handles mobile slide-in and desktop visibility — the Contact button inherits that behaviour with no extra work.

## Frontend

### ContactModal.tsx (new component)

A centered overlay modal containing:

- **Name** — text input, required
- **Email** — email input, required, validated as a valid email format
- **Message** — textarea, required, min 10 characters
- **Send message** button — submits the form; shows a loading state while the request is in flight
- **✕** close button in the top-right corner
- **Success state** — after a successful send, the form is replaced with a confirmation message ("Message sent — Thanks for reaching out. I'll get back to you soon.") and a Close button
- **Error state** — if the request fails, an inline error message appears below the form ("Something went wrong — please try again or email pcaisearch@atomicmail.io directly")

The modal traps focus while open and closes on Escape key or clicking the backdrop.

### SupportBanner.tsx (modified)

Adds a "Contact" button that sets local state `contactOpen = true`, rendering the `ContactModal`. No new context or global state needed.

## Backend

### New endpoint: `POST /contact`

Accepts a JSON body:

```
{ name: string, email: string, message: string }
```

Validation (returns 422 on failure):
- All three fields required and non-empty
- `email` must be a valid email format
- `message` minimum 10 characters

On valid input, calls Resend's API to send an email to pcaisearch@atomicmail.io with:
- **From:** `PCAIsearch Contact <noreply@pcaisearch.app>` (or Resend's sandbox sender on free tier)
- **Reply-To:** the user's submitted email address
- **Subject:** `[PCAIsearch] Message from {name}`
- **Body:** plain text with name, email, and message

Returns `{ ok: true }` on success, or propagates a 500 on Resend failure.

### Environment variable

`RESEND_API_KEY` — added to the DigitalOcean App Platform dashboard alongside existing keys.

### Dependency

`resend` Python package added to `requirements.txt`.

## Data Flow

```
User clicks "Contact" in SupportBanner
  → ContactModal opens
  → User fills Name / Email / Message and clicks Send
  → Frontend POSTs to /contact
  → Backend validates fields
  → Backend calls Resend API
  → Resend delivers email to pcaisearch@atomicmail.io with Reply-To set to user's email
  → Backend returns { ok: true }
  → Modal switches to success state
```

## Error Handling

- Frontend validates all fields before submitting (no empty fields, valid email format)
- If the backend returns an error, the modal shows an inline error message — the form is not cleared so the user can retry
- The Send button is disabled while a request is in flight to prevent double-submission

## Testing

- Backend: one unit test for `POST /contact` with a mocked Resend client — verifies the correct payload is sent and a 200 is returned
- Backend: one test for missing/invalid fields — verifies 422 is returned
- Frontend: manual smoke test — open modal, submit form, confirm success state appears

## Files to Create / Modify

| File | Change |
|------|--------|
| `frontend/components/ContactModal.tsx` | New component |
| `frontend/components/SupportBanner.tsx` | Add Contact button + render ContactModal |
| `backend/app/main.py` (or new `backend/app/routers/contact.py`) | Add POST /contact endpoint |
| `requirements.txt` | Add `resend` |
| `tests/backend/test_contact.py` | New test file |
