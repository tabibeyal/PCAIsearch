'use client';

import React from 'react';
import { searchVerses } from '@/lib/api';
import { SearchResultsView } from './SearchResultsView';
import { SearchResult } from '@/types/api';

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full text-[#9c8c7a]">
      <div className="text-center">
        <div className="w-8 h-8 rounded-full animate-spin mx-auto mb-3" style={{ border: '2px solid #e8e4dc', borderTopColor: '#6b4e35' }} />
        <p className="text-sm">Searching the Canon…</p>
      </div>
    </div>
  );
}

function ErrorState({ isRateLimit, onRetry }: { isRateLimit: boolean; onRetry: () => void }) {
  return (
    <div className="flex items-center justify-center p-8 text-red-500 text-center">
      <div>
        <h2 className="text-xl font-bold mb-2">{isRateLimit ? 'Rate Limit Exceeded' : 'Search Error'}</h2>
        <p>{isRateLimit ? 'You have sent too many requests. Please wait a moment and try again.' : 'Unable to retrieve passages for this query.'}</p>
        {!isRateLimit && (
          <button
            onClick={onRetry}
            className="mt-4 text-[#6b4e35] border border-[#6b4e35] px-3 py-1.5 rounded text-sm hover:bg-[#ede8df] transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function SearchResultsLoader({ query, nikayas }: { query: string; nikayas: string[] }) {
  const [results, setResults] = React.useState<SearchResult[] | null>(null);
  const [error, setError] = React.useState<{ status?: number } | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);

  React.useEffect(() => {
    setResults(null);
    setError(null);

    let cancelled = false;
    const controller = new AbortController();

    (async () => {
      try {
        const data = await searchVerses(query, 20, nikayas.length ? nikayas : undefined, controller.signal);
        if (!cancelled) setResults(data.results);
      } catch (e: any) {
        if (!cancelled && e.name !== 'AbortError') setError(e);
      }
    })();

    return () => { cancelled = true; controller.abort(); };
  }, [query, nikayas.join(','), retryCount]);

  if (error) return <ErrorState isRateLimit={error.status === 429} onRetry={() => setRetryCount(c => c + 1)} />;
  if (!results) return <LoadingState />;
  return <SearchResultsView results={results} query={query} />;
}
