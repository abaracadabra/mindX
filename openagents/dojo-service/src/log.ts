/**
 * Logging + JSONL append helpers — same shape as boardroom-service/log.ts.
 * Kept duplicated rather than pulled into a shared package so each service
 * is independently auditable and deployable (one of the user's constraints
 * is local libraries over deps).
 */

import { appendFileSync, statSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';

const MAX_BYTES = 100 * 1024 * 1024;

export function log(level: 'info' | 'warn' | 'error' | 'debug', mod: string, msg: string, ctx?: Record<string, unknown>) {
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, mod, msg, ...(ctx ?? {}) }));
}

export function appendJsonl(path: string, record: Record<string, unknown>): void {
  const dir = dirname(path);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  try {
    if (existsSync(path) && statSync(path).size >= MAX_BYTES) {
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      renameSync(path, join(dir, `${basename(path, '.jsonl')}.${ts}.jsonl`));
    }
  } catch (e) {
    log('warn', 'log', 'rotation failed; continuing append', { path, err: String(e) });
  }
  appendFileSync(path, JSON.stringify(record) + '\n', 'utf-8');
}
