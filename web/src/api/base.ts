/**
 * Base path of the CricketLens API. Relative by default: the site and the API share one origin (the Vite
 * proxy in development, the Vercel rewrite in production). Set VITE_API_BASE_URL at build time only when
 * the API is deployed on a different origin, e.g. https://api.example.com/api.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

/** A request still pending after this long is treated as waiting for the API to start (a cold start takes ~7–9 s). */
export const SLOW_REQUEST_MS = 5000;

const slowRequests = new Set<number>();
const listeners = new Set<() => void>();
let nextRequestId = 0;

function notify() {
  listeners.forEach((listener) => listener());
}

/** True while at least one API request has been pending for SLOW_REQUEST_MS or longer. */
export function hasSlowRequest(): boolean {
  return slowRequests.size > 0;
}

export function subscribeSlowRequests(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** fetch() for every API call: identical behaviour, plus tracking of requests that are slow to answer. */
export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const id = nextRequestId++;
  const timer = setTimeout(() => {
    slowRequests.add(id);
    notify();
  }, SLOW_REQUEST_MS);
  try {
    return await fetch(input, init);
  } finally {
    clearTimeout(timer);
    if (slowRequests.delete(id)) notify();
  }
}
