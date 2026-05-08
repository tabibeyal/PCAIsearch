import { SearchResponse, SynthesisResponse } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function searchVerses(query: string): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Search request failed');
  return res.json();
}

export async function getSynthesis(query: string): Promise<SynthesisResponse> {
  const res = await fetch(`${API_BASE}/synthesize?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Synthesis request failed');
  return res.json();
}
