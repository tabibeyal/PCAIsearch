'use client';

import React from 'react';
import { submitFeedback } from '@/lib/api';

const CATEGORIES = [
  'Doctrinally inaccurate',
  'Missing important nuance',
  'Not relevant to my question',
  "Sources don't support the answer",
  'Too vague',
] as const;

interface FeedbackBarProps {
  query: string;
  answer: string;
}

export function FeedbackBar({ query, answer }: FeedbackBarProps) {
  const [rating, setRating] = React.useState<'up' | 'down' | null>(null);
  const [panelOpen, setPanelOpen] = React.useState(false);
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null);
  const [comment, setComment] = React.useState('');
  const [submitted, setSubmitted] = React.useState(false);
  const [submittedFadeIn, setSubmittedFadeIn] = React.useState(false);

  React.useEffect(() => {
    if (submitted) {
      requestAnimationFrame(() => requestAnimationFrame(() => setSubmittedFadeIn(true)));
    }
  }, [submitted]);

  const handleThumbsUp = async () => {
    if (submitted) return;
    setRating('up');
    setSubmitted(true);
    try {
      await submitFeedback({ query, answer, rating: 'up', category: null, comment: null });
    } catch {
      // feedback is optional — ignore submission failures
    }
  };

  const handleThumbsDown = () => {
    if (submitted) return;
    setRating('down');
    setPanelOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitted(true);
    setPanelOpen(false);
    try {
      await submitFeedback({
        query,
        answer,
        rating: 'down',
        category: selectedCategory,
        comment: comment || null,
      });
    } catch {
      // feedback is optional — ignore submission failures
    }
  };

  return (
    <div className="border-t border-[#e8e4dc] pt-3 mt-6 relative">

      {/* Fix 4: buttons + panel fade out when submitted */}
      <div style={{ opacity: submitted ? 0 : 1, transition: 'opacity 150ms ease', pointerEvents: submitted ? 'none' : 'auto' }}>
        <div className="flex items-center gap-3 mb-1.5">
          <span className="text-xs text-[#76604a] font-sans">Was this helpful?</span>
          <button
            onClick={handleThumbsUp}
            className={`border rounded-md px-2.5 py-1.5 text-base transition-colors ${
              rating === 'up'
                ? 'bg-[#4a3728] border-[#4a3728] text-white'
                : 'bg-white border-[#e8e4dc] text-[#6b4e35] hover:bg-[#ede8df]'
            }`}
          >
            👍
          </button>
          <button
            onClick={handleThumbsDown}
            className={`border rounded-md px-2.5 py-1.5 text-base transition-colors ${
              rating === 'down'
                ? 'bg-[#4a3728] border-[#4a3728] text-white'
                : 'bg-white border-[#e8e4dc] text-[#6b4e35] hover:bg-[#ede8df]'
            }`}
          >
            👎
          </button>
        </div>
        <p className="text-[11px] text-[#76604a] font-sans italic mb-3">
          Feedback includes your question and this full answer.
        </p>

        {/* Fix 3: panel animates in on mount; exits by unmounting (no layout ghost) */}
        {panelOpen && (
          <div
            className="bg-white border border-[#e8e4dc] rounded-lg p-4 font-sans"
            style={{ animation: 'fadeUp 300ms cubic-bezier(0.22, 1, 0.36, 1) forwards' }}
          >
            <div className="flex items-center justify-between mb-2.5">
              <p className="text-xs font-semibold text-[#4a3728]">What was the problem?</p>
              <button
                onClick={() => { setPanelOpen(false); setRating(null); }}
                className="text-[#76604a] hover:text-[#4a3728] text-sm leading-none"
                aria-label="Dismiss feedback panel"
              >
                ×
              </button>
            </div>
            <div className="flex flex-wrap gap-2 mb-3.5">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                  className={`border rounded-full px-3 py-1 text-xs transition-colors ${
                    selectedCategory === cat
                      ? 'bg-[#ede8df] border-[#c8b89a] text-[#6b4e35]'
                      : 'bg-white border-[#c8b89a] text-[#6b4e35] hover:bg-[#f5f0e8]'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment (optional)"
              className="w-full border border-[#e8e4dc] rounded-md p-2 text-xs text-[#4a3728] resize-none h-14 font-sans"
            />
            <div className="flex justify-end mt-2.5">
              <button
                onClick={handleSubmit}
                aria-label="Submit feedback"
                className="bg-[#4a3728] text-white border-none rounded-md p-2 flex items-center justify-center hover:bg-[#6b4e35] transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Fix 4: thank-you fades in over the buttons area */}
      {submitted && (
        <div
          className="absolute top-0 left-0 flex items-center gap-3"
          style={{
            opacity: submittedFadeIn ? 1 : 0,
            transform: submittedFadeIn ? 'translateY(0)' : 'translateY(4px)',
            transition: 'opacity 200ms ease, transform 200ms ease',
          }}
        >
          <span className="text-xs text-[#76604a] font-sans">Thank you for your feedback.</span>
          <button
            disabled
            className="border rounded-md px-2.5 py-1.5 text-base opacity-60 cursor-default bg-[#4a3728] border-[#4a3728] text-white"
          >
            {rating === 'up' ? '👍' : '👎'}
          </button>
        </div>
      )}
    </div>
  );
}
