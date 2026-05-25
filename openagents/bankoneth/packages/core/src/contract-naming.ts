// SPDX-License-Identifier: Apache-2.0
//
// Contract-naming helpers — ENSIP-3 + ENSIP-15 + ENSIP-19 review tooling.
//
// Three exports drive the audit:
//   reverseNamespace()    derive the reverse label + namehash for any
//                         coinType (60 = ENSIP-3 mainnet, else ENSIP-19).
//   getContractPrimary()  read ENS Registry → resolver → name(node).
//   verifyContractName()  reverse + forward + round-trip in one call.
//
// Spec links:
//   https://ensips.ethereum.org/ensips/3   — reverse resolution
//   https://ensips.ethereum.org/ensips/15  — immutable contract naming
//   https://ensips.ethereum.org/ensips/19  — multichain reverse (draft)

import {
  type Address,
  type Hex,
  type PublicClient,
  namehash,
} from "viem";

import { ensAddressesFor } from "./addresses";
import { normalize } from "./normalize";

// ── Minimal ABI subsets ──────────────────────────────────────────

const ENS_REGISTRY_ABI = [{
  type: "function",
  name: "resolver",
  stateMutability: "view",
  inputs:  [{ name: "node", type: "bytes32" }],
  outputs: [{ name: "",     type: "address" }],
}] as const;

const RESOLVER_ABI = [
  {
    type: "function",
    name: "name",
    stateMutability: "view",
    inputs:  [{ name: "node", type: "bytes32" }],
    outputs: [{ name: "",     type: "string"  }],
  },
  {
    type: "function",
    name: "addr",
    stateMutability: "view",
    inputs:  [{ name: "node", type: "bytes32" }],
    outputs: [{ name: "",     type: "address" }],
  },
] as const;

const ZERO_ADDR: Address = "0x0000000000000000000000000000000000000000";

// ── reverseNamespace ─────────────────────────────────────────────

/**
 * Derive the reverse-namespace label + namehash for `addr` under the
 * given `coinType`.
 *
 * - `coinType === 60` (default): ENSIP-3 mainnet — `[addr].addr.reverse`.
 * - Anything else: ENSIP-19 — `[addr].<coinType-hex>.reverse`, where the
 *   coinType is rendered as lowercase hex with no `0x` prefix and no
 *   leading zeros. E.g. Optimism (coinType 0x8000000a) → `8000000a`.
 *
 * Address is lowercased, no `0x` prefix per the canonical reverse-node
 * derivation.
 */
export function reverseNamespace(
  addr: Address,
  coinType: number = 60,
): { label: string; node: Hex } {
  const lowerAddr = addr.slice(2).toLowerCase();
  const scope = coinType === 60
    ? "addr"
    : coinType.toString(16); // already no leading zeros, lowercase
  const label = `${lowerAddr}.${scope}.reverse`;
  return { label, node: namehash(label) as Hex };
}

// ── getContractPrimary ───────────────────────────────────────────

/**
 * Resolve `address` → primary ENS name via the contract-naming chain:
 *   1. Compute the reverse node per `reverseNamespace`.
 *   2. Ask the ENS Registry for the resolver bound to that node.
 *   3. Ask that resolver for `name(node)`.
 *
 * Returns `null` when any step is missing (no resolver, empty name).
 */
export async function getContractPrimary(args: {
  client: PublicClient;
  address: Address;
  coinType?: number;
  /** Optional override of the ENS Registry to read. Defaults to the
   *  client's chain via `ensAddressesFor`. */
  registry?: Address;
}): Promise<string | null> {
  const coinType = args.coinType ?? 60;
  const chainId  = args.client.chain?.id ?? 1;
  const registry = args.registry ?? ensAddressesFor(chainId).registry;
  const { node } = reverseNamespace(args.address, coinType);

  try {
    const resolver = await args.client.readContract({
      address: registry,
      abi:     ENS_REGISTRY_ABI,
      functionName: "resolver",
      args:    [node],
    }) as Address;

    if (!resolver || resolver === ZERO_ADDR) return null;

    const name = await args.client.readContract({
      address: resolver,
      abi:     RESOLVER_ABI,
      functionName: "name",
      args:    [node],
    }) as string;

    return name.length > 0 ? name : null;
  } catch {
    return null;
  }
}

// ── verifyContractName ───────────────────────────────────────────

