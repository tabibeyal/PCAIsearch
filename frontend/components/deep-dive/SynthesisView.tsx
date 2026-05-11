import React from 'react';
import { SynthesisResponse } from '@/types/api';

interface SynthesisViewProps {
  data: SynthesisResponse;
  deepDive: boolean;
  onDeepDiveToggle: () => void;
  onCitationClick: (ref: string) => void;
}

export function SynthesisView({ data, deepDive, onDeepDiveToggle, onCitationClick }: SynthesisViewProps) {
  const { answer, is_faithful } = data;

  const citationRegex = /\[([A-Z\s\d:.,]+)\]/g;

  const renderCitation = (ref: string, key: React.Key) => {
    const lower = ref.toLowerCase();
    const isUnverified = lower.includes('unverified') || lower.includes('hallucinated');
    return (
      <button
        key={key}
        onClick={() => onCitationClick(ref)}
        className={`mx-1 px-1.5 py-0.5 rounded text-xs font-medium transition-colors ${
          isUnverified
            ? 'bg-red-100 text-red-600 hover:bg-red-200 cursor-not-allowed'
            : 'bg-blue-100 text-blue-700 hover:bg-blue-200 underline decoration-blue-300'
        }`}
      >
        [{ref}]
      </button>
    );
  };

  const renderText = (text: string) => {
    const parts = text.split(citationRegex);
    return parts.map((part, index) => {
      if (index % 2 !== 0) {
        const refs = part.split(',').map(r => r.trim()).filter(Boolean);
        return refs.length === 1
          ? renderCitation(refs[0], index)
          : <span key={index}>{refs.map((r, i) => renderCitation(r, i))}</span>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="h-full overflow-y-auto p-6 bg-white text-black">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Synthesized Answer</h2>
          <div className="flex items-center gap-2">
            {!is_faithful && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
                ⚠️ Potential Hallucinations Flagged
              </span>
            )}
            <button
              onClick={onDeepDiveToggle}
              className={`text-xs px-3 py-1 rounded font-medium border transition-colors ${
                deepDive
                  ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700'
                  : 'bg-white text-blue-600 border-blue-300 hover:bg-blue-50'
              }`}
            >
              {deepDive ? 'Hide Sources' : 'Deep Dive'}
            </button>
          </div>
        </div>

        <div className="text-lg leading-relaxed whitespace-pre-wrap text-gray-800">
          {renderText(answer)}
        </div>
      </div>
    </div>
  );
}
