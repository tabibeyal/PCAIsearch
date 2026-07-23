import { describe, expect, it } from 'vitest';

import { staleViewRedirectTarget } from './staleViewRedirect';

describe('staleViewRedirectTarget', () => {
  it('returns null when no view param is present', () => {
    expect(staleViewRedirectTarget(undefined, [], 'anger')).toBeNull();
  });

  it('targets the bare path when view is present and there are no nikayas', () => {
    expect(staleViewRedirectTarget('results', [], 'anger')).toBe('/search/anger');
  });

  it('preserves nikayas in the redirect target', () => {
    expect(staleViewRedirectTarget('results', ['mn', 'an'], 'anger')).toBe(
      '/search/anger?nikayas=mn&nikayas=an',
    );
  });

  it('strips view even when its value is synthesis', () => {
    expect(staleViewRedirectTarget('synthesis', [], 'anger')).toBe('/search/anger');
  });
});