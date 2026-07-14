import React from 'react';
import { SearchResult } from '@/types/api';
import { dhammatalksUrl } from '@/lib/sourceUrl';
import { isCommentaryResult } from '@/lib/commentary';

interface SearchResultsViewProps {
  results: SearchResult[];
}

export function SearchResultsView({ results }: SearchResultsViewProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-4" style={{ animation: 'fadeIn 300ms ease' }}>
      {results.length === 0 ? (
        <div className="text-center py-12 text-[#76604a]">
          No suttas matched your search. Try rephrasing your question, or clear the Nikāya filter to search all collections.
        </div>
      ) : (
        results.map((result) => {
          const url = dhammatalksUrl(result.id);
          const rawScore = Number.isFinite(result.score) ? result.score : 0;
          const pct = Math.round(rawScore * 100);
          const isCommentary = isCommentaryResult(result);
          return (
            <div
              key={result.id}
              className="bg-white border border-[#e8e4dc] rounded-xl p-[14px]"
            >
              {(result.title_english || result.title_pali) && (
                <div className="mb-2">
                  {result.title_english && (
                    <div className="text-base font-semibold text-[#2c1f14]">
                      {result.title_english}
                    </div>
                  )}
                  {result.title_pali && (
                    <div className="text-sm italic text-[#76604a]">
                      {result.title_pali}
                    </div>
                  )}
                </div>
              )}
              {isCommentary && (
                <div className="mb-2">
                  <span className="inline-flex items-center gap-1 bg-white border border-[#6b4e35] text-[#6b4e35] text-xs font-medium px-2 py-0.5 rounded">
                    <span aria-hidden="true">✎</span>
                    Translator&apos;s introduction
                  </span>
                </div>
              )}
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
                <span className="text-[#76604a] text-xs">{pct}% match</span>
              </div>

              {result.pali && (
                <p className="italic text-[#76604a] text-xs leading-[1.6] mb-2">
                  {result.pali}
                </p>
              )}

              <p
                className="text-[#6b5c4e] text-[13px] leading-[1.75] mb-2"
                style={{ fontFamily: 'Georgia, serif' }}
              >
                {result.english}
              </p>

              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#76604a] underline text-[11px] hover:text-[#6b4e35]"
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
