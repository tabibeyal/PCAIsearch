---
name: Ask the Pali Canon
description: AI-powered search for the Pali Canon — calm, scholarly, ancient.
colors:
  pale-vellum: "#faf9f7"
  deep-ink: "#2c1f14"
  deep-sandalwood: "#4a3728"
  sandalwood: "#6b4e35"
  passage-ink: "#6b5c4e"
  pale-sandalwood: "#9c8c7a"
  reed-line: "#e8e4dc"
  vellum-wash: "#ede8df"
  river-taupe: "#b5a494"
  stone-dust: "#c8bfb5"
  warm-stone: "#d4c9b8"
  amber-cta: "#f59e0b"
  state-warning-bg: "#fef3c7"
  state-warning-text: "#b45309"
  state-error-bg: "#fee2e2"
  state-error-text: "#dc2626"
typography:
  display:
    fontFamily: "Georgia, serif"
    fontWeight: 700
    fontSize: "clamp(1.875rem, 5vw, 2.25rem)"
    lineHeight: 1.1
    letterSpacing: "normal"
  synthesis:
    fontFamily: "Georgia, serif"
    fontWeight: 400
    fontSize: "17px"
    lineHeight: 1.85
  body:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontWeight: 400
    fontSize: "1rem"
    lineHeight: 1.6
  passage:
    fontFamily: "Georgia, serif"
    fontWeight: 400
    fontSize: "0.8125rem"
    lineHeight: 1.75
  source:
    fontFamily: "Georgia, serif"
    fontWeight: 400
    fontSize: "15px"
    lineHeight: 1.75
  label:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontWeight: 500
    fontSize: "0.875rem"
  micro:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontWeight: 400
    fontSize: "0.75rem"
rounded:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  full: "9999px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.deep-sandalwood}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.sandalwood}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.sandalwood}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
  tab-active:
    backgroundColor: "{colors.deep-sandalwood}"
    textColor: "#ffffff"
    rounded: "{rounded.full}"
    padding: "6px 16px"
  tab-inactive:
    backgroundColor: "transparent"
    textColor: "{colors.pale-sandalwood}"
    rounded: "{rounded.full}"
    padding: "6px 16px"
  nikaya-pill-active:
    backgroundColor: "{colors.vellum-wash}"
    textColor: "{colors.sandalwood}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  nikaya-pill-inactive:
    backgroundColor: "transparent"
    textColor: "{colors.pale-sandalwood}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  sutta-chip:
    backgroundColor: "{colors.vellum-wash}"
    textColor: "{colors.sandalwood}"
    rounded: "{rounded.xs}"
    padding: "2px 8px"
  citation-chip:
    backgroundColor: "{colors.vellum-wash}"
    textColor: "{colors.sandalwood}"
    rounded: "{rounded.xs}"
    padding: "2px 6px"
  citation-chip-unverified:
    backgroundColor: "{colors.state-error-bg}"
    textColor: "{colors.state-error-text}"
    rounded: "{rounded.xs}"
    padding: "2px 6px"
---

# Design System: Ask the Pali Canon

## 1. Overview

**Creative North Star: "The Monastic Scriptorium"**

Quiet, orderly, ancient. The interface takes the posture of a scriptorium monk — precise, unhurried, completely in service to the text. Every surface steps aside so the suttas can speak. The design accumulates trust through restraint, not through personality.

The system is color-restrained: one sandalwood accent, used only where it earns its place — primary actions, active navigation, citation affordances. The warm near-white ground is a vellum register, present but never demanding. Depth comes from border tone and tonal fill, not shadows or elevation gestures. Typography does the heaviest lifting: Georgia serif is reserved for the display heading, the AI synthesis answer, and all extracted passage text — the three things the user actually came to read. Everything else steps back into the margin.

The deep-dive experience (synthesis answer + source pane) is the typographic center of gravity. When a user opens sources, the synthesis text at 17px/1.85 and the source text at 15px/1.75 are both set in Georgia, creating a single reading surface that feels like consulting a commentary alongside the primary text. Nothing else on any screen uses this pairing.

The system rejects four specific bad paths: the generic SaaS dashboard (dark sidebar, white chat bubbles, blue accents); the religious institution site (temple imagery, gold ornament); the academic filing cabinet (JSTOR-style density, no visual breathing room); the wellness app (pastel gradients, "peaceful" performance). None of those serve a practitioner trying to find a sutta passage.

