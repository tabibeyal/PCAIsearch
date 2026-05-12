@AGENTS.md

## Commands
`npm run dev` — dev server (port 3000)
`npm run build` — production build

## Key lib utilities
`lib/suttacentral.ts` — `suttaCentralUrl(id)` builds SuttaCentral URLs
`lib/utils.ts` — `stripThinking(text)` removes `<think>` blocks
`lib/api.ts` — typed fetch wrappers (`SearchResponse`, `SynthesisResponse`)
