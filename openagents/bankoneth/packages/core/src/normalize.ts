// SPDX-License-Identifier: Apache-2.0
//
// ENSIP-15 name normalization wrapper around @adraffy/ens-normalize.
//
// Every public entry point in BankonethClient (claim, purchase, host, lookup)
// runs user input through normalize() before hashing / signing / sending. Raw
// labels — including uppercase, leading/trailing whitespace, emoji ZWJ
// sequences, or confusables — must error here rather than silently produce a
// different namehash than the canonical ENS app would produce.

import { ens_normalize, ens_normalize_fragment, ens_split } from "@adraffy/ens-normalize";

/** Thrown when a name fails ENSIP-15 normalization. */
export class EnsNormalizeError extends Error {
  constructor(public readonly raw: string, public readonly cause: Error) {
    super(`[bankoneth] ENSIP-15 normalize failed for "${raw}": ${cause.message}`);
  }
}

/**
 * Normalize a full ENS name (e.g. "ALICE.bankon.eth" → "alice.bankon.eth").
 *
 * Apply this to:
 *   • Any user input that will be hashed (namehash / labelhash)
 *   • Any user input that will be sent to a registrar / resolver setter
 *   • Any name displayed back in the UI (so the canonical form roundtrips)
 *
 * Do NOT apply to:
 *   • Hex inputs (0x-prefixed) — they're not names
 *   • Empty strings — pass through
 */
export function normalize(name: string): string {
  if (name.length === 0) return name;
  try {
    return ens_normalize(name);
  } catch (e) {
    throw new EnsNormalizeError(name, e as Error);
  }
}

/**
 * Normalize a single label fragment (no dots).
 * Useful when the registrar takes a `label` separately from the parent node.
 */
export function normalizeLabel(label: string): string {
  if (label.length === 0) return label;
  if (label.includes(".")) {
    throw new EnsNormalizeError(label, new Error("label cannot contain '.'"));
  }
  try {
    return ens_normalize_fragment(label);
  } catch (e) {
    throw new EnsNormalizeError(label, e as Error);
  }
}

/** Split a normalized name into its labels. Errors if any label is invalid. */
export function splitLabels(name: string): string[] {
  // ens_split returns Label objects whose `input` and `output` are both
  // codepoint arrays (`number[]`). Convert via String.fromCodePoint.
  return ens_split(name).map(l =>
    String.fromCodePoint(...((l.output ?? l.input) as number[]))
  );
}

/** Predicate — true when the input is already normalized. */
export function isNormalized(name: string): boolean {
  try {
    return ens_normalize(name) === name;
  } catch {
    return false;
  }
}
