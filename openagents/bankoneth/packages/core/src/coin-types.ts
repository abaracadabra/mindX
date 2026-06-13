// SPDX-License-Identifier: Apache-2.0
//
// ENSIP-9 (multichain address resolution) + ENSIP-11 (EVM chain coinType
// derivation) tables for use with PublicResolver `addr(node, coinType)` and
// our own BankonSubnameResolver multichain setter.
//
// ENSIP-11 derivation:
//   coinType = (0x80000000 | chainId) >>> 0
//
// The top bit (0x80000000) marks "this is an EVM chain pointing at chainId".
// All non-EVM coin types follow SLIP-0044 directly. ENSIP-1 mandates that
// addr(node) without a coinType is exactly equivalent to addr(node, 60).
//
// Spec links:
//   https://ensips.ethereum.org/ensips/9   — multicoin addr interface
//   https://ensips.ethereum.org/ensips/11  — EVM coinType derivation

/** Derive the ENSIP-11 EVM coinType from a chainId. */
export function evmCoinType(chainId: number): number {
  // `>>> 0` coerces to unsigned 32-bit. Required so the value fits in the
  // ENS spec range (uint32-ish). Without it JS bit-OR can return negatives.
  return (0x80000000 | chainId) >>> 0;
}

/** Reverse — extract the chainId from an EVM coinType. Returns -1 if not EVM. */
export function chainIdFromCoinType(coinType: number): number {
  if ((coinType & 0x80000000) === 0) return -1;
  return coinType & 0x7fffffff;
}

/** Predicate — is this coinType an EVM chain (vs a SLIP-44 non-EVM)? */
export function isEvmCoinType(coinType: number): boolean {
  return (coinType & 0x80000000) !== 0;
}

// ── SLIP-0044 non-EVM coin types (subset) ────────────────────────────
// Source: github.com/satoshilabs/slips/blob/master/slip-0044.md

export const COIN_TYPE = {
  // Non-EVM (SLIP-44 native)
  BTC:                 0,
  LTC:                 2,
  DOGE:                3,
  ETH:                60,       // ENSIP-1 binds addr(node) to coinType 60
  ETC:                61,
  XRP:               144,
  BCH:               145,
  BNB:               714,       // BNB Beacon (legacy), not BSC

  // EVM (ENSIP-11 derived — all top-bit-set)
  EVM_ETHEREUM:      evmCoinType(1),          // 2147483649
  EVM_OPTIMISM:      evmCoinType(10),         // 2147483658
  EVM_BSC:           evmCoinType(56),         // 2147483704
  EVM_POLYGON:       evmCoinType(137),        // 2147483785
  EVM_FANTOM:        evmCoinType(250),
  EVM_ZKSYNC:        evmCoinType(324),
  EVM_ARBITRUM:      evmCoinType(42161),      // 2147525809
  EVM_AVALANCHE:     evmCoinType(43114),      // 2147526762
  EVM_GNOSIS:        evmCoinType(100),
  EVM_CELO:          evmCoinType(42220),
  EVM_BASE:          evmCoinType(8453),       // 2147492101
  EVM_SCROLL:        evmCoinType(534352),
  EVM_LINEA:         evmCoinType(59144),
  EVM_BLAST:         evmCoinType(81457),
  EVM_MANTLE:        evmCoinType(5000),
  EVM_ZORA:          evmCoinType(7777777),

  // Algorand (non-EVM but allocated via SLIP-0044 #283)
  ALGO:              0x8000011B,
} as const;

export type CoinTypeName = keyof typeof COIN_TYPE;

/** Friendly metadata for the UI's multichain address selector. */
export interface CoinTypeMeta {
  readonly name:     CoinTypeName;
  readonly label:    string;     // human label, e.g. "Polygon"
  readonly coinType: number;
  readonly chainId?: number;     // present for EVM entries
  readonly slip44?:  number;     // present for non-EVM SLIP-44 entries
}

