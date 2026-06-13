/**
 * Room store — JSONL append-only persistence + in-memory index.
 *
 * Storage shape: data/governance/rooms.jsonl
 *   Each line is either a Room snapshot ({"op":"upsert", room: {...}}) or a
 *   tombstone ({"op":"delete", room_id: "..."}). The index is rebuilt by
 *   replaying the log on boot — last-write-wins per room_id, tombstones
 *   remove the entry. This keeps the audit trail honest (deletions are
 *   visible in the log) while giving O(1) lookups in memory.
 *
 * Concurrency: single Node process per service; no locks needed beyond what
 * Node's single-threaded loop provides. Multi-worker would need a shared
 * substrate (Phase E2 if it becomes necessary).
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomBytes } from 'node:crypto';
import { CONFIG, loadAgentMap } from '../config.js';
import { appendJsonl, log } from '../log.js';
import type { Room, CreateRoomInput, RoomSeat } from './types.js';

const STORE_PATH = resolve(CONFIG.dataDir, 'rooms.jsonl');

interface UpsertEntry { op: 'upsert'; room: Room; ts: number; }
interface DeleteEntry { op: 'delete'; room_id: string; ts: number; }
type LogEntry = UpsertEntry | DeleteEntry;

const ROOMS = new Map<string, Room>();

function nowSec(): number { return Math.floor(Date.now() / 1000); }

function roomId(prefix = 'room'): string {
  return `${prefix}_${randomBytes(8).toString('hex')}`;
}

function persist(entry: LogEntry): void {
  appendJsonl(STORE_PATH, entry as unknown as Record<string, unknown>);
}

export function loadRoomStore(): void {
  ROOMS.clear();
  if (!existsSync(STORE_PATH)) return;
  let count = 0;
  for (const line of readFileSync(STORE_PATH, 'utf-8').split('\n')) {
    const t = line.trim();
    if (!t) continue;
    try {
      const e = JSON.parse(t) as LogEntry;
      if (e.op === 'upsert' && e.room?.room_id) {
        ROOMS.set(e.room.room_id, e.room);
        count++;
      } else if (e.op === 'delete' && e.room_id) {
        ROOMS.delete(e.room_id);
      }
    } catch {
      // Skip malformed line — operator-fixable; not a boot blocker.
    }
  }
  log('info', 'rooms', `room store loaded`, { count, rooms_in_memory: ROOMS.size, path: STORE_PATH });
}

export function getRoom(room_id: string): Room | null {
  return ROOMS.get(room_id) ?? null;
}

export function listRooms(opts: { mode?: Room['mode']; owner?: string } = {}): Room[] {
  const out: Room[] = [];
  for (const r of ROOMS.values()) {
    if (opts.mode && r.mode !== opts.mode) continue;
    if (opts.owner && r.owner.toLowerCase() !== opts.owner.toLowerCase()) continue;
    out.push(r);
  }
  // Sort: protected first (defaults at top), then newest first.
  out.sort((a, b) => {
    if (a.protected !== b.protected) return a.protected ? -1 : 1;
    return b.created_at - a.created_at;
  });
  return out;
}

export function createRoom(owner: `0x${string}`, input: CreateRoomInput): Room {
  const room: Room = {
    room_id: roomId(),
    owner: owner.toLowerCase() as `0x${string}`,
    name: input.name.slice(0, 120),
    description: input.description?.slice(0, 500),
    mode: input.mode,
    seats: input.seats ?? [],
    cabinet: input.cabinet ?? [owner.toLowerCase() as `0x${string}`],
    invited: {},
    protected: false,
    daio_sanctioned: false,
    created_at: nowSec(),
    updated_at: nowSec(),
  };
  ROOMS.set(room.room_id, room);
  persist({ op: 'upsert', room, ts: nowSec() });
  log('info', 'rooms', 'room created', { room_id: room.room_id, owner, mode: room.mode });
  return room;
}

export function updateRoom(room_id: string, patch: Partial<Room>): Room | null {
  const existing = ROOMS.get(room_id);
  if (!existing) return null;
  const updated: Room = { ...existing, ...patch, room_id: existing.room_id, updated_at: nowSec() };
  ROOMS.set(room_id, updated);
  persist({ op: 'upsert', room: updated, ts: nowSec() });
  return updated;
}

export function deleteRoom(room_id: string): boolean {
  const r = ROOMS.get(room_id);
  if (!r) return false;
  if (r.protected) {
    log('warn', 'rooms', 'refused to delete protected room', { room_id });
    return false;
  }
  ROOMS.delete(room_id);
  persist({ op: 'delete', room_id, ts: nowSec() });
  return true;
}

export function inviteToRoom(room_id: string, invitee: `0x${string}`): string | null {
  const r = ROOMS.get(room_id);
  if (!r) return null;
  const token = randomBytes(24).toString('hex');
  r.invited[invitee.toLowerCase()] = token;
  r.updated_at = nowSec();
  persist({ op: 'upsert', room: r, ts: nowSec() });
  return token;
}

export function acceptInvite(room_id: string, wallet: `0x${string}`, token: string): boolean {
  const r = ROOMS.get(room_id);
  if (!r) return false;
  const expected = r.invited[wallet.toLowerCase()];
  if (!expected || expected !== token) return false;
  delete r.invited[wallet.toLowerCase()];
  r.updated_at = nowSec();
  persist({ op: 'upsert', room: r, ts: nowSec() });
  return true;
}

/**
 * Boot the mindX-default private room (CEO + 7 soldiers).
 *
 * Idempotent — if a room with id `mindx-private-boardroom` already exists
 * in the store, it's left untouched. First-boot creates it from
 * agent_map.json's soldier + ceo entries.
 *
 * Owner: a placeholder all-zero address that means "mindX system". Real
 * cabinet management happens via shadow_overlord.jsonl entries.
 */
