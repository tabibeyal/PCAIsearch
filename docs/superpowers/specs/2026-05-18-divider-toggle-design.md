# Divider Toggle — Design Spec
_2026-05-18_

## Problem

When Deep Dive is open, the only way to hide the Sources pane is the "Hide Sources" button in the answer header. If you've scrolled down in the answer, that button is off-screen. There's no way to collapse/restore Sources without scrolling back up.

## Solution

A floating pill button sits on the divider between the two panes. It collapses and restores the Sources pane without requiring any scrolling.

---

## Visual Design

- **Shape:** Outlined pill, 18px wide × 36px tall, fully rounded corners
- **Colours:** Background `#faf9f7` (cream), border `1.5px solid #6b4e35` (warm brown), icon colour `#6b4e35`
- **Icon:** Chevron character — `›` when sources are open, `‹` when collapsed
- **Shadow:** `0 1px 4px rgba(107,78,53,0.15)` — subtle, matches site palette
- **Hover:** Border darkens slightly (`#4a3728`) to confirm interactivity

---

## States

### Sources open
- Both panes visible (50/50 split)
- Pill sits centred on the divider (`position: absolute; left: 50%; transform: translateX(-50%)`)
- Shows `›` — click collapses Sources

### Sources collapsed
- Answer pane expands to full width; Sources pane unmounted
- Pill moves to the right edge of the answer pane (`right: 0`)
- Rounded only on left side (`border-radius: 8px 0 0 8px`) so it hugs the edge
- Shows `‹` — click restores Sources

---

## Behaviour

- Toggle only appears when `deepDive` is true (i.e. after the user has entered Deep Dive)
- Collapsing sources does **not** exit Deep Dive — reopening restores the exact same Sources pane
- The existing "Deep Dive / Hide Sources" button in `SynthesisView` continues to work; "Hide Sources" exits Deep Dive entirely, the toggle only hides/shows
- Transitions use the existing `transition-all duration-300` already on the panes

---

## State model

Add `sourcesVisible: boolean` to `DualPaneContainer` (default `true` when `deepDive` becomes true).

| `deepDive` | `sourcesVisible` | Layout |
|---|---|---|
| false | — | Answer full width, no toggle |
| true | true | 50/50 split, toggle on divider showing `›` |
| true | false | Answer full width, toggle on right edge showing `‹` |

"Hide Sources" button sets `deepDive = false` (and implicitly `sourcesVisible = true` for next open).
Divider toggle sets `sourcesVisible = !sourcesVisible`.

---

## Responsive

- Toggle only visible at `md:` breakpoint and above
- On mobile the panes stack vertically; the toggle is hidden (`hidden md:flex`)

---

## Files to change

- `frontend/components/deep-dive/DualPaneContainer.tsx` — add `sourcesVisible` state, render `DividerToggle`, conditionally render Sources pane based on `sourcesVisible`

## New component

- `frontend/components/deep-dive/DividerToggle.tsx` — the pill button; props: `sourcesVisible: boolean`, `onClick: () => void`

---

## Out of scope

- Drag-to-resize the divider
- Remembering toggle state across searches
- Mobile layout changes