**Key Characteristics:**
- One accent color (Deep Sandalwood) on ≤15% of any screen — rarity is the mechanism
- Serif reserved for display headline, synthesis answer, and all passage text; system sans for all UI chrome
- Flat-by-default elevation; only the primary search input earns a shadow
- Motion confined to the deep-dive pane enter, loading feedback, and the typewriter placeholder
- State colors (amber warning, red error) appear only for semantic alerts — never decoration

## 2. Colors: The Sandalwood Palette

One warm-brown family, five lightness steps from espresso to vellum. No secondary accent. Two semantic state colors appear only for error and warning conditions.

### Primary

- **Deep Sandalwood** (`#4a3728`): Button fills, active tab state, active nav. Used on ≤15% of any screen. Its rarity is what makes it read as "act here."
- **Sandalwood** (`#6b4e35`): Hover state for Deep Sandalwood surfaces, inline link text, citation chip text, secondary emphasis.

### Neutral

- **Pale Vellum** (`#faf9f7`): Body background on all surfaces — landing, nav, synthesis pane, source pane. Warm but quiet. Never a design statement.
- **Deep Ink** (`#2c1f14`): All primary text. Near-black with a warm cast; never pure black.
- **Passage Ink** (`#6b5c4e`): English passage text in result cards. Slightly warmer than Sandalwood; subordinate to the UI but still readable.
- **Muted Sandalwood** (`#76604a`): Secondary text, labels, descriptors, inactive tab text, placeholder text, Pāḷi supporting text, match-percentage label. The minimum AA-readable text color — passes 4.5:1 on Pale Vellum, white, and Vellum Wash. Use this for every small text role that carries meaning.
- **Pale Sandalwood** (`#9c8c7a`): Focus rings and focus-within borders only (non-text UI indicator; meets the 3:1 non-text contrast minimum), and the primary-button loading fill. Not for text — at ~3.2:1 it fails WCAG AA for body text.
- **Reed Line** (`#e8e4dc`): Borders, card outlines, dividers, spinner track, and the structural gap color between deep-dive panes. The primary depth signal.
- **Vellum Wash** (`#ede8df`): Active chip/pill fills, hover tints on empty interactive surfaces, highlighted source card background.
- **River Taupe** (`#b5a494`): Blinking cursor, typewriter placeholder. Decorative only (aria-hidden) — fails WCAG AA on Pale Vellum as body text.
- **Stone Dust** (`#c8bfb5`): Whisper-level decorative only — fails WCAG AA. Not used for any meaning-carrying text (the match-percentage label uses Muted Sandalwood so the score is actually readable).
- **Warm Stone** (`#d4c9b8`): Nikāya pill pending state during navigation. Clears on route settle.

### State (semantic only — never decorative)

- **Amber Warning** (`#fef3c7` bg / `#92400e` text): Hallucination-flagged badge in the synthesis header.
- **Error** (`#fee2e2` bg / `#991b1b` text): Unverified citation chips inside synthesis text. Signals "do not cite this."

### Accent (off-palette, single use)

- **Amber CTA** (`#f59e0b`): Donation button in SupportBanner only. Deliberately off-palette to signal an external, economic action. Never reuse elsewhere.

### Named Rules

**The One Accent Rule.** Deep Sandalwood (`#4a3728`) is the only saturated color on any screen. Deploy it on primary buttons and active states only. Never as decoration, never on inactive states.

**The Contrast Floor Rule.** River Taupe (`#b5a494`), Stone Dust (`#c8bfb5`), and Pale Sandalwood (`#9c8c7a`) do not meet WCAG AA for body text (each lands ~1.8–3.3:1). Use them only for non-text or decorative roles: River Taupe for the blinking cursor / typewriter placeholder (aria-hidden), Stone Dust for whisper-level decoration, Pale Sandalwood for focus rings/borders and the button loading fill. Real readable text uses Deep Ink, Sandalwood, or Muted Sandalwood (`#76604a`) as the minimum — Muted Sandalwood is the only secondary-text color that clears 4.5:1 on Pale Vellum, white, and Vellum Wash.

**The State Isolation Rule.** Amber and red appear only for semantic alert states (hallucination warning, unverified citation). Reaching for either color anywhere else is a design error.

