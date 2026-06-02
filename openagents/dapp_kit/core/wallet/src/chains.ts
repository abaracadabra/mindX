// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Chain catalog for the openagents/ dApp kit.
// Contract: docs/services/wallet_connection_as_a_service.md §5.
//
// Each entry is a viem-compatible Chain object plus a few mindX-specific
// fields (isAlgorand, isMindXNative).

import type { Chain } from "viem";
import {
  mainnet,
  sepolia,
  base,
  baseSepolia,
} from "viem/chains";

export interface ChainEntry extends Chain {
  /** True for non-EVM Algorand chains; routes to a separate adapter. */
  isAlgorand?: true;
  /** True for chains where mindX has Tier-1 / native infrastructure (e.g. 0G). */
  isMindXNative?: true;
}

// 0G Galileo testnet (EVM). Chain id 16601.
export const zerogGalileo: ChainEntry = {
  id: 16601,
  name: "0G Galileo Testnet",
  nativeCurrency: { name: "0G", symbol: "0G", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://evmrpc-testnet.0g.ai"] },
  },
  blockExplorers: {
    default: { name: "ChainScan", url: "https://chainscan-galileo.0g.ai" },
  },
  isMindXNative: true,
};

// 0G mainnet (EVM). Chain id confirmed at deploy time; placeholder for now.
// The real chain id is fixed once 0G mainnet RPC publishes; this entry exists
// so deployments/0g_mainnet.json has a catalog target.
export const zerogMainnet: ChainEntry = {
  id: 16600,
  name: "0G Mainnet",
  nativeCurrency: { name: "0G", symbol: "0G", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://evmrpc.0g.ai"] },
  },
  blockExplorers: {
    default: { name: "ChainScan", url: "https://chainscan.0g.ai" },
  },
  isMindXNative: true,
};

// Algorand mainnet (synthetic EIP-155 id 416001 for routing purposes;
// the underlying chain is non-EVM and uses algosdk).
export const algorandMainnet: ChainEntry = {
  id: 416001,
  name: "Algorand Mainnet",
  nativeCurrency: { name: "Algorand", symbol: "ALGO", decimals: 6 },
  rpcUrls: {
    default: { http: ["https://mainnet-api.algonode.cloud"] },
  },
  blockExplorers: {
    default: { name: "AlgoExplorer", url: "https://allo.info" },
  },
  isAlgorand: true,
};

export const algorandTestnet: ChainEntry = {
  id: 416002,
  name: "Algorand Testnet",
  nativeCurrency: { name: "Algorand", symbol: "ALGO", decimals: 6 },
  rpcUrls: {
    default: { http: ["https://testnet-api.algonode.cloud"] },
  },
  blockExplorers: {
    default: { name: "AlgoExplorer", url: "https://testnet.allo.info" },
  },
  isAlgorand: true,
};

/**
 * Seed catalog. Consumers add their own chains via
 * `connect({ extraChains: [...] })`.
 */
export const CHAINS: Record<string, ChainEntry> = {
  ethereum: { ...mainnet },
  sepolia: { ...sepolia },
  base: { ...base },
  "base-sepolia": { ...baseSepolia },
  "0g-galileo": zerogGalileo,
  "0g-mainnet": zerogMainnet,
  "algorand-mainnet": algorandMainnet,
  "algorand-testnet": algorandTestnet,
};

/**
 * Look up a chain entry by its catalog key.
 */
export function chainByKey(key: string): ChainEntry | undefined {
  return CHAINS[key];
}

/**
 * Look up a chain entry by EIP-155 chain id.
 */
export function chainById(id: number): ChainEntry | undefined {
  for (const c of Object.values(CHAINS)) {
    if (c.id === id) return c;
  }
  return undefined;
}
