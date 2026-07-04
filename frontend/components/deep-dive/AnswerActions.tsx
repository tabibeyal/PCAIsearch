'use client';

import React from 'react';

import { shareAnswer } from '@/lib/api';
import { SearchResult } from '@/types/api';

import { formatAnswerAsPlainText } from './formatAnswerAsPlainText';

type ButtonStatus = 'idle' | 'success' | 'error';

interface AnswerActionsProps {
  query: string;
  answer: string;
  context: SearchResult[];
  receipt: string;
}

function useTemporaryStatus(): [ButtonStatus, (status: ButtonStatus) => void] {
  const [status, setStatus] = React.useState<ButtonStatus>('idle');
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const setTemporaryStatus = (next: ButtonStatus) => {
    setStatus(next);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setStatus('idle'), 2000);
  };

  return [status, setTemporaryStatus];
}

export function AnswerActions({ query, answer, context, receipt }: AnswerActionsProps) {
  const [copyStatus, setCopyStatus] = useTemporaryStatus();
  const [shareStatus, setShareStatus] = useTemporaryStatus();

  const handleCopy = async () => {
    try {
      const plainText = formatAnswerAsPlainText(answer, context);
      await navigator.clipboard.writeText(plainText);
      setCopyStatus('success');
    } catch (e) {
      console.error('Copy to clipboard failed', e);
      setCopyStatus('error');
    }
  };

  const handleShare = async () => {
    try {
      const { id } = await shareAnswer({ query, answer, context, receipt });
      const url = `${window.location.origin}/share/${id}`;
      await navigator.clipboard.writeText(url);
      setShareStatus('success');
    } catch (e) {
      console.error('Share failed', e);
      setShareStatus('error');
    }
  };

  const copyLabel = copyStatus === 'success' ? 'Copied!' : copyStatus === 'error' ? "Couldn't copy" : 'Copy';
  const shareLabel = shareStatus === 'success' ? 'Link copied!' : shareStatus === 'error' ? "Couldn't share" : 'Share';

  return (
    <div className="border-t border-[#e8e4dc] pt-3 mt-6 flex items-center gap-2 font-sans">
      <button
        type="button"
        onClick={handleCopy}
        className="border border-[#e8e4dc] rounded-md px-2.5 py-1.5 text-xs font-medium text-[#6b4e35] bg-white hover:bg-[#ede8df] transition-colors"
      >
        {copyLabel}
      </button>
      <button
        type="button"
        onClick={handleShare}
        className="border border-[#e8e4dc] rounded-md px-2.5 py-1.5 text-xs font-medium text-[#6b4e35] bg-white hover:bg-[#ede8df] transition-colors"
      >
        {shareLabel}
      </button>
    </div>
  );
}
