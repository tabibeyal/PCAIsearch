import React from 'react';
import { SearchResult } from '@/types/api';
import { suttaCentralUrl } from '@/lib/suttacentral';

interface SearchResultsViewProps {
  results: SearchResult[];
  query: string;
}

export function SearchResultsView({ results, query }: SearchResultsViewProps) {
  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-8">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-semibold text-gray-800">Search Results</h1>
        <p className="text-gray-500">Found {results.length} relevant verses for "{query}"</p>
      </header>

      <div className="space-y-6">
        {results.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No results found for this query.
          </div>
        ) : (
          results.map((result, index) => (
            <div
              key={result.id}
              className="p-4 rounded-lg border border-gray-200 bg-white hover:border-blue-300 transition-colors shadow-sm"
            >
              <div className="flex justify-between items-start gap-2 flex-wrap mb-2">
                <a
                  href={suttaCentralUrl(result.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-blue-600 hover:underline bg-blue-50 px-2 py-1 rounded"
                >
                  {result.id}
                </a>
                <span className="text-xs text-gray-400">
                  Score: {result.score.toFixed(4)}
                </span>
              </div>
              <div className="space-y-3">
                <div className="font-serif text-lg text-gray-900 leading-relaxed">
                  {result.pali}
                </div>
                <div className="text-gray-600 italic leading-relaxed border-l-2 border-gray-200 pl-4">
                  {result.english}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
