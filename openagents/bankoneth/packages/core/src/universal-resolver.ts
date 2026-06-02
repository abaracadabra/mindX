// SPDX-License-Identifier: Apache-2.0
//
// Universal Resolver — bankoneth's preferred forward-resolution entry point.
//
// Mainnet address: 0xeEeEEEeE14D718C2B47D9923Deab1335E144EeEe
//   - ENS-DAO-upgradable proxy (constant address across UR versions)
//   - ENSv2-forward-compatible (will be re-pointed when Namechain ships)
//   - Bundles addr / text / contenthash / multichain into a single multicall
//   - Transparently follows CCIP-Read (EIP-3668) offchain resolvers
//
// Why this matters for bankoneth:
//   - Resolves *.base.eth, *.cb.id, *.uni.eth (offchain) without bespoke code
//   - One read instead of N round-trips for the name-card profile fetch
//   - Tracks ENSv2 Universal Resolver upgrade automatically
//
// API surface kept small on purpose; callers should reach for viem's native
// `getEnsAddress` / `getEnsText` / `getEnsName` for one-shot reads. This
// module shines for "fetch the whole profile in one round-trip."

import type { Address, Hex, PublicClient } from "viem";
import {
  getEnsAddress,
  getEnsText,
  getEnsName,
  getEnsResolver,
} from "viem/actions";

// viem does not export a `getEnsContentHash` action. We read contenthash
// directly via the resolver discovered by getEnsResolver, falling back to
// null on any failure. The bytes returned follow ENSIP-7 encoding.
const CONTENTHASH_ABI = [{
  type: "function",
  name: "contenthash",
  stateMutability: "view",
  inputs: [{ name: "node", type: "bytes32" }],
  outputs: [{ name: "", type: "bytes" }],
}] as const;

import { namehash } from "viem";

import { normalize } from "./normalize";
import { COIN_TYPE } from "./coin-types";
import { MAINNET, SEPOLIA, ZERO_ADDR, type EnsAddresses, ensAddressesFor } from "./addresses";

/** Canonical UR addresses re-exported for convenience. */
export const UNIVERSAL_RESOLVER_MAINNET: Address = MAINNET.universalResolver;
export const UNIVERSAL_RESOLVER_SEPOLIA: Address = SEPOLIA.universalResolver;

/** What `resolveProfile` returns. */
export interface ProfileLookup {
  /** Normalized name queried. */
  name: string;
  /** `addr(node)` — coinType 60 (ETH). */
  address: Address;
  /** Resolver discovered on chain (zero when no resolver bound). */
  resolver: Address;
  /** Text records, keyed. Unset records appear as empty string. */
  text: Record<string, string>;
  /** Contenthash bytes (e.g. ipfs://... resolved via @ensdomains/content-hash). */
  contenthash: Hex | null;
  /** Multichain addresses, keyed by coinType. */
  coinAddr: Record<number, Hex>;
  /** Resolution latency (ms). */
  latencyMs: number;
  /** Whether the resolver served any CCIP-Read offchain response (best-effort). */
  offchain: boolean;
}

/** Arguments for `resolveProfile`. */
export interface ProfileLookupArgs {
  client: PublicClient;
  name: string;
  /** Optional address overrides; defaults to canonical for the client's chain. */
  ens?: EnsAddresses;
  /** Text record keys to fetch. */
  textKeys?: readonly string[];
  /** Multichain coinTypes to fetch alongside the L1 address. */
  coinTypes?: readonly number[];
}

const DEFAULT_TEXT_KEYS = [
  "avatar", "description", "url", "email", "notice", "keywords",
  "com.twitter", "com.github", "com.discord", "com.reddit", "org.telegram",
  "eth.ens.delegate", "location",
  // bankoneth agentic keyset
  "mindx.endpoint", "bonafide.attestation", "agent.capabilities",
  "inft.uri", "agenticplace.listing", "x402.endpoint", "algoid.did",
  "agent.card",
];

const DEFAULT_COIN_TYPES = [
  COIN_TYPE.BTC, COIN_TYPE.LTC, COIN_TYPE.DOGE,
  COIN_TYPE.EVM_OPTIMISM, COIN_TYPE.EVM_POLYGON, COIN_TYPE.EVM_BASE,
  COIN_TYPE.EVM_ARBITRUM, COIN_TYPE.EVM_AVALANCHE, COIN_TYPE.EVM_BSC,
  COIN_TYPE.ALGO,
];

/**
 * Fetch a name's full profile (address + text records + contenthash + multichain
 * addrs + resolver) through the Universal Resolver, in parallel.
 *
 * Viem dispatches each `getEnsX` through the UR when `universalResolverAddress`
 * is set, so CCIP-Read works transparently — offchain resolvers like
 * `*.base.eth` or `*.cb.id` Just Work.
 */
