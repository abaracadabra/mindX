/**
 * Shadow-overlord six-tier model.
 *
 *   0 observer  — anonymous; read public rooms only
 *   1 invitee   — wallet with a signed invite token; can accept invite
 *   2 person    — BONA FIDE balance (or K-of-N vouched pre-mint)
 *   3 seat      — listed in room.seats[]; vote in that room
 *   4 cabinet   — listed in service.cabinet[]; manage rooms, issue invites
 *   5 sovereign — DAIO multisig OR shadow-overlord ECDSA+JWT
 *
 * Higher tier subsumes lower tiers. An endpoint that requires tier ≥ N
 * accepts any session with tier in {N..5}.
 */

export type Tier = 0 | 1 | 2 | 3 | 4 | 5;

export const TIERS = {
  observer:  0,
  invitee:   1,
  person:    2,
  seat:      3,
  cabinet:   4,
  sovereign: 5,
} as const;

export type TierName = keyof typeof TIERS;

export interface TieredSession {
  address: `0x${string}`;
  tier: Tier;
  /** room_id (for room-scoped tiers 1..3) or service name (for service-wide tiers 4..5). */
  scope: string;
  /** Personhood status snapshot at JWT-issue time. */
  personhood: 'none' | 'pending' | 'granted';
  exp: number;
  iat: number;
}

export function tierName(t: Tier): TierName {
  return (Object.entries(TIERS).find(([_, v]) => v === t)?.[0] ?? 'observer') as TierName;
}

export function requiresTier(session: TieredSession | null, required: Tier, scope?: string): boolean {
  if (!session) return required === 0;
  if (session.tier < required) return false;
  // Tier 4+ is service-wide; tier 1..3 is room-scoped. If a scope is requested,
  // enforce that the session's scope matches.
  if (scope && session.tier < TIERS.cabinet && session.scope !== scope) return false;
  return true;
}