const META: Record<CoinTypeName, CoinTypeMeta> = {
  BTC:           { name: "BTC",          label: "Bitcoin",         coinType: COIN_TYPE.BTC,           slip44: 0     },
  LTC:           { name: "LTC",          label: "Litecoin",        coinType: COIN_TYPE.LTC,           slip44: 2     },
  DOGE:          { name: "DOGE",         label: "Dogecoin",        coinType: COIN_TYPE.DOGE,          slip44: 3     },
  ETH:           { name: "ETH",          label: "Ethereum",        coinType: COIN_TYPE.ETH,           slip44: 60    },
  ETC:           { name: "ETC",          label: "Ethereum Classic",coinType: COIN_TYPE.ETC,           slip44: 61    },
  XRP:           { name: "XRP",          label: "Ripple",          coinType: COIN_TYPE.XRP,           slip44: 144   },
  BCH:           { name: "BCH",          label: "Bitcoin Cash",    coinType: COIN_TYPE.BCH,           slip44: 145   },
  BNB:           { name: "BNB",          label: "BNB Beacon",      coinType: COIN_TYPE.BNB,           slip44: 714   },
  EVM_ETHEREUM:  { name: "EVM_ETHEREUM", label: "Ethereum (EVM)",  coinType: COIN_TYPE.EVM_ETHEREUM,  chainId: 1    },
  EVM_OPTIMISM:  { name: "EVM_OPTIMISM", label: "Optimism",        coinType: COIN_TYPE.EVM_OPTIMISM,  chainId: 10   },
  EVM_BSC:       { name: "EVM_BSC",      label: "BNB Smart Chain", coinType: COIN_TYPE.EVM_BSC,       chainId: 56   },
  EVM_POLYGON:   { name: "EVM_POLYGON",  label: "Polygon",         coinType: COIN_TYPE.EVM_POLYGON,   chainId: 137  },
  EVM_FANTOM:    { name: "EVM_FANTOM",   label: "Fantom",          coinType: COIN_TYPE.EVM_FANTOM,    chainId: 250  },
  EVM_ZKSYNC:    { name: "EVM_ZKSYNC",   label: "zkSync Era",      coinType: COIN_TYPE.EVM_ZKSYNC,    chainId: 324  },
  EVM_ARBITRUM:  { name: "EVM_ARBITRUM", label: "Arbitrum One",    coinType: COIN_TYPE.EVM_ARBITRUM,  chainId: 42161 },
  EVM_AVALANCHE: { name: "EVM_AVALANCHE",label: "Avalanche",       coinType: COIN_TYPE.EVM_AVALANCHE, chainId: 43114 },
  EVM_GNOSIS:    { name: "EVM_GNOSIS",   label: "Gnosis",          coinType: COIN_TYPE.EVM_GNOSIS,    chainId: 100  },
  EVM_CELO:      { name: "EVM_CELO",     label: "Celo",            coinType: COIN_TYPE.EVM_CELO,      chainId: 42220 },
  EVM_BASE:      { name: "EVM_BASE",     label: "Base",            coinType: COIN_TYPE.EVM_BASE,      chainId: 8453 },
  EVM_SCROLL:    { name: "EVM_SCROLL",   label: "Scroll",          coinType: COIN_TYPE.EVM_SCROLL,    chainId: 534352 },
  EVM_LINEA:     { name: "EVM_LINEA",    label: "Linea",           coinType: COIN_TYPE.EVM_LINEA,     chainId: 59144 },
  EVM_BLAST:     { name: "EVM_BLAST",    label: "Blast",           coinType: COIN_TYPE.EVM_BLAST,     chainId: 81457 },
  EVM_MANTLE:    { name: "EVM_MANTLE",   label: "Mantle",          coinType: COIN_TYPE.EVM_MANTLE,    chainId: 5000 },
  EVM_ZORA:      { name: "EVM_ZORA",     label: "Zora",            coinType: COIN_TYPE.EVM_ZORA,      chainId: 7777777 },
  ALGO:          { name: "ALGO",         label: "Algorand",        coinType: COIN_TYPE.ALGO,          slip44: 283   },
};

/** All entries — useful for populating a UI select. */
export const COIN_TYPES: CoinTypeMeta[] = Object.values(META);

/** Lookup metadata by name. */
export function metaFor(name: CoinTypeName): CoinTypeMeta {
  return META[name];
}

/** Lookup metadata by coinType value. Returns undefined if unknown. */
export function metaForCoinType(coinType: number): CoinTypeMeta | undefined {
  return COIN_TYPES.find(m => m.coinType === coinType);
}
