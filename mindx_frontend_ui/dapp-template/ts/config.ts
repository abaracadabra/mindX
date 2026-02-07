/**
 * Dapp config – production TypeScript.
 * Replace hardcoded values with env at build time for deployment.
 */

function getApiBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  if (window.MINDX_API_URL) return window.MINDX_API_URL;
  const port = window.MINDX_BACKEND_PORT ?? '8000';
  return `http://localhost:${port}`;
}

export const config = {
  apiBase: getApiBase(),
} as const;