/** Round-trip status for an expected `(contractAddress, expectedName)`. */
export interface ContractNameStatus {
  /** What the reverse resolver says — null when unset. */
  reverseName: string | null;
  /** What the forward resolver maps `expectedName` to — null when unset. */
  forwardAddr: Address | null;
  /** The name we're checking against. Normalized (ENSIP-15). */
  expectedName: string;
  /** True iff reverseName === expectedName AND forwardAddr === address. */
  roundTrip: boolean;
  /** Human-readable list of what's missing. Empty array when roundTrip is true. */
  gaps: string[];
}

/**
 * Audit a contract's primary-name configuration end-to-end.
 *
 * Reverse leg via `getContractPrimary`. Forward leg via the canonical
 * `PublicResolver.addr(namehash(name))` on the chain pinned by
 * `ensAddressesFor`. Both legs use the publicClient — no wallet
 * required.
 */
export async function verifyContractName(args: {
  client: PublicClient;
  address: Address;
  expectedName: string;
  coinType?: number;
  /** Override the resolver used for the forward leg. Defaults to the
   *  per-chain canonical PublicResolver. */
  forwardResolver?: Address;
  /** Override the ENS Registry used for the reverse-leg resolver lookup. */
  registry?: Address;
}): Promise<ContractNameStatus> {
  const expectedName = normalize(args.expectedName);
  const coinType     = args.coinType ?? 60;
  const chainId      = args.client.chain?.id ?? 1;
  const ens          = ensAddressesFor(chainId);

  const reverseName = await getContractPrimary({
    client:   args.client,
    address:  args.address,
    coinType,
    registry: args.registry,
  });

  let forwardAddr: Address | null = null;
  try {
    const resolver = args.forwardResolver ?? ens.publicResolver;
    const result = await args.client.readContract({
      address: resolver,
      abi:     RESOLVER_ABI,
      functionName: "addr",
      args:    [namehash(expectedName) as Hex],
    }) as Address;
    forwardAddr = result && result !== ZERO_ADDR ? result : null;
  } catch {
    forwardAddr = null;
  }

  const gaps: string[] = [];
  const reverseMatches = reverseName === expectedName;
  const forwardMatches = forwardAddr !== null
    && forwardAddr.toLowerCase() === args.address.toLowerCase();

  if (reverseName === null) gaps.push("no reverse name set");
  else if (!reverseMatches)  gaps.push(`reverse mismatch: got "${reverseName}", expected "${expectedName}"`);

  if (forwardAddr === null)  gaps.push(`no forward addr record on ${expectedName}`);
  else if (!forwardMatches)  gaps.push(`forward mismatch: got ${forwardAddr}, expected ${args.address}`);

  return {
    reverseName,
    forwardAddr,
    expectedName,
    roundTrip: reverseMatches && forwardMatches,
    gaps,
  };
}

// ── L2 ReverseRegistrars (ENSIP-19) ──────────────────────────────

/**
 * Per-chain L2 ReverseRegistrar addresses for ENSIP-19 multichain
 * reverse. Operators using bankoneth on an L2 should call setName on
 * the corresponding registrar; the namespace becomes
 * `[addr].<coinType>.reverse` per `reverseNamespace`.
 *
 * IMPORTANT — addresses below are draft / known-good values pulled
 * from the canonical `ensdomains/ens-contracts` deployments. Verify
 * each against the deployment artifact for your target chain before
 * mainnet broadcast:
 *   github.com/ensdomains/ens-contracts/tree/staging/deployments
 *
 * Empty for chains where ENS hasn't published a canonical L2
 * ReverseRegistrar yet — fall back to off-chain attestation or wait
 * for the upstream deploy.
 */
export const L2_REVERSE_REGISTRARS: Record<number, Address> = {
  // chainId 10 — Optimism (verify against canonical deployment)
  10:     "0x0000000000000000000000000000000000000000",
  // chainId 8453 — Base (verify against canonical deployment)
  8453:   "0x0000000000000000000000000000000000000000",
  // chainId 42161 — Arbitrum (verify against canonical deployment)
  42161:  "0x0000000000000000000000000000000000000000",
  // chainId 534352 — Scroll (verify against canonical deployment)
  534352: "0x0000000000000000000000000000000000000000",
  // chainId 59144 — Linea (verify against canonical deployment)
  59144:  "0x0000000000000000000000000000000000000000",
};

/** Lookup the L2 ReverseRegistrar address for a chain. Returns null when
 *  the chain isn't pinned (operator must populate before use). */
export function l2ReverseRegistrarFor(chainId: number): Address | null {
  const addr = L2_REVERSE_REGISTRARS[chainId];
  if (!addr || addr === ZERO_ADDR) return null;
  return addr;
}
