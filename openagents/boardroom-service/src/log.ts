/**
 * Minimal logging + JSONL append helpers.
 *
 * Deliberately avoids winston / pino. The shape we need is small:
 *   - structured console output with ts + level + module
 *   - append-only writes to data/governance/*.jsonl with file rotation
 *     at 100MB (mirrors mindX's catalogue event log policy).
 *
 * No buffering — sessions are infrequent enough that fsync per write is fine
 * and the audit-trail guarantee is more important than micro-throughput.
 */

import { appendFileSync, statSync, renameSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';

const MAX_BYTES = 100 * 1024 * 1024; // 100 MB rotation

export function log(level: 'info' | 'warn' | 'error' | 'debug', mod: string, msg: string, ctx?: Record<string, unknown>) {
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    level,
    mod,
    msg,
    ...(ctx ?? {}),
  });
  // eslint-disable-next-line no-console
  console.log(line);
}

export function appendJsonl(path: string, record: Record<string, unknown>): void {
  // Ensure parent dir exists.
  const dir = dirname(path);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  // Rotate if oversized.
  try {
    if (existsSync(path) && statSync(path).size >= MAX_BYTES) {
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      renameSync(path, join(dir, `${basename(path, '.jsonl')}.${ts}.jsonl`));
    }
  } catch (e) {
    log('warn', 'log', 'rotation check failed; continuing append', { path, err: String(e) });
  }

  appendFileSync(path, JSON.stringify(record) + '\n', { encoding: 'utf-8' });
}
