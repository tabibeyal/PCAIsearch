import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';
import { proxyToBackend } from './backendProxy';

// Regression: the /api/stream proxy must forward the client's abort signal to
// the upstream fetch. When a user clicks a filter mid-stream, the browser
// aborts the EventSource; if the proxy doesn't cancel the upstream, the old
// backend generation keeps running and exhausts the backend's concurrency
// limit, so the next (active) search is rejected with 429 -> "Search Error"
// (with no backend error log, since 429 is a normal response).

describe('proxyToBackend abort forwarding', () => {
  beforeEach(() => {
    vi.stubEnv('API_URL', 'http://localhost:8000');
  });

  it('forwards the client abort signal so a cancelled search cancels the upstream', async () => {
    const fetched = vi.fn().mockResolvedValue(new Response('ok', { status: 200 }));
    global.fetch = fetched as unknown as typeof fetch;

    const request = new NextRequest('http://localhost/api/stream?q=test');
    await proxyToBackend(request, '/stream', { Accept: 'text/event-stream' });

    const init = fetched.mock.calls[0][1] as RequestInit;
    expect(init.signal).toBe(request.signal);
  });
});