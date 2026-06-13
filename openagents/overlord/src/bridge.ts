// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — bridge.ts
//
// Adapter from the canonical overlord model (public/member/overseer/overlord +
// levels) onto the existing boardroom-service / dojo-service six-tier shape
// (observer..sovereign). Lets those services adopt the overlord model
// incrementally — keep their challenge/verify/JWT/middleware, just resolve the
// tier through here — without a rewrite.
//
//   public   → 0 observer    (no privileged access)
//   member   → 2 person      (privileged baseline; member level is the new,
//                             finer granularity the legacy tier lacked)
//   overseer → 4 cabinet      (moderator / distributor of privilege)
//   overlord → 5 sovereign    (admin)
//
// Tiers 1 (invitee) and 3 (seat) are invite- and room-scoped — orthogonal to
// the holdings/identity axis — so they are layered by the room/invite logic on
// top of the role resolved here, not produced by it.

import type { Privilege, Role } from "./model.js";

export type Tier = 0 | 1 | 2 | 3 | 4 | 5;

export const ROLE_TO_TIER: Record<Role, Tier> = {
  public: 0,
  member: 2,
  overseer: 4,
  overlord: 5,
};

export const TIER_NAME: Record<Tier, string> = {
  0: "observer",
  1: "invitee",
  2: "person",
  3: "seat",
  4: "cabinet",
  5: "sovereign",
};

export function roleToTier(role: Role): Tier {
  return ROLE_TO_TIER[role];
}

/**
 * Map a resolved Privilege to the legacy tiered-session fields. `level` is
 * preserved alongside so consumers can use the finer overlord granularity while
 * still gating legacy `requiresTier(...)` checks.
 */
export function privilegeToSession(p: Privilege, scope: string): {
  address: string;
  tier: Tier;
  tier_name: string;
  role: Role;
  level: number;
  privileged: boolean;
  scope: string;
  chronos: { consensus: string; promised_by: string };
  reason: string;
} {
  const tier = roleToTier(p.role);
  return {
    address: p.address,
    tier,
    tier_name: TIER_NAME[tier],
    role: p.role,
    level: p.level,
    privileged: p.privileged,
    scope,
    chronos: { consensus: p.asOf.consensus, promised_by: p.asOf.promisedBy },
    reason: p.reason,
  };
}
