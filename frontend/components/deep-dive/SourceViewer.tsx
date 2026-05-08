import React from 'react';
import { SearchResult } from '@/types/api';

function suttaCentralUrl(id: string): string {
  const suttaRef = id.split(':')[0].replace(/\s+/g, '').toLowerCase();
  return `https://suttacentral.net/${suttaRef}`;
}

interface SourceViewerProps {
  context: SearchResult[];
  activeRef?: string;
  onHighlight?: (ref: string) => void;
}

export function SourceViewer({ context, activeRef }: SourceViewerProps) {
  return (
    <div className="h-full overflow-y-auto p-6 space-y-8 font-serif text-black bg-gray-50">
      {context.length === 0 ? (
        <div className="text-gray-500 italic">No source verses found.</div>
      ) : (
        context.map((verse) => (
          <div
            key={verse.id}
            id={`verse-${verse.id.replace(/\s+/g, '-').toLowerCase()}`}
            className={`p-4 rounded-lg transition-all duration-300 border-l-4 ${
              activeRef === verse.id
                ? 'bg-yellow-100 border-yellow-500 shadow-sm'
                : 'bg-white border-transparent shadow-sm'
            }`}
          >
            <div className="text-xs font-bold mb-2 uppercase tracking-wider">
              <a
                href={suttaCentralUrl(verse.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                {verse.id}
              </a>
            </div>
            <div className="mb-3 text-lg leading-relaxed italic text-gray-800">
              {verse.pali}
            </div>
            <div className="text-md leading-relaxed text-gray-700">
              {verse.english}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
