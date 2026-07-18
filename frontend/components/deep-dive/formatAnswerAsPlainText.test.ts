import { describe, expect, it } from 'vitest';

import { SearchResult } from '@/types/api';

import { formatAnswerAsPlainText } from './formatAnswerAsPlainText';

const context: SearchResult[] = [
  { id: 'MN 27:14', english: 'lie english', score: 1, title: 'Cūḷahatthipadopamasutta The Shorter Discourse on the Elephant Footprint Simile' },
];

describe('formatAnswerAsPlainText', () => {
  it('strips bold and italic markdown markers', () => {
    const result = formatAnswerAsPlainText('This is **bold** and *italic* text.', []);
    expect(result).toBe('This is bold and italic text.');
  });

  it('expands a citation to ref plus sutta title when a matching context title exists', () => {
    const result = formatAnswerAsPlainText('A deliberate lie [MN 27:14].', context);
    expect(result).toBe(
      'A deliberate lie [MN 27:14 — Cūḷahatthipadopamasutta The Shorter Discourse on the Elephant Footprint Simile].'
    );
  });

  it('leaves a citation unexpanded when no matching context title exists', () => {
    const result = formatAnswerAsPlainText('Something [Unverified].', []);
    expect(result).toBe('Something [Unverified].');
  });
});