## 3. Typography

**Display / Passage Font:** Georgia (serif) — used for the landing heading, synthesis answer, and all extracted passage text
**Body / UI Font:** system-ui, -apple-system, sans-serif — used for navigation, labels, buttons, and all UI chrome

**Character:** A serif/sans split where the serif appears only for what the user came to read: the heading that names the tool, the synthesized AI answer, and the ancient source text it surfaces. The sans handles all scaffolding. The split is the system's clearest statement about what matters.

### Hierarchy

- **Display** (Georgia bold, `clamp(1.875rem, 5vw, 2.25rem)`, line-height 1.1): Landing page heading only. "Ask the Pali Canon."
- **Synthesis** (Georgia regular, `17px`, line-height 1.85): AI-generated answer text in the synthesis pane. The most generous setting in the system — long-form reading deserves room. Color: Deep Ink.
- **Source** (Georgia regular, `15px`, line-height 1.75): English passage text in SourceViewer cards. Slightly smaller than synthesis to signal supporting status, but readable for attentive reading. Color: Deep Ink.
- **Passage** (Georgia regular, `0.8125rem` / 13px, line-height 1.75): English passage text in result list cards. Compact scanning mode. Color: Passage Ink (`#6b5c4e`).
- **Body** (system sans regular, 1rem, line-height 1.6): Search input text, navigation prose, general UI copy.
- **Label** (system sans medium, 0.875rem, line-height 1.4): Tab labels, nav links, button text.
- **Micro** (system sans regular, 0.75rem, line-height 1.4): Nikāya chip text, sutta ID badges, score percentages, "view on dhammatalks.org" link.

### Named Rules

**The Serif Reserve Rule.** Georgia appears in exactly four contexts: the display heading, synthesis answer, source viewer passages, and result card passages. Not in navigation, not in button labels, not in supporting copy.

**The Reading Gradient Rule.** Three serif sizes — 17px synthesis, 15px source, 13px result card — each calibrated to their reading mode. Do not flatten them to a single size "for consistency." The gradient communicates hierarchy between primary, supporting, and scanning contexts.

## 4. Elevation

The system is flat by default. Surfaces are differentiated by border color and tonal fill, not shadow depth. A white card on Pale Vellum reads as distinct through its Reed Line border; shadow would over-declare what should quietly recede.

The one exception: the primary landing search input earns a soft ambient shadow because it is the single primary action affordance on an otherwise flat page.

The deep-dive split layout uses Reed Line (`#e8e4dc`) as the gap color between panes — a structural divider that uses the border color as a surface, not a shadow.

### Shadow Vocabulary

- **Ambient Search** (`0 1px 2px rgba(0,0,0,0.05), 0 0 0 1px #e8e4dc`): Primary landing search input only.

### Motion Vocabulary

The global transition curve is `cubic-bezier(0.22, 1, 0.36, 1)` — a spring-like settle applied to all Tailwind transitions via `:root --default-transition-timing-function`. Three keyframes are defined:

- **`paneEnter`** (`translateX(20px) + blur(4px)` → resting, 300ms): Source pane slides and unblurs in. The blur adds material weight to the reveal.
- **`fadeUp`** (`translateY(6px) + opacity 0` → resting): Content arriving after a wait.
- **`fadeIn`** (opacity 0 → 1, 300ms): Results list and deep-dive divider toggle.

All animations suppressed via `prefers-reduced-motion: reduce` in globals.css — a hard requirement.

### Named Rules

**The Flat-By-Default Rule.** Shadows appear only on the primary search input. Everything else uses border-only depth. Adding a shadow to any card, nav, banner, or modal is almost certainly wrong.

**The Motion Restraint Rule.** Motion conveys one of three things: loading state, content arrival, or structural layout change (pane open/close). Decorative motion — hover flourishes, staggered list entrances, scroll choreography — is prohibited.

## 5. Components

### Buttons

Understated. They do not announce themselves; they wait to be found.

