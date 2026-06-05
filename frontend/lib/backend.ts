// Origin of the FastAPI backend, used by the Next.js route handlers that proxy
// to it. Server-side only — the browser talks to those routes under /api.
export const BACKEND_URL = process.env.API_URL ?? 'http://localhost:8000';
