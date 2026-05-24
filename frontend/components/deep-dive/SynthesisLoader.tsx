'use client';

import React from 'react';
import { streamSynthesis } from '@/lib/api';
import { DualPaneContainer } from './DualPaneContainer';
import { SynthesisResponse } from '@/types/api';
import { stripThinking } from '@/lib/utils';

const STEPS = [
  { key: 'searching', label: 'Searching the Canon', trigger: 'Searching the Canon…' },
  { key: 'composing', label: 'Composing answer',    trigger: 'Composing answer…'    },
  { key: 'verifying', label: 'Verifying sources',   trigger: 'Verifying sources…'   },
] as const;

type StepState = 'pending' | 'active' | 'done';

function getStepState(index: number, activeIndex: number): StepState {
  if (index < activeIndex) return 'done';
  if (index === activeIndex) return 'active';
  return 'pending';
}

function StepIcon({ state, size = 20 }: { state: StepState; size?: number }) {
  if (state === 'done') {
    return (
      <div style={{ width: size, height: size, borderRadius: '50%', background: '#6b4e35', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <span style={{ color: 'white', fontSize: 10 }}>✓</span>
      </div>
    );
  }
  if (state === 'active') {
    return (
      <div
        className="animate-spin"
        style={{ width: size, height: size, borderRadius: '50%', border: '2px solid #6b4e35', borderTopColor: 'transparent', flexShrink: 0 }}
      />
    );
  }
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', border: '1.5px solid #9c8c7a', flexShrink: 0 }} />
  );
}

// horizontal=true is used by the streaming view (sidebar/topbar layout)
function StepList({ currentStatus, horizontal = false }: { currentStatus: string; horizontal?: boolean }) {
  const activeIndex = Math.max(0, STEPS.findIndex(s => s.trigger === currentStatus));

  if (horizontal) {
    return (
      <div className="flex items-center gap-3 px-4 py-2 bg-[#faf9f7] border-b border-[#e8e4dc]">
        {STEPS.map((step, i) => {
          const state = getStepState(i, activeIndex);
          return (
            <React.Fragment key={step.key}>
              {i > 0 && <span className="text-[#d1cdc7] text-xs flex-shrink-0">›</span>}
              <div className={`flex items-center gap-1.5 ${state === 'pending' ? 'opacity-30' : state === 'done' ? 'opacity-50' : ''}`}>
                <StepIcon state={state} size={14} />
                <span className={`text-[10px] ${state === 'active' ? 'text-[#6b4e35] font-semibold' : 'text-[#9c8c7a]'}`}>
                  {step.label}
                </span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3.5 py-4 px-5">
      {STEPS.map((step, i) => {
        const state = getStepState(i, activeIndex);
        return (
          <div
            key={step.key}
            className={`flex items-center gap-3 ${state === 'pending' ? 'opacity-30' : state === 'done' ? 'opacity-50' : ''}`}
          >
            <StepIcon state={state} />
            <span className={`text-sm ${
              state === 'done'   ? 'text-[#6b4e35] line-through' :
              state === 'active' ? 'text-[#6b4e35] font-semibold' :
                                   'text-[#9c8c7a]'
            }`}>
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ErrorMessage({ isRateLimit, detail, onRetry }: { isRateLimit: boolean; detail?: string; onRetry: () => void }) {
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
        <div className="mt-4 flex items-center justify-center gap-4 flex-wrap">
          {!isRateLimit && (
            <button
              onClick={onRetry}
              className="text-[#6b4e35] border border-[#6b4e35] px-3 py-1.5 rounded text-sm hover:bg-[#ede8df] transition-colors"
            >
              Try again
            </button>
          )}
          <a href="/" className="inline-block text-[#6b4e35] underline">Return to home</a>
        </div>
      </div>
    </div>
  );
}

function cacheKey(query: string, nikayas?: string[]) {
  return `synthesis:${query}:${nikayas?.join(',') ?? ''}`;
}

function readCache(query: string, nikayas?: string[]): SynthesisResponse | null {
  try {
    const raw = sessionStorage.getItem(cacheKey(query, nikayas));
    return raw ? (JSON.parse(raw) as SynthesisResponse) : null;
  } catch {
    return null;
  }
}

function writeCache(query: string, nikayas: string[] | undefined, data: SynthesisResponse) {
  try {
    sessionStorage.setItem(cacheKey(query, nikayas), JSON.stringify(data));
  } catch {
    // sessionStorage full or unavailable — ignore
  }
}

export function SynthesisLoader({ query, nikayas }: { query: string; nikayas?: string[] }) {
  const [streamText, setStreamText] = React.useState('');
  const [status, setStatus] = React.useState('Searching the Canon…');
  const [data, setData] = React.useState<SynthesisResponse | null>(null);
  const [error, setError] = React.useState<{ status?: number; message?: string } | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);
  const [streamingFadeIn, setStreamingFadeIn] = React.useState(false);
  const streamingStarted = React.useRef(false);

  // When the page becomes visible again after being hidden and we're in error state, auto-retry once.
  React.useEffect(() => {
    if (!error) return;
    const handleVisibility = () => {
      if (!document.hidden) setRetryCount(c => c + 1);
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [error]);

  React.useEffect(() => {
    setStreamText('');
    setStatus('Searching the Canon…');
    setData(null);
    setError(null);

    const cached = readCache(query, nikayas);
    if (cached) {
      setData(cached);
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    // setTimeout(0) prevents the double-fetch from React StrictMode: cleanup clears the
    // timer synchronously before the stream starts, so only one request reaches the backend.
    const timerId = setTimeout(() => {
      (async () => {
        try {
          for await (const event of streamSynthesis(query, nikayas, controller.signal)) {
            if (cancelled) break;
            if (event.type === 'status') setStatus(event.text);
            else if (event.type === 'chunk') setStreamText(t => t + event.text);
            else if (event.type === 'done') {
              const response = event as SynthesisResponse;
              writeCache(query, nikayas, response);
              setData(response);
              break;
            }
            else if (event.type === 'error') throw Object.assign(new Error(event.message), { status: 500 });
          }
        } catch (e: any) {
          if (!cancelled && e.name !== 'AbortError') setError(e);
        }
      })();
    }, 0);

    return () => { cancelled = true; clearTimeout(timerId); controller.abort(); };
  }, [query, nikayas?.join(','), retryCount]);

  const visible = streamText ? stripThinking(streamText) : '';

  // Fix 6: cross-fade when streaming layout first appears
  React.useEffect(() => {
    if (visible && !streamingStarted.current) {
      streamingStarted.current = true;
      requestAnimationFrame(() => requestAnimationFrame(() => setStreamingFadeIn(true)));
    }
  }, [visible]);

  if (data) return <DualPaneContainer data={data} />;

  if (error) return (
    <ErrorMessage
      isRateLimit={error.status === 429}
      detail={error.message}
      onRetry={() => setRetryCount(c => c + 1)}
    />
  );

  if (visible) {
    return (
      <div
        className="h-full flex flex-col bg-[#fef9f0]"
        style={{ opacity: streamingFadeIn ? 1 : 0, transition: 'opacity 200ms ease' }}
      >
        {/* Mobile: horizontal step bar */}
        <div className="md:hidden flex-shrink-0">
          <StepList currentStatus={status} horizontal />
        </div>
        {/* Desktop: sidebar + text / Mobile: text only (bar is above) */}
        <div className="flex-1 flex overflow-hidden">
          {/* Desktop sidebar */}
          <div className="hidden md:flex flex-col w-32 flex-shrink-0 border-r border-[#e8e4dc] bg-[#faf9f7]">
            <StepList currentStatus={status} />
          </div>
          {/* Streaming text */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto">
              <div className="text-[17px] leading-[1.85] whitespace-pre-wrap text-[#1a1a1a]" style={{ fontFamily: 'Georgia, serif' }}>
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
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-full bg-[#fef9f0]">
      <StepList currentStatus={status} />
    </div>
  );
}
