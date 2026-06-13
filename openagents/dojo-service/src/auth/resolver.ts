/**
 * Tier resolver — given a wallet address + requested scope, decide which
 * tier the address is at.
 *
 * Order (highest wins):
 *   1. Sovereign — wallet in shadow_overlord.jsonl with role=sovereign
 *   2. Cabinet   — wallet in shadow_overlord.jsonl with role=cabinet
 *                  OR in the service's static cabinet (this service's owners)
 *   3. Seat      — wallet listed in the requested room's seats[] (room-scoped)
 *   4. Person    — has personhood (queried from dojo-service if available)
 *   5. Invitee   — request carried a valid invite token (passed in via param)
 *   6. Observer  — default
 *
 * Reads shadow_overlord.jsonl from the shared filesystem on each lookup;
 * cheap because the file is tiny and only sovereign/cabinet entries land
 * there. SIGHUP-safe — re-read on every call rather than caching, so
 * promote/revoke takes effect immediately.
 */

import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { CONFIG } from '../config.js';
import { TIERS, type Tier } from './tiers.js';

interface ShadowOverlordEntry {
  wallet: string;       // lowercase 0x address
  role: 'sovereign' | 'cabinet';
  scope?: string;       // optional service-name restriction
  granted_at: number;
  granted_by?: string;
}

function readShadowOverlord(): ShadowOverlordEntry[] {
  const path = resolve(CONFIG.dataDir, 'shadow_overlord.jsonl');
  if (!existsSync(path)) return [];
  try {
    const raw = readFileSync(path, 'utf-8');
    const entries: ShadowOverlordEntry[] = [];
    for (const line of raw.split('\n')) {
      const t = line.trim();
      if (!t) continue;
      try {
        const e = JSON.parse(t);
        if (e?.wallet && e?.role) {
          entries.push({
            wallet: String(e.wallet).toLowerCase(),
            role: e.role,
            scope: e.scope,
            granted_at: e.granted_at ?? 0,
            granted_by: e.granted_by,
          });
        }
      } catch { /* skip malformed line */ }
    }
    return entries;
  } catch {
    return [];
  }
}

export interface RoomLike {
  room_id: string;
  seats?: Array<{ address?: string; role?: string }>;
  cabinet?: string[];  // wallet addresses
}

export interface ResolveOptions {
  /** Requested scope — a room_id or this service's name. */
  scope: string;
  /** If the request carried a valid invite token, set this. */
  inviteValid?: boolean;
  /** Optional room object (for tier-3 seat check). */
  room?: RoomLike;
  /** Personhood lookup (queried from dojo-service in practice). */
  personhood?: 'none' | 'pending' | 'granted';
}

export function resolveTier(wallet: `0x${string}`, opts: ResolveOptions): { tier: Tier; reason: string } {
  const w = wallet.toLowerCase();
  const so = readShadowOverlord();

  // 1. Sovereign
  const sov = so.find(e => e.wallet === w && e.role === 'sovereign'
                       && (!e.scope || e.scope === opts.scope || e.scope === '*'));
  if (sov) return { tier: TIERS.sovereign, reason: 'shadow_overlord:sovereign' };

  // 2. Cabinet
  const cab = so.find(e => e.wallet === w && e.role === 'cabinet'
                       && (!e.scope || e.scope === opts.scope || e.scope === '*'));
  if (cab) return { tier: TIERS.cabinet, reason: 'shadow_overlord:cabinet' };
  if (opts.room?.cabinet?.map(a => a.toLowerCase()).includes(w)) {
    return { tier: TIERS.cabinet, reason: 'room:cabinet' };
  }

  // 3. Seat (room-scoped)
  if (opts.room?.seats?.some(s => s.address?.toLowerCase() === w)) {
    return { tier: TIERS.seat, reason: 'room:seat' };
  }

  // 4. Person
  if (opts.personhood === 'granted') return { tier: TIERS.person, reason: 'dojo:personhood_granted' };

  // 5. Invitee
  if (opts.inviteValid) return { tier: TIERS.invitee, reason: 'invite:valid' };

  // 6. Observer default
  return { tier: TIERS.observer, reason: 'default' };
}
