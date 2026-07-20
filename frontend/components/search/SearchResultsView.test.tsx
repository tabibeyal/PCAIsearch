import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { SearchResultsView } from './SearchResultsView';
import { SearchResult } from '@/types/api';

function makeResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return { id: 'MN 27:14', english: 'passage text', score: 0.9, ...overrides };
}

describe('SearchResultsView weak-pool notice', () => {
  it('renders the notice when isWeakPool is true', () => {
    const html = renderToStaticMarkup(
      <SearchResultsView results={[makeResult()]} isWeakPool={true} />
    );
    expect(html).toContain('No strong matches');
  });

  it('does not render the notice when isWeakPool is false', () => {
    const html = renderToStaticMarkup(
      <SearchResultsView results={[makeResult()]} isWeakPool={false} />
    );
    expect(html).not.toContain('No strong matches');
  });

  it('does not render the notice when isWeakPool is omitted', () => {
    const html = renderToStaticMarkup(<SearchResultsView results={[makeResult()]} />);
    expect(html).not.toContain('No strong matches');
  });

  it('does not render the notice on the empty-results state even if isWeakPool is true', () => {
    const html = renderToStaticMarkup(<SearchResultsView results={[]} isWeakPool={true} />);
    expect(html).not.toContain('No strong matches');
  });
});

describe('SearchResultsView match percentage', () => {
  it('renders a percentage for an organic result with a score', () => {
    const html = renderToStaticMarkup(
      <SearchResultsView results={[makeResult({ score: 0.75, is_guarantee_filler: false })]} isWeakPool={false} />
    );
    expect(html).toContain('75% match');
  });

  it('renders no percentage for an organic result with a null score (weak pool)', () => {
    const html = renderToStaticMarkup(
      <SearchResultsView results={[makeResult({ score: null, is_guarantee_filler: false })]} isWeakPool={true} />
    );
    expect(html).not.toContain('% match');
  });

  it('renders the filler badge instead of a percentage for a filler result under a weak pool', () => {
    const html = renderToStaticMarkup(
      <SearchResultsView
        results={[makeResult({ score: null, is_guarantee_filler: true, id: 'DN 1:1' })]}
        isWeakPool={true}
      />
    );
    expect(html).toContain('Included for DN');
    expect(html).not.toContain('% match');
  });
});
