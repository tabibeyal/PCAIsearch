import { SearchResponse, SynthesisResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ??
  (typeof window === 'undefined' ? 'http://localhost:8000' : '/api');

function apiError(message: string, status: number): Error {
  const err = new Error(message) as Error & { status: number };
  err.status = status;
  return err;
}

export async function searchVerses(query: string, topK = 20, nikayas?: string[]): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  nikayas?.forEach(n => params.append('nikayas', n));
  const res = await fetch(`${API_BASE}/search?${params}`);
  if (!res.ok) throw apiError('Search request failed', res.status);
  return res.json();
}

export async function getSynthesis(query: string): Promise<SynthesisResponse> {
  const res = await fetch(`${API_BASE}/synthesize?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw apiError('Synthesis request failed', res.status);
  return res.json();
}

export async function* streamSynthesis(query: string, nikayas?: string[]) {
  const params = new URLSearchParams({ q: query });
  nikayas?.forEach(n => params.append('nikayas', n));
  const res = await fetch(`${API_BASE}/stream?${params}`);
  if (!res.ok) throw apiError('Stream request failed', res.status);

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop()!;
    for (const part of parts) {
      if (part.startsWith('data: ')) yield JSON.parse(part.slice(6));
    }
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
