/**
 * Base path of the CricketLens API. Relative by default: the site and the API share one origin (the Vite
 * proxy in development, the Vercel rewrite in production). Set VITE_API_BASE_URL at build time only when
 * the API is deployed on a different origin, e.g. https://api.example.com/api.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');
