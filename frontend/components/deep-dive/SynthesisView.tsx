import React from 'react';
import { SynthesisResponse } from '@/types/api';
import { FeedbackBar } from './FeedbackBar';
import { AnswerActions } from './AnswerActions';
import { AnswerText } from './AnswerText';
import { SUPPORT_BANNER_SENTINEL_HEIGHT } from '@/lib/banner';

interface SynthesisViewProps {
  data: SynthesisResponse;
  deepDive: boolean;
  onDeepDiveToggle: () => void;
  onCitationClick: (ref: string) => void;
}

export function SynthesisView({ data, deepDive, onDeepDiveToggle, onCitationClick }: SynthesisViewProps) {
  const { answer, is_faithful, query, context, receipt } = data;

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
          <AnswerText text={answer} onCitationClick={onCitationClick} />
        </div>
        <AnswerActions query={query} answer={answer} context={context} receipt={receipt} />
        <FeedbackBar query={query} answer={answer} />
        {/* Sentinel: banner only shows on mobile when this clears the viewport bottom */}
        <div className={`${SUPPORT_BANNER_SENTINEL_HEIGHT} md:h-0`} aria-hidden="true" data-support-trigger />
      </div>
    </div>
  );
}
