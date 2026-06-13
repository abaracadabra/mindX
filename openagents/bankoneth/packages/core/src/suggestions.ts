// SPDX-License-Identifier: Apache-2.0
//
// Label-taken suggestion engine.
//
// When `alice` is taken, the UI offers alternatives the user is likely to
// be happy with: trailing numerals, common modifiers, the user's own
// wallet-prefix variant. Each suggestion comes with a batched availability
// check so the UI can render checkmarks beside ones the user can claim
// right now.

import {
  type Address,
  type Hex,
  type PublicClient,
} from "viem";
import { checkAvailability, type AvailabilityResult } from "./availability";

export interface SuggestionsArgs {
  publicClient:    PublicClient;
  nameWrapperAddr: Address;
  parentNode:      Hex;
  /** The original label the user typed that turned out to be taken. */
  label: string;
  /** Optional wallet address — drives the 0xPREFIX-based suggestion. */
  walletAddress?: Address;
  /** Max number of suggestions to return (default 6). */
  limit?: number;
}

/** A label suggestion with live availability + the on-chain node. */
export type Suggestion = AvailabilityResult & { reason: string };

/** Generate alternative labels deterministically from a taken label. */
export function generateAlternatives(args: Omit<SuggestionsArgs, "publicClient" | "nameWrapperAddr">): string[] {
  const base = args.label.trim().toLowerCase();
  if (!base) return [];

  const suggestions: string[] = [];
  const seen = new Set<string>([base]);
  const push = (s: string) => {
    if (s && !seen.has(s) && s !== base) {
      seen.add(s);
      suggestions.push(s);
    }
  };

  // Numeric tails — `alice1`, `alice2`, `alice99`.
  for (const n of [1, 2, 3, 7, 42, 99]) push(`${base}${n}`);

  // Year tail — `alice2026`.
  const year = new Date().getUTCFullYear();
  push(`${base}${year}`);

  // Common modifiers.
  push(`${base}_`);
  push(`_${base}`);
  push(`${base}eth`);
  push(`the${base}`);
  push(`${base}dao`);
  push(`${base}xyz`);

  // Wallet-prefix flavour — useful for agent claimants.
  if (args.walletAddress) {
    push(`${args.walletAddress.slice(2, 6).toLowerCase()}${base}`);
    push(`${base}${args.walletAddress.slice(-4).toLowerCase()}`);
  }

  return suggestions.slice(0, args.limit ?? 6);
}

/** Why each alternative was generated — surfaced in the UI as a small label. */
export function reasonFor(base: string, candidate: string, year = new Date().getUTCFullYear()): string {
  if (candidate === `${base}${year}`) return "current year";
  if (/\d+$/.test(candidate) && candidate.startsWith(base)) return "numeric suffix";
  if (candidate.endsWith("eth")) return "explicit eth tail";
  if (candidate.endsWith("dao") || candidate.endsWith("xyz")) return "common suffix";
  if (candidate.startsWith("the")) return "definite-article variant";
  if (candidate.includes("_")) return "underscore variant";
  return "wallet-prefix";
}

/** Run availability checks across all generated alternatives in parallel. */
export async function suggestAlternatives(args: SuggestionsArgs): Promise<Suggestion[]> {
  const candidates = generateAlternatives({
    label:         args.label,
    walletAddress: args.walletAddress,
    parentNode:    args.parentNode,
    limit:         args.limit,
  });
  const checks = await Promise.allSettled(candidates.map(c =>
    checkAvailability({
      publicClient:    args.publicClient,
      nameWrapperAddr: args.nameWrapperAddr,
      parentNode:      args.parentNode,
      label:           c,
    })
  ));
  return checks
    .map((c, i) => c.status === "fulfilled"
      ? { ...c.value, reason: reasonFor(args.label, candidates[i]!) }
      : null)
    .filter((s): s is Suggestion => s !== null);
}
