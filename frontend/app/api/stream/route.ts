import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

const BACKEND = process.env.API_URL ?? 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams.toString();
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND}/stream?${params}`, {
      headers: { Accept: 'text/event-stream' },
    });
  } catch (e) {
    return new Response(`Backend unreachable: ${e}`, { status: 502 });
  }
  if (!upstream.ok || !upstream.body) {
    return new Response(`Backend error: ${upstream.status}`, { status: upstream.status });
  }
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'X-Accel-Buffering': 'no',
    },
  });
}
