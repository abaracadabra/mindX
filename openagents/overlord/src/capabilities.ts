// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — capabilities.ts
//
// The overlord/overseer separation, encoded. The overseer is the moderator /
// distributor of privilege: it can grant and move member access and moderate,
// but it CANNOT run destructive / integrity-affecting operations. Those are
// overlord-only. This is the intentional separation so the overseer cannot
// destroy system integrity, and the overlord is not needed for day-to-day
// privilege distribution.

import type { Role } from "./model.js";

export type Action =
  // public
  | "read.public"
  // member (privileged)
  | "read.member"
  | "act.member"
  // overseer — moderate + distribute privilege (the second-in-command powers)
  | "distribute.privilege"
  | "moderate"
  | "admin.read"
  // DESTRUCTIVE — overlord only
  | "clear"
  | "destroy.cabinet"
  | "rotate.keys"
  | "release.key";

/** Integrity-affecting actions. Overlord-only, regardless of level. */
export const DESTRUCTIVE: readonly Action[] = [
  "clear",
  "destroy.cabinet",
  "rotate.keys",
  "release.key",
];

const CAPS: Record<Role, ReadonlySet<Action>> = {
  public: new Set<Action>(["read.public"]),
  member: new Set<Action>(["read.public", "read.member", "act.member"]),
  overseer: new Set<Action>([
    "read.public",
    "read.member",
    "act.member",
    "distribute.privilege",
    "moderate",
    "admin.read",
  ]),
  overlord: new Set<Action>([
    "read.public",
    "read.member",
    "act.member",
    "distribute.privilege",
    "moderate",
    "admin.read",
    "clear",
    "destroy.cabinet",
    "rotate.keys",
    "release.key",
  ]),
};

/**
 * Can `role` perform `action`? Destructive actions are overlord-only by
 * construction — even an overseer at any level is denied, which is the whole
 * point of the separation. `level` is reserved for finer member/overseer
 * gradations and is accepted now so callers don't change signature later.
 */
export function can(role: Role, action: Action, _level = 1): boolean {
  if (DESTRUCTIVE.includes(action)) return role === "overlord";
  return CAPS[role].has(action);
}

export function capabilities(role: Role): Action[] {
  return [...CAPS[role]];
}