- **Shape:** 12px radius (`rounded-xl`) for standard and icon buttons; 8px (`rounded-lg`) for inline compact buttons.
- **Primary** (Deep Sandalwood fill, white text): The authoritative action. 36×36px for icon buttons; padded to content for text buttons.
- **Hover:** Background shifts to Sandalwood (`#6b4e35`). No scale or lift.
- **Active:** `transform: scale(0.97)`, 80ms ease. Tactile press.
- **Loading state:** Background shifts to Pale Sandalwood (`#9c8c7a`).
- **Ghost / Outline:** Transparent fill, Reed Line border, Sandalwood text. Secondary actions: Contact button, Deep Dive toggle at rest.
- **Deep Dive toggle (active):** Deep Sandalwood fill, white text, Deep Sandalwood border.
- **Disabled:** `opacity: 0.25`.

### View Switcher Tabs

- **Active:** Deep Sandalwood fill, white text, full-radius pill.
- **Inactive:** No fill, Muted Sandalwood text. Hover: Vellum Wash fill.
- **Separator:** Reed Line 1px vertical rule between tabs and Nikāya filter (hidden on mobile).

### Nikāya Filter Pills

Two tiers, so the row is a scannable five choices instead of twelve peer pills. The four main nikāyas (DN/MN/SN/AN) are always visible as pills alongside **All**. The seven Khuddaka-pāṭha sub-books (DHP/ITI/UD/STNP/THAG/THIG/KHP) sit behind a **Khuddaka** disclosure toggle.

- **Primary row:** `All` + `DN` + `MN` + `SN` + `AN`, always visible.
- **Khuddaka disclosure:** a pill-shaped toggle (not a filter selector). Chevron rotates 180° when open. Shows a count `(n)` when a sub-book is active, so the active selection is signaled even while closed. Opens automatically when a Khuddaka book is in the URL selection; closing is still allowed.
- **Inactive:** Reed Line border, no fill, Muted Sandalwood text. Hover: Vellum Wash fill.
- **Active:** Vellum Wash fill, Sandalwood text, Reed Line border.
- **Pending:** Warm Stone fill, Deep Sandalwood text. Clears on route settle.
- **Interaction:** Plain click = switch to this nikāya only. Re-clicking the sole active pill resets to All. Cmd/Ctrl-click toggles multi-selection (works on main pills and Khuddaka sub-books alike).

### Search Input (Landing)

The primary action surface and the system's one design gesture.

- **Container:** White fill, 16px radius (`rounded-2xl`), Reed Line border, ambient shadow. Grows vertically with content (textarea, not input).
- **Typewriter placeholder:** Animated sample queries, 530ms cursor blink in River Taupe. Pauses on focus, fades on first keystroke.
- **Focus ring:** Border shifts to Pale Sandalwood; `ring-2 ring-[#9c8c7a]`.
- **Submit button:** 36×36px, 12px radius, absolute bottom-right, Deep Sandalwood fill, up-arrow SVG.

### Nav Search Input (Compact)

Same container vocabulary (white, `rounded-2xl`, Reed Line border) but compact (`py-2`, single-line). Submit button 28×28px, 8px radius.

### Result Cards (SearchResultsView)

- **Shape:** 12px radius, Reed Line border, white fill, 14px all-sides padding.
- **Header:** Sutta chip left, match score right.
- **Pāḷi text (if present):** Italic, Muted Sandalwood, `text-xs`, system sans.
- **English passage:** Georgia regular, 13px / line-height 1.75, Passage Ink.
- **Footer:** "View on dhammatalks.org" in Muted Sandalwood, `text-[11px]`, underline on hover.
- **Match score:** Muted Sandalwood, `text-xs`. Right-aligned in the header. AA-readable so the score is legible, not whisper-level.

### Sutta ID Chip

Vellum Wash fill, Sandalwood text, 4px radius, `2px 8px` padding, Micro typography. Links to dhammatalks.org.

### Citation Chips (Synthesis Answer)

Inline `<button>` elements rendered within synthesis answer text.

- **Verified:** Vellum Wash fill, Sandalwood text, 4px radius, dotted underline, `text-[11px]`. Clicking opens the source pane and scrolls to the matching passage.
- **Unverified:** Error-red fill and text (`#fee2e2` / `#991b1b`), `cursor-not-allowed`. The guardrail caught a hallucination — display only, never link.

### Synthesis Pane (SynthesisView)

