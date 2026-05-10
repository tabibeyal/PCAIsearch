import { SearchResponse, SynthesisResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function apiError(message: string, status: number): Error {
  const err = new Error(message) as Error & { status: number };
  err.status = status;
  return err;
}

export async function searchVerses(query: string, topK = 20): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
  if (!res.ok) throw apiError('Search request failed', res.status);
  return res.json();
}

export async function getSynthesis(query: string): Promise<SynthesisResponse> {
  const res = await fetch(`${API_BASE}/synthesize?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw apiError('Synthesis request failed', res.status);
  return res.json();
}

export async function* streamSynthesis(query: string) {
  const res = await fetch(`${API_BASE}/stream?q=${encodeURIComponent(query)}`);
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
