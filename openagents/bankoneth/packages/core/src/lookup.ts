// SPDX-License-Identifier: Apache-2.0
//
// lookupName — the read-many helper that powers <bankoneth-name-card>.
//
// v2 changes (Phase 1.2):
//   - resolver reads now route through the Universal Resolver (`resolveProfile`)
//     so CCIP-Read offchain resolvers (`*.base.eth`, `*.cb.id`) Just Work
//   - name input runs through ENSIP-15 `@adraffy/ens-normalize` first
//   - `resolverAddr` argument is now OPTIONAL — UR discovers the resolver via
//     the ENS Registry; explicit passing is only useful for testing
//
// Three direct reads remain (NOT routed through UR):
//   - NameWrapper.getData()    → owner + fuses + expiry (wrapper state, not a resolver call)
//   - InftAdapter.tbaAddressOf → ERC-6551 wallet (bankoneth-specific, not standard ENS)
//
// Public API surface (preserved for <b-name-card> backwards-compat):
//   NameLookup, LookupArgs, lookupName, hasFuse, formatExpiry,
//   BANKON_RECORD_KEYS, FUSE, RecordKey, FuseName

import {
  type Address,
  type Hex,
  type PublicClient,
  labelhash,
  namehash,
} from "viem";

import { normalize } from "./normalize";
import { resolveProfile } from "./universal-resolver";

/** Standard BANKON text-record keys read by the name card. */
export const BANKON_RECORD_KEYS = [
  "avatar",
  "url",
  "description",
  "com.twitter",
  "com.github",
  "email",
  "mindx.endpoint",
  "bonafide.attestation",
  "agent.capabilities",
  "inft.uri",
  "agenticplace.listing",
  "x402.endpoint",
  "algoid.did",
] as const;

export type RecordKey = (typeof BANKON_RECORD_KEYS)[number];

/** ENS fuse bitmap. Names per NameWrapper. */
export const FUSE = {
  CANNOT_UNWRAP:          1 << 0,
  CANNOT_BURN_FUSES:      1 << 1,
  CANNOT_TRANSFER:        1 << 2,
  CANNOT_SET_RESOLVER:    1 << 3,
  CANNOT_SET_TTL:         1 << 4,
  CANNOT_CREATE_SUBDOMAIN:1 << 5,
  CANNOT_APPROVE:         1 << 6,
  PARENT_CANNOT_CONTROL:  1 << 16,
  IS_DOT_ETH:             1 << 17,
  CAN_EXTEND_EXPIRY:      1 << 18,
} as const;
export type FuseName = keyof typeof FUSE;

/** All info <bankoneth-name-card> needs to render. */
export interface NameLookup {
  /** Full subname queried, e.g. "alice.bankon.eth" (normalized). */
  name: string;
  /** Bytes32 namehash. */
  node: Hex;
  /** Wrapped-NFT owner (zero = not minted). */
  owner: Address;
  /** Set of burned fuses. Use `hasFuse(lookup, "CANNOT_UNWRAP")` to query. */
  fuses: number;
  /** Unix-seconds expiry (0 = not minted / non-expiring). */
  expiry: number;
  /** addr(node) — returns TBA when iNFT Mode A active, else raw owner addr. */
  addr: Address;
  /** Just the raw owner address (bypasses TBA override) — useful for UI labelling. */
  rawAddr: Address;
  /** Text records, key → value (empty string if unset). */
  records: Record<string, string>;
  /** Multichain addresses, keyed by ENSIP-11/SLIP-44 coinType (sparse). */
  coinAddr: Record<number, Hex>;
  /** ERC-6551 TBA from BankonInftAdapter (zero if iNFT not minted). */
  tba: Address;
  /**
   * True if all four soulbound fuses are burned (PARENT_CANNOT_CONTROL |
   * CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY).
   */
  isSoulbound: boolean;
  /** UNIX-ms timestamp of the lookup. */
  fetchedAt: number;
}

export interface LookupArgs {
  publicClient:        PublicClient;
  /** NameWrapper for the fuse + expiry + owner read. */
  nameWrapperAddr:     Address;
  /**
   * Optional explicit resolver address. v2: defaults to undefined — the
   * Universal Resolver discovers the bound resolver via the ENS Registry.
   * Pass explicitly only for tests or for resolvers not registered on chain.
   */
  resolverAddr?:       Address;
  /** Optional iNFT adapter — pass to populate `tba`. */
  inftAdapterAddr?:    Address;
  /** Optional override of the text-record keys to fetch. */
  recordKeys?:         readonly string[];
  /** Optional override of the multichain coinTypes to fetch. */
  coinTypes?:          readonly number[];
  /** The full subname, e.g. "alice.bankon.eth". */
  name: string;
}

// ── Minimal inline ABIs ────────────────────────────────────────────

