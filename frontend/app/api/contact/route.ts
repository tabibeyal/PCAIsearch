import { NextRequest } from 'next/server';

import { proxyToBackend } from '@/lib/backendProxy';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  return proxyToBackend(request, '/contact');
}
