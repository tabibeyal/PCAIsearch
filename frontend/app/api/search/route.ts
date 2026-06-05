import { NextRequest } from 'next/server';

import { BACKEND_URL } from '@/lib/backend';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/search?${params}`);
  } catch (e) {
    console.error('Backend unreachable:', e);
    return new Response('Service temporarily unavailable', { status: 502 });
  }
  if (!upstream.ok) {
    return new Response(`Backend error: ${upstream.status}`, { status: upstream.status });
  }
  const data = await upstream.json();
  return Response.json(data);
}
