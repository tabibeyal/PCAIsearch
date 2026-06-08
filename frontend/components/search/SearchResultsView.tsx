import React from 'react';
import { SearchResult } from '@/types/api';
import { dhammatalksUrl } from '@/lib/sourceUrl';

interface SearchResultsViewProps {
  results: SearchResult[];
  query: string;
}

export function SearchResultsView({ results }: SearchResultsViewProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-4" style={{ animation: 'fadeIn 300ms ease' }}>
      {results.length === 0 ? (
        <div className="text-center py-12 text-[#9c8c7a]">
          No results found for this query.
        </div>
      ) : (
        results.map((result) => {
          const url = dhammatalksUrl(result.id);
          const pct = Math.round(result.score * 100);
          return (
            <div
              key={result.id}
              className="bg-white border border-[#e8e4dc] rounded-xl p-[14px]"
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-2">
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-[#ede8df] text-[#6b4e35] text-xs font-medium px-2 py-0.5 rounded hover:underline"
                >
                  {result.id}
                </a>
                <span className="text-[#c8bfb5] text-xs">{pct}% match</span>
              </div>

              {result.pali && (
                <p className="italic text-[#9c8c7a] text-xs leading-[1.6] mb-2">
                  {result.pali}
                </p>
              )}

              <p
                className="border-l-2 border-[#e8e4dc] pl-4 text-[#6b5c4e] text-[13px] leading-[1.75] mb-2"
                style={{ fontFamily: 'Georgia, serif' }}
              >
                {result.english}
              </p>

              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#c8bfb5] underline text-[10px] hover:text-[#9c8c7a]"
              >
                View on dhammatalks.org
              </a>
            </div>
          );
        })
      )}
    </div>
  );
}
