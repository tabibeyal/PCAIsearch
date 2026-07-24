@AGENTS.md

## Key lib utilities
`lib/suttacentral.ts` — `suttaCentralUrl(id)` builds SuttaCentral URLs
`lib/utils.ts` — `stripThinking(text)` removes `<think>` blocks
`lib/api.ts` — typed fetch wrappers (`SynthesisResponse`, `submitFeedback`)

## Key components
`components/deep-dive/FeedbackBar.tsx` — thumbs up/down feedback UI rendered below synthesis answers; POSTs to `POST /feedback`; `query` prop threaded via `SynthesisLoader` → `DualPaneContainer` → `SynthesisView` → `FeedbackBar`
