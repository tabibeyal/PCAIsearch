# Handoff: Streaming Text → Final Answer Style Consistency

## Status

**Resolved.** Both render phases now use matching styles.

## Problem (was)

When the LLM streams, text was rendered in `SynthesisLoader.tsx` with styles that didn't match the final `SynthesisView`. The visual jump on stream completion was jarring.

## Current styles (both phases must match)

| Phase | Component | Styles |
|---|---|---|
| Streaming in progress | `SynthesisLoader.tsx` (line 75–77) | `bg-[#fef9f0]`, `text-[17px] leading-[1.85]`, Georgia serif |
| Stream complete | `SynthesisView.tsx` (lines 78, 101) | `bg-[#fef9f0]`, `text-[17px] leading-[1.85]`, Georgia serif |

## If styles diverge again

Keep these two files in sync:
- `frontend/components/deep-dive/SynthesisLoader.tsx` — streaming text div (~line 75–77)
- `frontend/components/deep-dive/SynthesisView.tsx` — response body div (~lines 78, 101)

The font size, line height, font family, and background must match exactly.

## No backend changes needed.