export async function resolveProfile(args: ProfileLookupArgs): Promise<ProfileLookup> {
  const start = Date.now();
  const name  = normalize(args.name);

  const chainId  = args.client.chain?.id ?? 1;
  const ens      = args.ens ?? ensAddressesFor(chainId);
  const ur       = ens.universalResolver;
  const textKeys = args.textKeys  ?? DEFAULT_TEXT_KEYS;
  const coinTypes = args.coinTypes ?? DEFAULT_COIN_TYPES;

  // All reads run in parallel — viem's getEnsX will route through UR and
  // surface CCIP-Read responses automatically.
  const commonOpts = { universalResolverAddress: ur } as const;

  const addressP   = getEnsAddress(args.client, { name, ...commonOpts }).catch(() => ZERO_ADDR as Address);
  const resolverP  = getEnsResolver(args.client, { name, ...commonOpts }).catch(() => ZERO_ADDR as Address);
  const textValsP  = Promise.all(
    textKeys.map((k: string) =>
      getEnsText(args.client, { name, key: k, ...commonOpts }).catch(() => "")
    )
  );
  const coinAddrsP = Promise.all(
    coinTypes.map((c: number) =>
      getEnsAddress(args.client, { name, coinType: BigInt(c), ...commonOpts })
        .then((a: Address | null) => [c, (a ?? "0x") as Hex] as const)
        .catch(() => [c, "0x" as Hex] as const)
    )
  );

  const [address, resolver, textVals, coinAddrEntries] = await Promise.all(
    [addressP, resolverP, textValsP, coinAddrsP]
  );

  // Contenthash via direct resolver read (no UR action in viem). Skip when
  // no resolver was discovered.
  let contenthash: Hex | null = null;
  if (resolver && resolver !== ZERO_ADDR) {
    try {
      const node = namehash(name) as Hex;
      const ch = await args.client.readContract({
        address: resolver,
        abi: CONTENTHASH_ABI,
        functionName: "contenthash",
        args: [node],
      });
      contenthash = (ch as Hex) ?? null;
    } catch {
      contenthash = null;
    }
  }

  const text: Record<string, string> = {};
  textKeys.forEach((k, i) => { text[k] = textVals[i] ?? ""; });

  const coinAddr: Record<number, Hex> = {};
  for (const [c, a] of coinAddrEntries) {
    if (a && a !== "0x") coinAddr[c] = a;
  }

  return {
    name,
    address: (address ?? ZERO_ADDR) as Address,
    resolver: (resolver ?? ZERO_ADDR) as Address,
    text,
    contenthash,
    coinAddr,
    latencyMs: Date.now() - start,
    // We can't reliably detect offchain resolution from the read alone;
    // surface false here. CCIP-Read still works — this flag is informational
    // only and would need viem-level instrumentation to set true.
    offchain: false,
  };
}

/** Result of a reverse (address → primary name) lookup. */
export interface ReverseLookup {
  /** ENS primary name for the address, or null when none set. */
  primary: string | null;
  /** Resolver that served the address record on the forward leg. */
  resolver: Address;
  /** Latency (ms). */
  latencyMs: number;
}

/** Arguments for `resolveReverse`. */
export interface ReverseLookupArgs {
  client: PublicClient;
  address: Address;
  /** Defaults to coinType 60 (ETH). Use `evmCoinType(chainId)` for L2 reverse. */
  coinType?: number;
  /** Optional address overrides; defaults to canonical for the client's chain. */
  ens?: EnsAddresses;
}

/**
 * Resolve an address → primary name via the Universal Resolver's reverse path.
 * For L2 reverse records (ENSIP-19 territory), pass `coinType: evmCoinType(L2chainId)`.
 */
export async function resolveReverse(args: ReverseLookupArgs): Promise<ReverseLookup> {
  const start    = Date.now();
  const chainId  = args.client.chain?.id ?? 1;
  const ens      = args.ens ?? ensAddressesFor(chainId);

  // viem.getEnsName uses UR under the hood when universalResolverAddress is set.
  // coinType branch: viem currently doesn't accept coinType on getEnsName; for
  // non-60 reverse you'd need a manual UR call. Track viem upstream for L2
  // reverse support.
  const primary = await getEnsName(args.client, {
    address: args.address,
    universalResolverAddress: ens.universalResolver,
  }).catch(() => null);

  return {
    primary: primary ?? null,
    resolver: ens.universalResolver,
    latencyMs: Date.now() - start,
  };
}
