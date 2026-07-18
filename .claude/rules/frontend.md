---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.vue"
  - "**/*.svelte"
  - "**/*.css"
  - "**/*.scss"
  - "**/*.html"
  - "**/components/**"
  - "**/pages/**"
  - "**/views/**"
  - "**/layouts/**"
  - "**/styles/**"
---

# Frontend

## Component Framework

Use whatever the project already has. Don't mix competing libraries.

| Category | In use | Options (don't introduce) |
|---|---|---|
| CSS | **Tailwind CSS v4** | vanilla CSS, CSS Modules, styled-components, Emotion, UnoCSS |
| Primitives | **none (custom components)** | shadcn/ui, Radix, Headless UI, Ark UI, DaisyUI, Mantine |
| Animation | **CSS transitions (Tailwind built-ins)** | Framer Motion, GSAP, View Transitions API, AutoAnimate |
| Charts | **none** | Recharts, D3, Chart.js, Visx, ECharts |
| Icons | **none** | Lucide, Phosphor, Heroicons, Tabler Icons, Iconify |
