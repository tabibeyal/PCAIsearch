import { NextRequest } from 'next/server';

// Shared backend proxy helper for Next.js /api route handlers.
// Forwards method, search params, content-type and body to API_URL.

const BACKEND_URL = process.env.API_URL ?? 'http://localhost:8000';

export async function proxyToBackend(
  request: NextRequest,
  path: string,
  extraHeaders?: Record<string, string>,
) {
  const params = request.nextUrl.searchParams.toString();
  const url = `${BACKEND_URL}${path}${params ? `?${params}` : ''}`;
  const init: RequestInit = { method: request.method };
  const contentType = request.headers.get('Content-Type');
  if (contentType) {
    init.headers = { 'Content-Type': contentType, ...extraHeaders };
  } else if (extraHeaders) {
    init.headers = extraHeaders;
  }
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text();
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch (e) {
    console.error('Backend unreachable:', e);
    return new Response('Service temporarily unavailable', { status: 502 });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}
