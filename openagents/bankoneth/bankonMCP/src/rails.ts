// SPDX-License-Identifier: Apache-2.0
//
// rails.ts — ADAPTIVE x402 rail selection. Given the offers in a 402 challenge, pick the rail
// (network + asset) to pay on, honoring: network allowlist, per-call USDC cap, a session spend
// budget, and a preference order. Mirrors the bankon "inference budget metabolism" idea: route to
// the cheapest / most-available rail, adapt as budget depletes.
import type { X402Offer } from "./x402.js";

export interface RailPolicy {
  allowNetworks: string[];        // e.g. ["base","arc","optimism"]
  preferOrder: string[];          // try in this order (cheap/fast first)
  maxPerCallUsdc: bigint;         // hard cap per call (6dp)
  sessionBudgetUsdc: bigint;      // total this session (6dp)
}

export const DEFAULT_POLICY: RailPolicy = {
  allowNetworks: ["base", "arc", "optimism", "polygon", "arbitrum", "base-sepolia"],
  preferOrder: ["base", "arc", "optimism", "polygon", "arbitrum"],
  maxPerCallUsdc: 1_000000n,      // $1
  sessionBudgetUsdc: 50_000000n,  // $50
};

export class AdaptiveRails {
  spent = 0n;
  lastOffer?: X402Offer;
  constructor(public policy: RailPolicy = DEFAULT_POLICY) {}

  remaining(): bigint { return this.policy.sessionBudgetUsdc - this.spent; }

  /** Choose the best payable offer or throw (caps/allowlist/budget enforced). */
  pick(offers: X402Offer[]): X402Offer {
    const ok = offers.filter((o) =>
      o.scheme === "exact" &&
      this.policy.allowNetworks.includes(o.network) &&
      BigInt(o.maxAmountRequired) <= this.policy.maxPerCallUsdc &&
      BigInt(o.maxAmountRequired) <= this.remaining());
    if (!ok.length) throw new Error("no x402 offer within rail policy (allowlist / per-call cap / session budget)");
    // preference order first, then cheapest
    ok.sort((a, b) => {
      const pa = this.policy.preferOrder.indexOf(a.network), pb = this.policy.preferOrder.indexOf(b.network);
      if (pa !== pb) return (pa < 0 ? 99 : pa) - (pb < 0 ? 99 : pb);
      return Number(BigInt(a.maxAmountRequired) - BigInt(b.maxAmountRequired));
    });
    this.lastOffer = ok[0];
    return ok[0];
  }

  /** Record a settled payment against the session budget. */
  charge(amount: bigint) { this.spent += amount; }
}
