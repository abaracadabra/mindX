// SPDX-License-Identifier: Apache-2.0
//
// lookupName — the read-many helper that powers <bankoneth-name-card>.
//
// Beats ENS's per-record sequential reads by batching:
//   - NameWrapper.getData()    → owner + fuses + expiry
//   - Resolver.addr(node)       → primary ETH address (or TBA override)
//   - Resolver.text(node, k)    → text records for the BANKON keyset
//   - InftAdapter.tbaAddressOf  → ERC-6551 wallet (if iNFT Mode A bound)
//
// All reads via viem multicall when the chain supports it; falls back to
// sequential reads otherwise.

import {
  type Address,
  type Hex,
  type PublicClient,
  keccak256,
  encodePacked,
  labelhash,
  namehash,
  pad,
} from "viem";

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
  /** Full subname queried, e.g. "alice.bankon.eth". */
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
  /** ERC-6551 TBA from BankonInftAdapter (zero if iNFT not minted). */
  tba: Address;
  /** True if all four soulbound fuses are burned (PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY). */
  isSoulbound: boolean;
  /** UNIX-ms timestamp of the lookup. */
  fetchedAt: number;
}

export interface LookupArgs {
  publicClient:        PublicClient;
  nameWrapperAddr:     Address;
  resolverAddr:        Address;
  inftAdapterAddr?:    Address;     // optional — pass to fill `tba`
  /** Optional override of the record keys to fetch. Defaults to BANKON_RECORD_KEYS. */
  recordKeys?:         readonly string[];
  /** The full subname, e.g. "alice.bankon.eth". */
  name: string;
}

// ── Minimal inline ABIs (no JSON imports — keeps the bundle small) ──

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

const RESOLVER_ABI = [
  {
    type: "function",
    name: "addr",
    stateMutability: "view",
    inputs: [{ name: "node", type: "bytes32" }],
    outputs: [{ name: "", type: "address" }],
  },
  {
    type: "function",
    name: "text",
    stateMutability: "view",
    inputs: [
      { name: "node", type: "bytes32" },
      { name: "key",  type: "string"  },
    ],
    outputs: [{ name: "", type: "string" }],
  },
] as const;

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
  const node = namehash(args.name) as Hex;
  const lh   = labelhash(args.name.split(".")[0]!) as Hex;
  const keys = args.recordKeys ?? BANKON_RECORD_KEYS;

  // Run reads in parallel — viem batches under the hood when transport supports it.
  const [
    nwData,
    addrVal,
    ...textVals
  ] = await Promise.all([
    args.publicClient.readContract({
      address: args.nameWrapperAddr,
      abi: NAME_WRAPPER_ABI,
      functionName: "getData",
      args: [BigInt(node)],
    }) as Promise<readonly [Address, number, bigint]>,
    args.publicClient.readContract({
      address: args.resolverAddr,
      abi: RESOLVER_ABI,
      functionName: "addr",
      args: [node],
    }).catch(() => ZERO_ADDR) as Promise<Address>,
    ...keys.map(k =>
      args.publicClient.readContract({
        address: args.resolverAddr,
        abi: RESOLVER_ABI,
        functionName: "text",
        args: [node, k],
      }).catch(() => "") as Promise<string>
    ),
  ]);

  const [owner, fuses, expiry] = nwData;

  // The resolver's `addr` returns TBA when iNFT Mode A is active. To get the
  // raw owner address we'd need a separate `_addr[]` getter, but the
  // canonical resolver doesn't expose it, so we use the NameWrapper owner
  // as the raw fallback.
  const rawAddr = owner;

  // Separate TBA lookup via the adapter (independent of resolver state).
  let tba: Address = ZERO_ADDR;
  if (args.inftAdapterAddr && args.inftAdapterAddr !== ZERO_ADDR) {
    try {
      tba = await args.publicClient.readContract({
        address: args.inftAdapterAddr,
        abi: INFT_ADAPTER_ABI,
        functionName: "tbaAddressOf",
        args: [lh],
      }) as Address;
    } catch { /* adapter missing or label unbound — leave zero */ }
  }

  const records: Record<string, string> = {};
  for (let i = 0; i < keys.length; i++) {
    records[keys[i]!] = textVals[i] ?? "";
  }

  const soulboundMask =
    FUSE.PARENT_CANNOT_CONTROL |
    FUSE.CANNOT_UNWRAP         |
    FUSE.CANNOT_TRANSFER       |
    FUSE.CAN_EXTEND_EXPIRY;
  const isSoulbound = (fuses & soulboundMask) === soulboundMask;

  return {
    name: args.name,
    node,
    owner,
    fuses,
    expiry: Number(expiry),
    addr: addrVal,
    rawAddr,
    records,
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
