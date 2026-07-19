import { describe, expect, it } from 'vitest';
import { isGuaranteeFillerResult } from '@/lib/guaranteeFiller';
import { SearchResult } from '@/types/api';

function makeResult(is_guarantee_filler?: boolean): SearchResult {
  return { id: 'mn27:14', english: '…', score: 0.9, is_guarantee_filler };
}

describe('isGuaranteeFillerResult', () => {
  it('returns true for a result flagged as guarantee filler', () => {
    expect(isGuaranteeFillerResult(makeResult(true))).toBe(true);
  });

  it('returns false for an organic result flagged false', () => {
    expect(isGuaranteeFillerResult(makeResult(false))).toBe(false);
  });

  it('returns false when the flag is absent (organic by default)', () => {
    expect(isGuaranteeFillerResult(makeResult(undefined))).toBe(false);
  });
});