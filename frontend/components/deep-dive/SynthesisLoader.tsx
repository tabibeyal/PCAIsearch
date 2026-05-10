'use client';

import React from 'react';
import { streamSynthesis } from '@/lib/api';
import { DualPaneContainer } from './DualPaneContainer';
import { SynthesisResponse } from '@/types/api';

const THINK_RE = /<think>[\s\S]*?<\/think>/gi;

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full text-gray-400">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm">Searching the Canon…</p>
      </div>
    </div>
  );
}

function ErrorMessage({ isRateLimit }: { isRateLimit: boolean }) {
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
        <a href="/" className="mt-4 inline-block text-blue-600 underline">Return to home</a>
      </div>
    </div>
  );
}

export function SynthesisLoader({ query }: { query: string }) {
  const [streamText, setStreamText] = React.useState('');
  const [data, setData] = React.useState<SynthesisResponse | null>(null);
  const [error, setError] = React.useState<{ status?: number } | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        for await (const event of streamSynthesis(query)) {
          if (cancelled) break;
          if (event.type === 'chunk') setStreamText(t => t + event.text);
          else if (event.type === 'done') setData(event as SynthesisResponse);
        }
      } catch (e: any) {
        if (!cancelled) setError(e);
      }
    })();
    return () => { cancelled = true; };
  }, [query]);

  if (error) return <ErrorMessage isRateLimit={error.status === 429} />;

  if (data) return <DualPaneContainer data={data} />;

  if (streamText) {
    const visible = streamText.replace(THINK_RE, '').trim();
    return (
      <div className="h-full overflow-y-auto p-6 bg-white">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-xl font-semibold mb-6">Synthesized Answer</h2>
          <div className="text-lg leading-relaxed whitespace-pre-wrap text-gray-800">
            {visible}
            <span className="inline-block w-0.5 h-5 bg-blue-500 animate-pulse ml-0.5 align-middle" />
          </div>
        </div>
      </div>
    );
  }

  return <LoadingState />;
}