const NAME_WRAPPER_ABI = [{
  type: "function",
  name: "getData",
  stateMutability: "view",
  inputs: [{ name: "id", type: "uint256" }],
  outputs: [
    { name: "owner",  type: "address" },
    { name: "fuses",  type: "uint32" },
    { name: "expiry", type: "uint64" },
  ],
}] as const;

const INFT_ADAPTER_ABI = [{
  type: "function",
  name: "tbaAddressOf",
  stateMutability: "view",
  inputs: [{ name: "labelhash", type: "bytes32" }],
  outputs: [{ name: "", type: "address" }],
}] as const;

const ZERO_ADDR: Address = "0x0000000000000000000000000000000000000000";

/** Stitch together the full record + TBA + fuses dataset. */
export async function lookupName(args: LookupArgs): Promise<NameLookup> {
  const name = normalize(args.name);
  const node = namehash(name) as Hex;
  const lh   = labelhash(name.split(".")[0]!) as Hex;

  const recordKeys = args.recordKeys;
  const coinTypes  = args.coinTypes;

  // Three parallel branches:
  //   1. NameWrapper.getData (owner / fuses / expiry) — direct
  //   2. Universal Resolver profile (addr / text / contenthash / multichain)
  //   3. iNFT adapter TBA — direct
  const [nwData, profile, tba] = await Promise.all([
    args.publicClient.readContract({
      address: args.nameWrapperAddr,
      abi: NAME_WRAPPER_ABI,
      functionName: "getData",
      args: [BigInt(node)],
    }).catch(() => [ZERO_ADDR, 0, 0n] as const) as Promise<readonly [Address, number, bigint]>,

    resolveProfile({
      client: args.publicClient,
      name,
      textKeys: recordKeys,
      coinTypes,
    }).catch(() => ({
      name,
      address: ZERO_ADDR,
      resolver: ZERO_ADDR,
      text: {} as Record<string, string>,
      contenthash: null,
      coinAddr: {} as Record<number, Hex>,
      latencyMs: 0,
      offchain: false,
    })),

    (async (): Promise<Address> => {
      if (!args.inftAdapterAddr || args.inftAdapterAddr === ZERO_ADDR) return ZERO_ADDR;
      try {
        return (await args.publicClient.readContract({
          address: args.inftAdapterAddr,
          abi: INFT_ADAPTER_ABI,
          functionName: "tbaAddressOf",
          args: [lh],
        })) as Address;
      } catch {
        return ZERO_ADDR;
      }
    })(),
  ]);

  const [owner, fuses, expiry] = nwData;

  // resolveProfile only returns the canonical BANKON_RECORD_KEYS subset by
  // default plus any caller-provided keys. The name-card consumes records
  // by exact key so we don't need to fill unset keys — but for stable iteration
  // make sure every requested key has a string value (possibly empty).
  const wantedKeys = recordKeys ?? BANKON_RECORD_KEYS;
  const records: Record<string, string> = {};
  for (const k of wantedKeys) records[k] = profile.text[k] ?? "";

  const soulboundMask =
    FUSE.PARENT_CANNOT_CONTROL |
    FUSE.CANNOT_UNWRAP         |
    FUSE.CANNOT_TRANSFER       |
    FUSE.CAN_EXTEND_EXPIRY;
  const isSoulbound = (fuses & soulboundMask) === soulboundMask;

  return {
    name,
    node,
    owner,
    fuses,
    expiry: Number(expiry),
    // UR address read returns the resolver's `addr(node)`. For bankoneth
    // subnames, our resolver's `addr` overrides to the TBA when bound; for
    // ENS PublicResolver it returns the raw addr record. Same semantics.
    addr: profile.address,
    // Raw owner from the NameWrapper, regardless of TBA override.
    rawAddr: owner,
    records,
    coinAddr: profile.coinAddr,
    tba,
    isSoulbound,
    fetchedAt: Date.now(),
  };
}

/** Convenience predicate. */
export function hasFuse(lookup: { fuses: number }, name: FuseName): boolean {
  return (lookup.fuses & FUSE[name]) === FUSE[name];
}

/** Human-readable expiry: "expires in 11 mo", "expired 3 d ago", "no expiry". */
export function formatExpiry(unixSec: number, now = Math.floor(Date.now() / 1000)): string {
  if (unixSec === 0) return "no expiry";
  const delta = unixSec - now;
  const abs = Math.abs(delta);
  const unit = abs >= 365 * 86400 ? ["yr",  365 * 86400] :
               abs >= 30 * 86400  ? ["mo",  30 * 86400]  :
               abs >= 86400       ? ["d",   86400]       :
               abs >= 3600        ? ["h",   3600]        :
                                    ["m",   60];
  const n = Math.round(abs / (unit[1] as number));
  return delta >= 0 ? `expires in ${n} ${unit[0]}` : `expired ${n} ${unit[0]} ago`;
}
