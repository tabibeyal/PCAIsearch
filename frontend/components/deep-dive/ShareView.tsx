'use client';

import React from 'react';
import { SearchResult } from '@/types/api';
import { AnswerText } from './AnswerText';
import { SourceViewer } from './SourceViewer';

interface ShareViewProps {
  query: string;
  answer: string;
  context: SearchResult[];
}

export function ShareView({ query, answer, context }: ShareViewProps) {
  const [activeRef, setActiveRef] = React.useState<string | undefined>(undefined);

  const handleCitationClick = (ref: string) => {
    setActiveRef(ref);
    const id = `verse-${ref.replace(/\s+/g, '-').toLowerCase()}`;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="flex flex-col md:flex-row h-full w-full overflow-hidden bg-[#e8e4dc]">
      <div className="w-full md:w-1/2 h-1/2 md:h-full overflow-hidden border-b md:border-b-0 md:border-r border-[#e8e4dc]">
        <div className="h-full overflow-y-auto scroll-smooth p-6 bg-[#faf9f7] text-[#2c1f14]">
          <div className="max-w-2xl mx-auto">
            <p className="text-xs text-[#76604a] mb-1 font-sans uppercase tracking-wide">Shared answer</p>
            <h1 className="text-lg font-semibold mb-4 font-sans text-[#2c1f14]">{query}</h1>
            <div className="text-[17px] leading-[1.85]" style={{ fontFamily: 'Georgia, serif' }}>
              <AnswerText text={answer} onCitationClick={handleCitationClick} />
            </div>
          </div>
        </div>
      </div>
      <div className="w-full md:w-1/2 h-1/2 md:h-full overflow-hidden">
        <SourceViewer context={context} activeRef={activeRef} />
      </div>
    </div>
  );
}
