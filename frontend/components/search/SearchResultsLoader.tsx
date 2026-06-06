'use client';

import React from 'react';
import { searchVerses } from '@/lib/api';
import { SearchResultsView } from './SearchResultsView';
import { SearchResult } from '@/types/api';

const MESSAGES = [
  'Starting your search…',
  'Looking through the suttas…',
  'Almost there…',
];

// v3: clears stale data from earlier uncapped measurements
const TIMING_KEY = 'passages_avg_ms_v3';
const TIMING_N = 10;
const STEP3_FLOOR_MS = 600;
const MIN_STEP_MS = 1200;
const MAX_STEP_MS = 3000;
const MAX_AVG_MS = 12000; // cap stored avg so very slow backend runs don't skew forever

function getAvgMs(): number {
  try {
    const v = localStorage.getItem(TIMING_KEY);
    return v ? Math.min(Math.max(parseFloat(v), 1500), MAX_AVG_MS) : 5000;
  } catch { return 5000; }
}

function updateAvgMs(elapsedMs: number) {
  try {
    const clamped = Math.min(elapsedMs, MAX_AVG_MS);
    const prev = getAvgMs();
    const countRaw = localStorage.getItem(TIMING_KEY + '_n');
    const count = countRaw ? Math.min(parseInt(countRaw), TIMING_N - 1) : 0;
    const next = count === 0 ? clamped : (prev * count + clamped) / (count + 1);
    localStorage.setItem(TIMING_KEY, String(next));
    localStorage.setItem(TIMING_KEY + '_n', String(count + 1));
  } catch {}
}

// Steps 1 and 2 each take 38% of expected time (total 76%); step 3 uses the
// remaining ~24%, which is always shorter than either preceding step.
// Hard caps prevent extreme averages from producing absurdly long messages.
function stepDurationMs(): number {
  const avg = getAvgMs();
  return Math.min(Math.max(avg * 0.38, MIN_STEP_MS), MAX_STEP_MS);
}

function LoadingState({ phase }: { phase: 0 | 1 | 2 }) {
  const [displayPhase, setDisplayPhase] = React.useState<0 | 1 | 2>(phase);
  const [visible, setVisible] = React.useState(true);

  React.useEffect(() => {
    if (displayPhase === phase) return;
    const t1 = setTimeout(() => setVisible(false), 0);
    const t2 = setTimeout(() => { setDisplayPhase(phase); setVisible(true); }, 250);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [displayPhase, phase]);

  return (
    <div className="flex items-center justify-center h-full text-[#9c8c7a]">
      <div className="text-center">
        <div className="w-8 h-8 rounded-full animate-spin mx-auto mb-3" style={{ border: '2px solid #e8e4dc', borderTopColor: '#6b4e35' }} />
        <p className="text-sm" style={{ opacity: visible ? 1 : 0, transition: 'opacity 250ms' }}>
          {MESSAGES[displayPhase]}
        </p>
      </div>
    </div>
  );
}

function ErrorState({ isRateLimit, onRetry }: { isRateLimit: boolean; onRetry: () => void }) {
  return (
    <div className="flex items-center justify-center p-8 text-red-500 text-center">
      <div>
        <h2 className="text-xl font-bold mb-2">{isRateLimit ? 'Rate Limit Exceeded' : 'Search Error'}</h2>
        <p>{isRateLimit ? 'You have sent too many requests. Please wait a moment and try again.' : 'Unable to retrieve passages for this query.'}</p>
        {!isRateLimit && (
          <button
            onClick={onRetry}
            className="mt-4 text-[#6b4e35] border border-[#6b4e35] px-3 py-1.5 rounded text-sm hover:bg-[#ede8df] transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

// Single state machine replaces phase + resultsReady + showResults + resultsRef.
// 'ready' holds the data while STEP3_FLOOR_MS elapses; 'shown' triggers the
// view swap. The phase timer short-circuits on any non-loading state.
type State =
  | { kind: 'loading'; phase: 0 | 1 | 2 }
  | { kind: 'ready'; results: SearchResult[] }
  | { kind: 'shown'; results: SearchResult[] }
  | { kind: 'error'; status?: number };

type Action =
  | { type: 'reset' }
  | { type: 'tick'; to: 0 | 1 | 2 }
  | { type: 'results'; data: SearchResult[] }
  | { type: 'shown' }
  | { type: 'error'; status?: number };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'reset':
      return { kind: 'loading', phase: 0 };
    case 'results':
      return { kind: 'ready', results: action.data };
    case 'shown':
      return state.kind === 'ready' ? { kind: 'shown', results: state.results } : state;
    case 'tick':
      if (state.kind !== 'loading') return state;
      return { kind: 'loading', phase: action.to };
    case 'error':
      return { kind: 'error', status: action.status };
  }
}

export function SearchResultsLoader({ query, nikayas }: { query: string; nikayas: string[] }) {
  const [state, dispatch] = React.useReducer(reducer, { kind: 'loading', phase: 0 });
  const [retryCount, setRetryCount] = React.useState(0);
  const [stepMs] = React.useState(stepDurationMs);
  const nikayasKey = nikayas.join(',');

  // Fetch (and reset on new query/retry)
  React.useEffect(() => {
    dispatch({ type: 'reset' });
    let cancelled = false;
    const controller = new AbortController();
    const startMs = Date.now();
    const nikayaList = nikayasKey ? nikayasKey.split(',') : undefined;

    // setTimeout(0) prevents StrictMode's double-invocation from sending two
    // requests to the backend: cleanup clears the timer before it fires.
    const timerId = setTimeout(() => {
      (async () => {
        try {
          const data = await searchVerses(query, 20, nikayaList, controller.signal);
          if (!cancelled) {
            updateAvgMs(Date.now() - startMs);
            dispatch({ type: 'results', data: data.results });
          }
        } catch (e: unknown) {
          const err = e as { name?: string; status?: number };
          if (!cancelled && err.name !== 'AbortError') dispatch({ type: 'error', status: err.status });
        }
      })();
    }, 0);

    return () => { cancelled = true; clearTimeout(timerId); controller.abort(); };
  }, [query, nikayasKey, retryCount]);

  // Advance loading phase 0→1→2 on timers; phase 2 has no timer (waits for results)
  const tickKey: number = state.kind === 'loading' ? state.phase : -1;
  React.useEffect(() => {
    if (tickKey === -1 || tickKey === 2) return;
    const t = setTimeout(() => dispatch({ type: 'tick', to: (tickKey + 1) as 0 | 1 | 2 }), stepMs);
    return () => clearTimeout(t);
  }, [tickKey, stepMs]);

  // Once results are in, hold for STEP3_FLOOR_MS then reveal
  React.useEffect(() => {
    if (state.kind !== 'ready') return;
    const t = setTimeout(() => dispatch({ type: 'shown' }), STEP3_FLOOR_MS);
    return () => clearTimeout(t);
  }, [state.kind]);

  if (state.kind === 'error') return <ErrorState isRateLimit={state.status === 429} onRetry={() => setRetryCount(c => c + 1)} />;
  if (state.kind === 'shown') return <SearchResultsView results={state.results} query={query} />;
  return <LoadingState phase={state.kind === 'loading' ? state.phase : 2} />;
}
