import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';

import { SearchResult } from '@/types/api';
import { SourceViewer } from './SourceViewer';

// Server-rendering the real SourceViewer exercises its `hasTitle` branch
// without a DOM — the closest thing to a render seam this leaf component has.
// The synthesize e2e flow stays manually verified (#87); this covers only the
// per-source title block vs. ID-only fallback.

describe('SourceViewer title rendering', () => {
  it('renders only the ID link when a source has no title', () => {
    const context: SearchResult[] = [
      { id: 'MN 1:5', english: 'body text', score: 1 },
    ];

    const html = renderToStaticMarkup(<SourceViewer context={context} />);

    expect(html).toContain('MN 1:5');
    expect(html).not.toContain('font-semibold text-[#2c1f14]');
    expect(html).not.toContain('italic text-[#76604a]');
  });

  it('renders the English title, italic Pāli title, and ID tag when a source has a title', () => {
    const context: SearchResult[] = [
      {
        id: 'MN 27:14',
        english: 'body text',
        score: 1,
        title_pali: 'Cūḷahatthipadopamasutta',
        title_english: 'The Shorter Discourse on the Elephant Footprint Simile',
      },
    ];

    const html = renderToStaticMarkup(<SourceViewer context={context} />);

    expect(html).toContain('The Shorter Discourse on the Elephant Footprint Simile');
    expect(html).toContain('italic text-[#76604a]');
    expect(html).toContain('Cūḷahatthipadopamasutta');
    expect(html).toContain('MN 27:14');
  });
});