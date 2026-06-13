/**
 * Session persistence — append-only to boardroom_sessions.jsonl.
 *
 * Same JSONL file mindX has been writing to from Python — the dashboard's
 * /insight/boardroom/recent reads this file, so during the cutover both
 * Python and Node write the same shape and the dashboard keeps working.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomBytes } from 'node:crypto';
import { CONFIG } from '../config.js';
import { appendJsonl } from '../log.js';
import type { Session } from './types.js';

const SESSIONS_PATH = resolve(CONFIG.dataDir, 'boardroom_sessions.jsonl');
const ACTIVE_SESSIONS = new Map<string, Session>();

export function newSessionId(): string {
  return `br_${randomBytes(8).toString('hex')}`;
}

export function persistSession(session: Session): void {
  appendJsonl(SESSIONS_PATH, session as unknown as Record<string, unknown>);
  ACTIVE_SESSIONS.delete(session.session_id);
}

export function trackActive(session: Session): void {
  ACTIVE_SESSIONS.set(session.session_id, session);
}

export function getActive(session_id: string): Session | null {
  return ACTIVE_SESSIONS.get(session_id) ?? null;
}

export function recentSessions(limit = 50): Session[] {
  if (!existsSync(SESSIONS_PATH)) return [];
  const lines = readFileSync(SESSIONS_PATH, 'utf-8').split('\n').filter(l => l.trim());
  const tail = lines.slice(-limit);
  const sessions: Session[] = [];
  for (const line of tail) {
    try {
      sessions.push(JSON.parse(line));
    } catch { /* skip */ }
  }
  return sessions.reverse();
}
