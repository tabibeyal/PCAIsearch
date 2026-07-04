import React from 'react';

interface AnswerTextProps {
  text: string;
  onCitationClick: (ref: string) => void;
}

export function AnswerText({ text, onCitationClick }: AnswerTextProps) {
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

  const renderInline = (inlineText: string, pIdx: number): React.ReactNode[] => {
    const result: React.ReactNode[] = [];
    const re = /\*\*([^*]+)\*\*|\*([^*]+)\*|\[([A-Za-z\s\d:.,\-]+)\]/g;
    let last = 0;
    let seg = 0;
    let match;
    while ((match = re.exec(inlineText)) !== null) {
      if (match.index > last) result.push(<span key={`${pIdx}-t${seg++}`}>{inlineText.slice(last, match.index)}</span>);
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
    if (last < inlineText.length) result.push(<span key={`${pIdx}-t${seg}`}>{inlineText.slice(last)}</span>);
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

  return <>{text.split(/\n\n+/).map((block, pIdx) => renderBlock(block, pIdx))}</>;
}
