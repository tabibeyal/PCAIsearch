import { SearchResult, SynthesisResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ??
  (typeof window === 'undefined' ? (process.env.API_URL ?? 'http://localhost:8000') : '/api');

function apiError(message: string, status: number): Error {
  return Object.assign(new Error(message), { status });
}

type StreamEvent =
  | { type: 'status'; text: string }
  | { type: 'chunk'; text: string }
  | (SynthesisResponse & { type: 'done' })
  | { type: 'error'; message: string };

function isTerminalEvent(event: unknown): event is StreamEvent {
  const e = event as StreamEvent;
  return e.type === 'done' || e.type === 'error';
}

export async function* streamSynthesis(query: string, nikayas?: string[], signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query });
  nikayas?.forEach(n => params.append('nikayas', n));

  const url = `${API_BASE}/stream?${params}`;
  const source = new EventSource(url, { signal } as EventSourceInit);
  const queue: StreamEvent[] = [];
  let notify: (() => void) | null = null;

  source.onmessage = (event) => {
    const data = JSON.parse(event.data) as StreamEvent;
    queue.push(data);
    notify?.();
    notify = null;
    if (isTerminalEvent(data)) {
      source.close();
    }
  };

  source.onerror = () => {
    queue.push({ type: 'error', message: 'Stream failed' });
    notify?.();
    notify = null;
    source.close();
  };

  try {
    while (true) {
      if (queue.length === 0) {
        await new Promise<void>((resolve) => { notify = resolve; });
      }
      const event = queue.shift()!;
      yield event;
      if (isTerminalEvent(event)) break;
    }
  } finally {
    source.close();
  }
}

export async function submitFeedback(payload: {
  query: string;
  answer: string;
  rating: 'up' | 'down';
  category: string | null;
  comment: string | null;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw apiError('Feedback submission failed', res.status);
}

export async function submitContact(payload: {
  name: string;
  email: string;
  message: string;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw apiError('Contact submission failed', res.status);
}

export async function shareAnswer(payload: {
  query: string;
  answer: string;
  context: SearchResult[];
  receipt: string;
}): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/share`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw apiError('Share failed', res.status);
  return res.json();
}

export async function getSharedAnswer(id: string): Promise<{
  query: string;
  answer: string;
  context: SearchResult[];
}> {
  const res = await fetch(`${API_BASE}/share/${id}`);
  if (!res.ok) throw apiError('Shared answer not found', res.status);
  return res.json();
}
