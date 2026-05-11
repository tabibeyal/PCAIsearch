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

  const renderInline = (text: string, pIdx: number): React.ReactNode[] => {
    const result: React.ReactNode[] = [];
    const re = /\*\*([^*]+)\*\*|\*([^*]+)\*|\[([A-Z\s\d:.,]+)\]/g;
    let last = 0;
    let seg = 0;
    let match;
    while ((match = re.exec(text)) !== null) {
      if (match.index > last) result.push(<span key={`${pIdx}-t${seg++}`}>{text.slice(last, match.index)}</span>);
      if (match[1] !== undefined) {
        result.push(<strong key={`${pIdx}-b${seg++}`}>{match[1]}</strong>);
      } else if (match[2] !== undefined) {
        result.push(<em key={`${pIdx}-i${seg++}`}>{match[2]}</em>);
      } else {
        const refs = match[3].split(',').map(r => r.trim()).filter(Boolean);
        result.push(
          refs.length === 1
            ? renderCitation(refs[0], `${pIdx}-c${seg++}`)
            : <span key={`${pIdx}-c${seg++}`}>{refs.map((r, i) => renderCitation(r, `${pIdx}-c${seg}-${i}`))}</span>
        );
      }
      last = match.index + match[0].length;
    }
    if (last < text.length) result.push(<span key={`${pIdx}-t${seg}`}>{text.slice(last)}</span>);
    return result;
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
    <div className="h-full overflow-y-auto scroll-smooth p-6 bg-white text-black">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-start justify-between gap-3 mb-6 flex-wrap">
          <h2 className="text-xl font-semibold">Synthesized Answer</h2>
          <div className="flex items-center gap-2 flex-wrap">
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
