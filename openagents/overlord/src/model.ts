// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — model.ts
//
// The overlord/overseer privilege hierarchy. One privilege axis, `public` at
// the bottom: privilege is *the access the public does not have*. Each role
// carries levels.
//
//   public   — no qualifying holding ⇒ no privileged access (public surface only)
//   member   — holds the qualifying asset ⇒ privileged; level = f(amount, tenure)
//   overseer — moderator / distributor of privilege; signature-proven address;
//              can grant/move member access but CANNOT run destructive ops
//   overlord — admin; signature-proven SHADOW_OVERLORD_ADDRESS; the only role
//              that can run destructive ops
//
// Identity = a public wallet key proven by signature (ECDSA, + ERC-1271 for
// smart accounts). Privilege = on-chain holdings whose blockchain timestamp
// (tenure) is confirmed via chronos.agent (multi-source: hardware + multi-chain
// block time, with a consensus confidence). The resolved {role, level} is a
// pure function of (address, signature, holdings, tenure, chronos).

import type { Address } from "viem";

export type Role = "public" | "member" | "overseer" | "overlord";

/** Higher ordinal subsumes lower for the public/privileged boundary. */
export const ROLE_ORDINAL: Record<Role, number> = {
  public: 0,
  member: 1,
  overseer: 2,
  overlord: 3,
};

export const PRIVILEGED_ROLES: readonly Role[] = ["member", "overseer", "overlord"];

/** Privilege = access the public lacks. True for member/overseer/overlord. */
export function isPrivileged(role: Role): boolean {
  return ROLE_ORDINAL[role] >= ROLE_ORDINAL.member;
}

// ── chronos promised-time (mirrors agents/chronos_agent.py PromisedTime) ──
export type ChronosConsensus = "correlated" | "degraded" | "drifted" | "offline";

export interface ChronosTime {
  /** Unix seconds (the integer part of chronos `unix_18dp`). */
  unix: number;
  /** Cross-source agreement tier. `offline` ⇒ tenure is unverified. */
  consensus: ChronosConsensus;
  confidenceMs: number;
  promisedBy: string; // "chronos.agent" | "local"
}

// ── holdings config ──────────────────────────────────────────────────────
export type TokenStandard = "erc20" | "erc721" | "erc1155";

/** A privilege band: the minimum holding amount AND minimum tenure to reach `level`. */
export interface LevelBand {
  level: number; // 1..n
  /** Raw token units (wei for ERC-20, token count for 721/1155). */
  minAmount: bigint;
  /** Chronos-verified holding age (seconds) required. 0 = no tenure requirement. */
  minTenureSec: number;
  label?: string;
}

export interface HoldingConfig {
  chainId: number;
  token: Address;
  standard: TokenStandard;
  /** For ERC-1155: which id to read. */
  tokenId?: bigint;
  /** Display only. */
  decimals?: number;
  /** Minimum balance to be a `member` at all (the public/privileged boundary). */
  threshold: bigint;
  /** Ascending by level; the highest band the holder qualifies for wins. */
  levelBands: LevelBand[];
  /**
   * Block to start the acquisition-timestamp Transfer scan from. Set this to
   * the token's deploy block: most RPCs reject `getLogs` over a 0→latest range
   * on a busy token, which would silently null the tenure (every member stuck
   * at L1). Default 0n.
   */
  fromBlock?: bigint;
}

/** The full overlord-template configuration (per deployment; nothing hardcoded). */
export interface OverlordConfig {
  /** The canonical SHADOW_OVERLORD_ADDRESS. */
  overlord: Address;
  /** Configured overseer address set (moderators / distributors of privilege). */
  overseers: readonly Address[];
  holding: HoldingConfig;
  /** Base URL for chronos `GET /v1/oracle/time`. Empty ⇒ same-origin. */
  chronosBaseUrl?: string;
  /** RFC-3986 host shown in the signed challenge (e.g. "mindx.pythai.net"). */
  domain: string;
}

/**
 * The resolved privilege state — event-verified, a pure function of
 * (address, signature, holdings, tenure, chronos).
 */
export interface Privilege {
  role: Role;
  level: number;
  /** role !== "public" — i.e. has access the public does not. */
  privileged: boolean;
  address: Address;
  reason: string;
  /** The chronos-promised time this resolution was computed against. */
  asOf: ChronosTime;
  /** Present for the member axis. */
  holding?: {
    amount: bigint;
    /** Block-timestamp (unix s) of the earliest acquisition, or null if unknown. */
    acquiredAt: number | null;
    /** Chronos-verified `asOf.unix - acquiredAt`, or null if unknown. */
    tenureSec: number | null;
  };
}