export function ensureMindxDefaultRoom(): Room {
  const DEFAULT_ID = 'mindx-private-boardroom';
  const existing = ROOMS.get(DEFAULT_ID);
  if (existing) return existing;

  const agentMap = loadAgentMap();
  const seats: RoomSeat[] = [];
  for (const [role, cfg] of Object.entries(agentMap.soldiers)) {
    seats.push({
      address: ((cfg.eth_address as `0x${string}` | undefined) ?? '0x0000000000000000000000000000000000000000') as `0x${string}`,
      role,
      weight: cfg.weight ?? 1.0,
      veto: cfg.veto ?? false,
      personhood_required: false,
      inference_provider: cfg.inference_provider,
      model: cfg.cloud_model ?? cfg.local_model,
    });
  }
  // CEO sits at the head but does not vote.
  if (agentMap.ceo) {
    seats.unshift({
      address: ((agentMap.ceo.eth_address as `0x${string}` | undefined) ?? '0x0000000000000000000000000000000000000000') as `0x${string}`,
      role: 'ceo',
      weight: 0.0,
      veto: false,
      personhood_required: false,
      inference_provider: agentMap.ceo.inference_provider,
      model: agentMap.ceo.cloud_model ?? agentMap.ceo.local_model,
    });
  }

  const room: Room = {
    room_id: DEFAULT_ID,
    owner: '0x0000000000000000000000000000000000000000' as `0x${string}`,
    name: 'mindX Private Boardroom',
    description: 'Default boardroom for mindX — CEO + seven soldiers (CISO/CRO 1.2× veto preserved).',
    mode: 'private',
    seats,
    cabinet: [],   // populated from shadow_overlord.jsonl at resolve time
    invited: {},
    protected: true,
    daio_sanctioned: false,
    created_at: nowSec(),
    updated_at: nowSec(),
  };
  ROOMS.set(DEFAULT_ID, room);
  persist({ op: 'upsert', room, ts: nowSec() });
  log('info', 'rooms', 'mindX-default room created', { room_id: DEFAULT_ID, seats: seats.length });
  return room;
}
