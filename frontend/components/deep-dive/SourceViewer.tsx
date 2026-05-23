import React from 'react';
import { SearchResult } from '@/types/api';
import { suttaCentralUrl } from '@/lib/suttacentral';

interface SourceViewerProps {
  context: SearchResult[];
  activeRef?: string;
  onClose?: () => void;
}

export function SourceViewer({ context, activeRef, onClose }: SourceViewerProps) {
  return (
    <div className="h-full flex flex-col">
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="md:hidden flex-shrink-0 w-full flex items-center justify-center gap-2 py-2.5 bg-[#faf9f7] border-b-[1.5px] border-[#6b4e35] text-[#6b4e35] text-xs font-semibold tracking-widest uppercase"
          aria-label="Hide sources"
        >
          Sources <span className="text-sm leading-none">▾</span>
        </button>
      )}
      <div className="flex-1 overflow-y-auto scroll-smooth p-6 space-y-8 font-serif text-black bg-gray-50">
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
    </div>
  );
}