- **Background:** Pale Vellum, full-height scroll, 24px padding.
- **Answer text:** Georgia regular, 17px / line-height 1.85, Deep Ink. The typographic center of gravity.
- **Hallucination warning badge:** Amber (`#fef3c7` bg / `#92400e` text), shown in the header row when the guardrail flags the answer.
- **Deep Dive toggle:** Ghost style at rest; primary fill when deep dive is active.

### Deep Dive Layout (DualPaneContainer + SourceViewer)

- **Split:** Synthesis 50% width on desktop (60% height on mobile), source pane takes the remainder. Reed Line fills the structural gap between panes.
- **Source pane enter:** `paneEnter` keyframe, 300ms, spring curve. Slides from right with a blur dissolve.
- **Source cards:** White fill, Reed Line border, 8px radius, 16px padding.
- **Active source card:** Vellum Wash fill, `#c8b89a` border — marks the cited passage in focus.
- **Source Pāḷi text:** Italic, Muted Sandalwood, `text-base` (16px), system sans.
- **Source English text:** Georgia regular, 15px / line-height 1.75, Deep Ink. Readable alongside synthesis — never compressed to result-card size.
- **Mobile close handle:** Full-width, Pale Vellum bg, Sandalwood border and text, `text-xs font-semibold`.

### Loading State

- **Spinner:** 32px circle, Reed Line track, Sandalwood arc. Centered in content area.
- **Phase messages:** Muted Sandalwood, 14px. Three phases crossfade at 250ms; timing calibrated to stored latency average so phases feel measured, not theatrical.

### Support Banner

- **Style:** White fill, Reed Line top border. Fixed at viewport bottom on mobile (slides in/out), static on desktop.
- **Donation CTA:** Amber-500 (`#f59e0b`) fill. The only off-palette color. Signals an external economic action.
- **Contact button:** Ghost style — Reed Line border, white fill, Sandalwood text.

## 6. Do's and Don'ts

### Do:

- **Do** use Georgia serif for display heading, synthesis answer, source passages, and result card passages exclusively. Four contexts only.
- **Do** keep Deep Sandalwood (`#4a3728`) on primary buttons and active states only. Rarity is the mechanism.
- **Do** use Reed Line (`#e8e4dc`) borders as the sole depth mechanism on cards. No card shadows.
- **Do** honour the reading gradient: 13px passage in result cards, 15px in source viewer, 17px in synthesis. Each size is calibrated to its reading mode.
- **Do** apply `prefers-reduced-motion` globally via the `0.01ms` duration override in globals.css. It is non-negotiable.
- **Do** use the spring curve (`cubic-bezier(0.22, 1, 0.36, 1)`) for all transitions — it is baked into `:root` and inherited automatically.
- **Do** use Pale Sandalwood (`#9c8c7a`) as the minimum text color on Pale Vellum backgrounds (4.5:1 WCAG AA).
- **Do** isolate amber and red to their semantic roles: amber for hallucination warnings, red for unverified citations. Nothing else.

### Don't:

- **Don't** use `border-left` or `border-right` greater than 1px as a colored accent stripe on cards, list items, or passage blocks.
- **Don't** make the interface look like a generic SaaS tool. No dark sidebars, no white chat bubbles, no blue or purple accent colors.
- **Don't** introduce religious imagery or ornamentation. No temple motifs, no gold decoration, no mandala geometry.
- **Don't** reproduce the academic-database aesthetic. No JSTOR-style density, no table-first information architecture, no color-coded category bars.
- **Don't** signal wellness or mindfulness through design. No pastel gradients, no overtly "peaceful" rounded-everything softness.
- **Don't** use gradient text (`background-clip: text`). Single solid color; emphasis via weight or size.
- **Don't** add shadows to result cards, navigation bars, or banners. Only the primary landing search input earns depth.
- **Don't** reuse the amber CTA (`#f59e0b`) for anything other than the external donation link.
- **Don't** use River Taupe (`#b5a494`), Stone Dust (`#c8bfb5`), or Pale Sandalwood (`#9c8c7a`) for any text that carries real meaning — all fail WCAG AA for body text. Muted Sandalwood (`#76604a`) is the floor for secondary text.
- **Don't** show orchestrated page-load sequences or staggered list entrances. Motion here is structural and functional.
- **Don't** compress source passage text to result-card size (13px). Source text is being read, not scanned; it lives at 15px.
- **Don't** use Georgia in UI labels, navigation items, or buttons. It belongs exclusively in heading and passage contexts.
