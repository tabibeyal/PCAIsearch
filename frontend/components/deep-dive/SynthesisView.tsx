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

  const renderInline = (text: string, pIdx: number) => {
    const parts = text.split(citationRegex);
    return parts.map((part, index) => {
      if (index % 2 !== 0) {
        const refs = part.split(',').map(r => r.trim()).filter(Boolean);
        return refs.length === 1
          ? renderCitation(refs[0], `${pIdx}-${index}`)
          : <span key={`${pIdx}-${index}`}>{refs.map((r, i) => renderCitation(r, `${pIdx}-${index}-${i}`))}</span>;
      }
      return <span key={`${pIdx}-${index}`}>{part}</span>;
    });
  };

  const renderBlock = (block: string, pIdx: number) => {
    const lines = block.split('\n');
    const bulletLines = lines.filter(l => /^[\*\-]\s/.test(l));
    if (bulletLines.length > 0 && bulletLines.length === lines.filter(l => l.trim()).length) {
      return (
        <ul key={pIdx} className="list-disc list-outside ml-5 mb-3 space-y-1">
          {bulletLines.map((line, i) => (
            <li key={i}>{renderInline(line.replace(/^[\*\-]\s+/, ''), pIdx * 1000 + i)}</li>
          ))}
        </ul>
      );
    }
    return <p key={pIdx} className="mb-3">{renderInline(block, pIdx)}</p>;
  };

  const renderText = (text: string) =>
    text.split(/\n\n+/).map((block, pIdx) => renderBlock(block, pIdx));

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

        <div className="text-lg leading-relaxed text-gray-800">
          {renderText(answer)}
        </div>
      </div>
    </div>
  );
}
