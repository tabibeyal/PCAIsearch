# Search Results Page Redesign

**Date:** 2026-05-17

## Summary

Redesign the search results page and homepage to share a warm, contemplative color scheme suited to ancient Buddhist texts. Serif typography, cream backgrounds, and warm brown accents replace the current blue/white/gray palette.

---

## Color Scheme (applied everywhere)

| Token | Value | Usage |
|---|---|---|
| `bg-cream` | `#faf9f7` | Page background, nav background |
| `border-warm` | `#e8e4dc` | Card borders, dividers |
| `accent-dark` | `#4a3728` | Active tab pill, submit button, links |
| `accent-mid` | `#6b4e35` | Sutta ID badges |
| `accent-light` | `#ede8df` | Badge background, tag fills |
| `text-primary` | `#2c1f14` | Body text |
| `text-secondary` | `#6b5c4e` | Passage English text |
| `text-muted` | `#9c8c7a` | Nav links, Pāḷi text, subtitles |
| `text-faint` | `#c8bfb5` | Match score, faint labels |

Body text and passage text uses **Georgia serif**. All UI chrome (nav, buttons, labels, badges) uses the system sans-serif stack.

---

## Homepage (`app/page.tsx` + `SearchBar.tsx`)

- Page background: `#faf9f7`
- Heading and subtitle use `text-primary` / `text-muted`
- Search box: `bg-white`, border `#e8e4dc`, focus border `#9c8c7a`, `border-radius: 16px`
- Submit button: `bg-[#4a3728]` text white, hover `#6b4e35`
- Animated placeholder text color: `#b5a494`
- Animated cursor color: `#b5a494`

---

## Results Page — Navigation Bar

Sticky top bar, `bg-[#faf9f7]`, border-bottom `#e8e4dc`. Two rows:

**Row 1:**
- Left: "Ask the Pali Canon" — small brand home link (`text-muted`, links to `/`)
- Center/right: editable search box (same style as homepage, pre-filled with current query). Submitting navigates to `/search/<newquery>`

**Row 2:**
- Tabs: "AI Answer" | "Passages"
- Active tab: `bg-[#4a3728]` pill, white text
- Inactive tab: `text-muted`, hover `bg-[#ede8df]`
- NikayaFilter: keep as-is, styled to match warm palette

---

## Results Page — AI Answer Tab (`SynthesisView.tsx`)

- Background: `#faf9f7`
- Answer text: Georgia serif, `text-primary`, `font-size: 15px`, `line-height: 1.85`
- Inline citations `[DN 31]`: `bg-[#ede8df]` pill, `text-[#6b4e35]`, system sans, `font-size: 11px`
- Hallucination warning badge: amber, kept as-is
- "Deep Dive" / "Hide Sources" button: styled with `border-[#e8e4dc]`, `text-[#6b4e35]`, active state `bg-[#4a3728]` white text

---

## Results Page — Passages Tab (`SearchResultsView.tsx`)

Each passage card:
- `bg-white`, border `#e8e4dc`, `border-radius: 12px`, padding `14px`
- **Header row**: sutta ID badge (left) + match score (right, `text-faint`)
  - Sutta ID: `bg-[#ede8df]` `text-[#6b4e35]` rounded badge, links to SuttaCentral
  - Match score: shown as percentage (e.g. "94% match")
- **Pāḷi text**: italic, `text-muted`, `font-size: 11px`, `line-height: 1.6` — shown only when `result.pali` is present
- **English text**: left-border `#e8e4dc` (`border-left: 2px solid`), Georgia serif, `text-secondary`, `font-size: 13px`, `line-height: 1.75`
- **SuttaCentral link**: `text-faint`, underline, `font-size: 10px`, shown below English

---

## Out of Scope

- No changes to backend, API, or data
- NikayaFilter logic unchanged — only visual styling updated
- `SynthesisLoader` streaming behavior unchanged
- `DualPaneContainer` / `SourceViewer` deep-dive panel unchanged structurally
