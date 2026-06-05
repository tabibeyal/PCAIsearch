import { NextRequest } from 'next/server';

import { BACKEND_URL } from '@/lib/backend';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response('Invalid JSON', { status: 400 });
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    console.error('Backend unreachable:', e);
    return new Response('Service temporarily unavailable', { status: 502 });
  }
  return new Response(null, { status: upstream.status });
}
