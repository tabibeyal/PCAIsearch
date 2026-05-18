# Handoff: Divider Toggle — Collapse/Restore Sources Pane

## What was built

A floating pill button on the divider between the Answer and Sources panes in Deep Dive mode. Clicking it collapses or restores the Sources pane without scrolling and without exiting Deep Dive.

## Behaviour

| State | Toggle position | Icon | Click action |
|---|---|---|---|
| Deep Dive open, sources visible | Centred on divider | `›` | Collapse sources, answer expands full width |
| Deep Dive open, sources collapsed | Right edge of screen | `‹` | Restore sources, answer returns to 50% |
| Deep Dive closed | Not rendered | — | — |

Additional rules:
- Clicking a citation **always** reopens sources (even if collapsed) and scrolls to the verse
- Clicking **"Hide Sources"** exits Deep Dive entirely and resets the toggle state for next entry
- Toggle is **hidden and non-interactive on mobile** (`hidden md:flex pointer-events-none md:pointer-events-auto`)

## Visual design

- 18×36px outlined pill
- Background `#faf9f7` (cream), border `1.5px solid #6b4e35` (warm brown), icon `#6b4e35`
- Hover: icon darkens to `#4a3728`
- Shadow: `0 1px 4px rgba(107,78,53,0.15)`
- Full border-radius when on divider (`10px`); left-only radius when hugging right edge (`8px 0 0 8px`)

## Files changed

| File | Change |
|---|---|
| `frontend/components/deep-dive/DividerToggle.tsx` | New component — the pill button |
| `frontend/components/deep-dive/DualPaneContainer.tsx` | Added `sourcesVisible` state, renders `DividerToggle` |

## State model (DualPaneContainer)

```
deepDive=false                → single pane, no toggle
deepDive=true, sourcesVisible=true  → 50/50 split, toggle on divider showing ›
deepDive=true, sourcesVisible=false → full-width answer, toggle on right edge showing ‹
```

`sourcesVisible` resets to `true` whenever Deep Dive is exited or a citation is clicked.

## No backend changes.
