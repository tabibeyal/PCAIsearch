import { describe, expect, it } from 'vitest';
import { isCommentaryResult } from '@/lib/commentary';
import { SearchResult } from '@/types/api';

function makeResult(section?: string): SearchResult {
  return { id: 'dn1:5', pali: '', english: '…', score: 0.9, section };
}

describe('isCommentaryResult', () => {
  it('returns true for a chunk the API flagged as commentary', () => {
    expect(isCommentaryResult(makeResult('commentary'))).toBe(true);
  });

  it('returns false for a canon chunk with no section marker', () => {
    expect(isCommentaryResult(makeResult(undefined))).toBe(false);
  });

  it('returns false for any section value other than commentary', () => {
    expect(isCommentaryResult(makeResult('canon'))).toBe(false);
  });
});