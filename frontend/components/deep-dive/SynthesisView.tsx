import React from 'react';
import { SynthesisResponse } from '@/types/api';
import { FeedbackBar } from './FeedbackBar';
import { SUPPORT_BANNER_SENTINEL_HEIGHT } from '@/lib/banner';

interface SynthesisViewProps {
  data: SynthesisResponse;
  deepDive: boolean;
  onDeepDiveToggle: () => void;
  onCitationClick: (ref: string) => void;
}

export function SynthesisView({ data, deepDive, onDeepDiveToggle, onCitationClick }: SynthesisViewProps) {
  const { answer, is_faithful, query } = data;

  const renderCitation = (ref: string, key: React.Key) => {
    const lower = ref.toLowerCase();
    const isUnverified = lower.includes('unverified') || lower.includes('hallucinated');
    return (
      <button
        key={key}
        onClick={() => onCitationClick(ref)}
        title={isUnverified ? 'This citation could not be verified' : 'View source passage'}
        className={`mx-1 px-1.5 py-0.5 rounded font-medium transition-colors ${
          isUnverified
            ? 'bg-red-100 text-red-800 hover:bg-red-200 cursor-not-allowed text-xs'
            : 'bg-[#ede8df] text-[#6b4e35] hover:bg-[#e8e4dc] text-[11px] font-sans cursor-pointer underline decoration-dotted underline-offset-2'
        }`}
      >
        [{ref}]
      </button>
    );
  };

  const renderInline = (text: string, pIdx: number): React.ReactNode[] => {
    const result: React.ReactNode[] = [];
    const re = /\*\*([^*]+)\*\*|\*([^*]+)\*|\[([A-Za-z\s\d:.,\-]+)\]/g;
    let last = 0;
    let seg = 0;
    let match;
    while ((match = re.exec(text)) !== null) {
      if (match.index > last) result.push(<span key={`${pIdx}-t${seg++}`}>{text.slice(last, match.index)}</span>);
      if (match[1] !== undefined) {
        result.push(<strong key={`${pIdx}-b${seg}`}>{renderInline(match[1], pIdx * 100 + seg++)}</strong>);
      } else if (match[2] !== undefined) {
        result.push(<em key={`${pIdx}-i${seg}`}>{renderInline(match[2], pIdx * 100 + seg++)}</em>);
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
    const bulletLines = lines.filter(l => /^[\*\-•]\s/.test(l));
    if (bulletLines.length > 0 && bulletLines.length === lines.filter(l => l.trim()).length) {
      return (
        <ul key={pIdx} className="list-disc list-outside ml-5 mb-3 space-y-1">
          {bulletLines.map((line, i) => (
            <li key={i}>{renderInline(line.replace(/^[\*\-•]\s+/, ''), pIdx * 1000 + i)}</li>
          ))}
        </ul>
      );
    }
    return <p key={pIdx} className="mb-3">{renderInline(block, pIdx)}</p>;
  };

  const renderText = (text: string) =>
    text.split(/\n\n+/).map((block, pIdx) => renderBlock(block, pIdx));

  return (
    <div className="h-full overflow-y-auto scroll-smooth p-6 bg-[#faf9f7] text-[#2c1f14]">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-start justify-end gap-3 mb-6 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {!is_faithful && (
              <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded font-medium">
                Potential Hallucinations Flagged
              </span>
            )}
            <button
              onClick={onDeepDiveToggle}
              title="Show the source passages this answer is drawn from"
              className={`text-xs px-3 py-1 rounded font-medium border transition-colors ${
                deepDive
                  ? 'bg-[#4a3728] text-white border-[#4a3728] hover:bg-[#6b4e35]'
                  : 'bg-white text-[#6b4e35] border-[#e8e4dc] hover:bg-[#ede8df]'
              }`}
            >
              {deepDive ? 'Exit Deep Dive' : 'Deep Dive'}
            </button>
          </div>
        </div>

        <div
          className="text-[17px] leading-[1.85] text-[#2c1f14]"
          style={{ fontFamily: 'Georgia, serif' }}
        >
          {renderText(answer)}
        </div>
        <FeedbackBar query={query} answer={answer} />
        {/* Sentinel: banner only shows on mobile when this clears the viewport bottom */}
        <div className={`${SUPPORT_BANNER_SENTINEL_HEIGHT} md:h-0`} aria-hidden="true" data-support-trigger />
      </div>
    </div>
  );
}
