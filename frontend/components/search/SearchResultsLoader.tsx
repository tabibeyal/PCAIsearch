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
        <p className="text-sm" aria-live="polite" aria-atomic="true" style={{ opacity: visible ? 1 : 0, transition: 'opacity 250ms' }}>
          {MESSAGES[displayPhase]}
        </p>
      </div>
    </div>
  );
}

function ErrorState({ isRateLimit, onRetry }: { isRateLimit: boolean; onRetry: () => void }) {
  return (
    <div className="flex items-center justify-center p-8 text-amber-800 text-center">
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

type State =
  | { kind: 'loading'; phase: 0 | 1 | 2 }
  | { kind: 'ready'; results: SearchResult[] }
  | { kind: 'shown'; results: SearchResult[] }
  | { kind: 'error'; status?: number };

export function SearchResultsLoader({ query, nikayas }: { query: string; nikayas: string[] }) {
  const [state, setState] = React.useState<State>({ kind: 'loading', phase: 0 });
  const [retryCount, setRetryCount] = React.useState(0);
  const [stepMs] = React.useState(stepDurationMs);
  const nikayasKey = nikayas.join(',');

  // Fetch on new query/retry
  React.useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const startMs = Date.now();
    const nikayaList = nikayasKey ? nikayasKey.split(',') : undefined;

    const timerId = setTimeout(() => {
      (async () => {
        try {
          const data = await searchVerses(query, nikayaList, controller.signal);
          if (!cancelled) {
            updateAvgMs(Date.now() - startMs);
            setState({ kind: 'ready', results: data.results });
          }
        } catch (e: unknown) {
          const err = e as { name?: string; status?: number };
          if (!cancelled && err.name !== 'AbortError') setState({ kind: 'error', status: err.status });
        }
      })();
    }, 0);

    return () => { cancelled = true; clearTimeout(timerId); controller.abort(); };
  }, [query, nikayasKey, retryCount]);

  // Advance loading phase 0→1→2 on timers; phase 2 has no timer (waits for results)
  const tickKey: number = state.kind === 'loading' ? state.phase : -1;
  React.useEffect(() => {
    if (tickKey === -1 || tickKey === 2) return;
    const t = setTimeout(() => setState({ kind: 'loading', phase: (tickKey + 1) as 0 | 1 | 2 }), stepMs);
    return () => clearTimeout(t);
  }, [tickKey, stepMs]);

  // Once results are in, hold for STEP3_FLOOR_MS then reveal
  React.useEffect(() => {
    if (state.kind !== 'ready') return;
    const t = setTimeout(() => setState({ kind: 'shown', results: state.results }), STEP3_FLOOR_MS);
    return () => clearTimeout(t);
  }, [state]);

  if (state.kind === 'error') return <ErrorState isRateLimit={state.status === 429} onRetry={() => setRetryCount(c => c + 1)} />;
  if (state.kind === 'shown') return <SearchResultsView results={state.results} />;
  return <LoadingState phase={state.kind === 'loading' ? state.phase : 2} />;
}
