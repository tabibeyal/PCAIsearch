import { describe, expect, it } from 'vitest';

import { formatQuestionForBanner } from './bannerQuestion';

describe('formatQuestionForBanner', () => {
  it('returns short questions unchanged', () => {
    expect(formatQuestionForBanner('What did the Buddha say about anger?')).toBe(
      'What did the Buddha say about anger?'
    );
  });

  it('returns a boundary-length question (exactly 100 chars) unchanged', () => {
    const exact = 'a'.repeat(100);
    expect(formatQuestionForBanner(exact)).toBe(exact);
  });

  it('truncates long questions to 100 chars and appends an ellipsis', () => {
    const long = 'a'.repeat(150);
    const out = formatQuestionForBanner(long);
    expect(out.length).toBe(101);
    expect(out.endsWith('…')).toBe(true);
    expect(out.startsWith('a'.repeat(100))).toBe(true);
  });

  it('trims surrounding whitespace before measuring length', () => {
    const padded = '   ' + 'a'.repeat(100) + 'b' + '   ';
    const out = formatQuestionForBanner(padded);
    expect(out.endsWith('…')).toBe(true);
    expect(out).toBe('a'.repeat(100) + '…');
  });
});
