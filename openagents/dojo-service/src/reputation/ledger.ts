/**
 * Reputation ledger — append-only deltas in dojo_events.jsonl.
 *
 * Same path mindX's daio/governance/dojo.py wrote to historically. Each
 * record:
 *
 *   { ts, agent_id, delta, event_type, reason, applied_by, total_after? }
 *
 * Per-agent score is computed by summing deltas from the head of the log.
 * Cheap because:
 *   - The log rotates at 100MB (log.ts handles it).
 *   - Most queries hit the cache; we recompute lazily on lookup, with the
 *     final score persisted back to a snapshot file (data/governance/dojo_snapshot.json)
 *     to amortize the cost.
 *
 * Privilege escalation tied to ranks (rankFor in config.ts).
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { CONFIG, rankFor } from '../config.js';
import { appendJsonl, log } from '../log.js';

const EVENTS_PATH   = resolve(CONFIG.dataDir, 'dojo_events.jsonl');
const SNAPSHOT_PATH = resolve(CONFIG.dataDir, 'dojo_snapshot.json');

interface EventRecord {
  ts: string;
  agent_id: string;         // wallet address or agent id (lowercase)
  delta: number;
  event_type: string;
  reason?: string;
  applied_by?: string;
}

interface Snapshot {
  scores: Record<string, number>;
  count_events: number;
  updated_at: number;
}

let SNAPSHOT: Snapshot | null = null;

function ensureSnapshotDir(): void {
  const d = dirname(SNAPSHOT_PATH);
  if (!existsSync(d)) mkdirSync(d, { recursive: true });
}

function readSnapshot(): Snapshot {
  if (SNAPSHOT) return SNAPSHOT;
  if (existsSync(SNAPSHOT_PATH)) {
    try {
      SNAPSHOT = JSON.parse(readFileSync(SNAPSHOT_PATH, 'utf-8')) as Snapshot;
      return SNAPSHOT;
    } catch { /* fall through to rebuild */ }
  }
  // Rebuild from events.
  SNAPSHOT = { scores: {}, count_events: 0, updated_at: 0 };
  if (existsSync(EVENTS_PATH)) {
    for (const line of readFileSync(EVENTS_PATH, 'utf-8').split('\n')) {
      const t = line.trim();
      if (!t) continue;
      try {
        const e = JSON.parse(t) as EventRecord;
        const a = String(e.agent_id ?? '').toLowerCase();
        if (!a) continue;
        SNAPSHOT.scores[a] = (SNAPSHOT.scores[a] ?? 0) + Number(e.delta ?? 0);
        SNAPSHOT.count_events += 1;
      } catch { /* skip */ }
    }
  }
  SNAPSHOT.updated_at = Math.floor(Date.now() / 1000);
  return SNAPSHOT;
}

function writeSnapshot(): void {
  if (!SNAPSHOT) return;
  ensureSnapshotDir();
  try { writeFileSync(SNAPSHOT_PATH, JSON.stringify(SNAPSHOT, null, 2), 'utf-8'); }
  catch (e) { log('warn', 'dojo', 'snapshot write failed', { err: String(e) }); }
}

export function getReputation(agent_id: string): { score: number; rank: ReturnType<typeof rankFor>; agent_id: string } {
  const a = agent_id.toLowerCase();
  const snap = readSnapshot();
  const score = snap.scores[a] ?? 0;
  return { agent_id: a, score, rank: rankFor(score) };
}

export function applyDelta(agent_id: string, delta: number, event_type: string, reason?: string, applied_by?: string): { score: number; rank: ReturnType<typeof rankFor> } {
  const a = agent_id.toLowerCase();
  appendJsonl(EVENTS_PATH, {
    ts: new Date().toISOString(),
    agent_id: a,
    delta,
    event_type,
    reason: reason?.slice(0, 500),
    applied_by: applied_by?.toLowerCase(),
  });
  const snap = readSnapshot();
  snap.scores[a] = (snap.scores[a] ?? 0) + delta;
  snap.count_events += 1;
  snap.updated_at = Math.floor(Date.now() / 1000);
  writeSnapshot();
  return { score: snap.scores[a], rank: rankFor(snap.scores[a]) };
}

export function getStandings(limit = 50): Array<{ agent_id: string; score: number; rank: ReturnType<typeof rankFor> }> {
  const snap = readSnapshot();
  const entries = Object.entries(snap.scores)
    .map(([agent_id, score]) => ({ agent_id, score, rank: rankFor(score) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, Math.max(1, Math.min(500, limit)));
  return entries;
}

export function getRankPrivileges(rank: ReturnType<typeof rankFor>): { read: boolean; analyze: boolean; vote: boolean; propose: boolean; approve: boolean; constitutional: boolean } {
  // Mirror the privilege escalation from daio/governance/dojo.py.
  switch (rank) {
    case 'novice':       return { read: false, analyze: false, vote: false, propose: false, approve: false, constitutional: false };
    case 'apprentice':   return { read: true,  analyze: true,  vote: false, propose: false, approve: false, constitutional: false };
    case 'journeyman':   return { read: true,  analyze: true,  vote: true,  propose: false, approve: false, constitutional: false };
    case 'expert':       return { read: true,  analyze: true,  vote: true,  propose: true,  approve: false, constitutional: false };
    case 'master':       return { read: true,  analyze: true,  vote: true,  propose: true,  approve: true,  constitutional: false };
    case 'grandmaster':  return { read: true,  analyze: true,  vote: true,  propose: true,  approve: true,  constitutional: true  };
    case 'sovereign':    return { read: true,  analyze: true,  vote: true,  propose: true,  approve: true,  constitutional: true  };
  }
}
