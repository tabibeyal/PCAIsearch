'use client';

import React from 'react';
import { streamSynthesis } from '@/lib/api';
import { DualPaneContainer } from './DualPaneContainer';
import { SynthesisResponse } from '@/types/api';
import { stripThinking } from '@/lib/utils';

function LoadingState({ status }: { status: string }) {
  return (
    <div className="flex items-center justify-center h-full text-[#9c8c7a]">
      <div className="text-center">
        <div className="w-8 h-8 rounded-full animate-spin mx-auto mb-3" style={{ border: '2px solid #e8e4dc', borderTopColor: '#6b4e35' }} />
        <p className="text-sm">{status}</p>
      </div>
    </div>
  );
}

function ErrorMessage({ isRateLimit, detail }: { isRateLimit: boolean; detail?: string }) {
  return (
    <div className="flex items-center justify-center p-8 text-red-500 text-center">
      <div>
        <h2 className="text-xl font-bold mb-2">
          {isRateLimit ? 'Rate Limit Exceeded' : 'Search Error'}
        </h2>
        <p>
          {isRateLimit
            ? 'You have sent too many requests. Please wait a moment and try again.'
            : 'Unable to retrieve search data for this query. Please check if the backend is running.'}
        </p>
        {detail && <p className="mt-2 text-sm text-red-400 font-mono">{detail}</p>}
        <a href="/" className="mt-4 inline-block text-[#6b4e35] underline">Return to home</a>
      </div>
    </div>
  );
}

export function SynthesisLoader({ query, nikayas }: { query: string; nikayas?: string[] }) {
  const [streamText, setStreamText] = React.useState('');
  const [status, setStatus] = React.useState('Searching the Canon…');
  const [data, setData] = React.useState<SynthesisResponse | null>(null);
  const [error, setError] = React.useState<{ status?: number } | null>(null);

  React.useEffect(() => {
    setStreamText('');
    setStatus('Searching the Canon…');
    setData(null);
    setError(null);
    let cancelled = false;
    (async () => {
      try {
        for await (const event of streamSynthesis(query, nikayas)) {
          if (cancelled) break;
          if (event.type === 'status') setStatus(event.text);
          else if (event.type === 'chunk') setStreamText(t => t + event.text);
          else if (event.type === 'done') setData(event as SynthesisResponse);
          else if (event.type === 'error') throw Object.assign(new Error(event.message), { status: 500 });
        }
      } catch (e: any) {
        if (!cancelled) setError(e);
      }
    })();
    return () => { cancelled = true; };
  }, [query, nikayas?.join(',')]);

  const visible = streamText ? stripThinking(streamText) : '';

  if (error) return <ErrorMessage isRateLimit={error.status === 429} detail={(error as any).message} />;

  if (data) return <DualPaneContainer data={data} />;

  if (visible) {
    return (
      <div className="h-full overflow-y-auto p-6 bg-[#faf9f7]">
        <div className="max-w-2xl mx-auto">
          <div className="text-[15px] leading-[1.85] whitespace-pre-wrap text-[#1a1a1a]" style={{ fontFamily: 'Georgia, serif' }}>
            {visible.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((seg, i) =>
              seg.startsWith('**') && seg.endsWith('**')
                ? <strong key={i}>{seg.slice(2, -2)}</strong>
                : seg.startsWith('*') && seg.endsWith('*')
                  ? <em key={i}>{seg.slice(1, -1)}</em>
                  : seg
            )}
            <span className="inline-block w-0.5 h-5 animate-pulse ml-0.5 align-middle" style={{ backgroundColor: '#6b4e35' }} />
          </div>
        </div>
      </div>
    );
  }

  return <LoadingState status={status} />;
}
