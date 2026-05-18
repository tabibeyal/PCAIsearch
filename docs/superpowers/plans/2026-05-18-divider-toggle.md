# Divider Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a floating pill button on the divider between Answer and Sources panes that collapses/restores Sources without scrolling.

**Architecture:** New `DividerToggle` component, absolutely positioned relative to the outer container. A new `sourcesVisible` boolean in `DualPaneContainer` controls whether the Sources pane renders and where the toggle is anchored.

**Tech Stack:** React, TypeScript, Tailwind CSS, inline styles for conditional positioning.

---

## File map

| Action | File |
|--------|------|
| Create | `frontend/components/deep-dive/DividerToggle.tsx` |
| Modify | `frontend/components/deep-dive/DualPaneContainer.tsx` |

No backend changes. No new dependencies.

---

### Task 1: Create `DividerToggle` component

**Files:**
- Create: `frontend/components/deep-dive/DividerToggle.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/components/deep-dive/DividerToggle.tsx` with this exact content:

```tsx
interface DividerToggleProps {
  sourcesVisible: boolean;
  onClick: () => void;
}

export function DividerToggle({ sourcesVisible, onClick }: DividerToggleProps) {
  return (
    <button
      onClick={onClick}
      className="hidden md:flex absolute z-10 items-center justify-center text-[#6b4e35] cursor-pointer transition-colors hover:text-[#4a3728]"
      style={{
        top: '50%',
        transform: sourcesVisible ? 'translate(-50%, -50%)' : 'translateY(-50%)',
        left: sourcesVisible ? '50%' : undefined,
        right: sourcesVisible ? undefined : 0,
        width: 18,
        height: 36,
        background: '#faf9f7',
        border: '1.5px solid #6b4e35',
        borderRadius: sourcesVisible ? '10px' : '8px 0 0 8px',
        fontSize: 11,
        boxShadow: '0 1px 4px rgba(107,78,53,0.15)',
      }}
      aria-label={sourcesVisible ? 'Collapse sources' : 'Expand sources'}
    >
      {sourcesVisible ? '›' : '‹'}
    </button>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep DividerToggle
```

Expected: no output (no errors).

---

### Task 2: Wire toggle into `DualPaneContainer`

**Files:**
- Modify: `frontend/components/deep-dive/DualPaneContainer.tsx`

- [ ] **Step 1: Replace the file contents**

Replace `frontend/components/deep-dive/DualPaneContainer.tsx` with:

```tsx
'use client';

import React from 'react';
import { SynthesisView } from './SynthesisView';
import { SourceViewer } from './SourceViewer';
import { DividerToggle } from './DividerToggle';
import { SynthesisResponse } from '@/types/api';

interface DualPaneContainerProps {
  data: SynthesisResponse;
}

export function DualPaneContainer({ data }: DualPaneContainerProps) {
  const [deepDive, setDeepDive] = React.useState(false);
  const [sourcesVisible, setSourcesVisible] = React.useState(true);
  const [activeRef, setActiveRef] = React.useState<string | undefined>(undefined);

  const handleCitationClick = (ref: string) => {
    setActiveRef(ref);
    if (!deepDive) setDeepDive(true);
    setSourcesVisible(true); // always reopen sources when jumping to a citation
    const id = `verse-${ref.replace(/\s+/g, '-').toLowerCase()}`;
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  };

  const handleDeepDiveToggle = () => {
    if (deepDive) setSourcesVisible(true); // reset for next open
    setDeepDive((v) => !v);
  };

  const showSources = deepDive && sourcesVisible;

  return (
    <div className={`relative flex h-full w-full overflow-hidden bg-gray-200 ${deepDive ? 'flex-col md:flex-row' : ''}`}>
      <div className={`overflow-hidden shadow-xl transition-all duration-300 ${
        deepDive
          ? showSources
            ? 'w-full md:w-1/2 h-1/2 md:h-full border-b border-gray-300 md:border-b-0 md:border-r'
            : 'w-full h-full'
          : 'w-full h-full'
      }`}>
        <SynthesisView
          data={data}
          deepDive={deepDive}
          onDeepDiveToggle={handleDeepDiveToggle}
          onCitationClick={handleCitationClick}
        />
      </div>

      {deepDive && (
        <DividerToggle
          sourcesVisible={sourcesVisible}
          onClick={() => setSourcesVisible((v) => !v)}
        />
      )}

      {showSources && (
        <div className="w-full md:w-1/2 h-1/2 md:h-full overflow-hidden">
          <SourceViewer context={data.context} activeRef={activeRef} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: no output.

- [ ] **Step 3: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully` (or similar), no errors.

- [ ] **Step 4: Visual verification**

Start the dev server (`npm run dev` in `frontend/`), open a search result page, click "Deep Dive". Verify:

1. Pill appears centred on the divider, `›` visible, cream background with brown border
2. Click `›` — Sources pane collapses, Answer expands full width, pill moves to right edge showing `‹`
3. Click `‹` — Sources pane restores, pill returns to divider showing `›`
4. Click "Hide Sources" — exits Deep Dive entirely (no toggle visible)
5. Click "Deep Dive" again — Sources pane visible, toggle on divider
6. On mobile width — toggle not visible

- [ ] **Step 5: Commit**

```bash
git add frontend/components/deep-dive/DividerToggle.tsx frontend/components/deep-dive/DualPaneContainer.tsx
git commit -m "feat: add divider toggle to collapse/restore sources pane"
```
