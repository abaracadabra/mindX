// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Per-chain deploy defaults: RPC URL, native currency, default gas budget.
// Contract: docs/services/contract_deployment_as_a_service.md §8.

export interface ChainDeployConfig {
  /** Catalog key (e.g. "base-sepolia"). */
  networkKey: string;
  /** EIP-155 chain id. */
  chainId: number;
  /** True if mainnet. Mainnet deploys trigger the two-step intent flow. */
  isMainnet: boolean;
  /** Default RPC URL (operator-overridable via env). */
  rpcUrl: string;
  /** Etherscan-family verifier URL (or undefined when not applicable). */
  verifierUrl?: string;
  /** Default per-deploy gas budget in USD. */
  defaultGasBudgetUSD: number;
  /** Default per-Tier-1-set gas budget in USD. */
  defaultTier1BudgetUSD: number;
}

export const CHAIN_DEPLOY_CONFIG: Record<string, ChainDeployConfig> = {
  "base-sepolia": {
    networkKey: "base-sepolia",
    chainId: 84532,
    isMainnet: false,
    rpcUrl: "https://sepolia.base.org",
    verifierUrl: "https://api-sepolia.basescan.org/api",
    defaultGasBudgetUSD: 1,
    defaultTier1BudgetUSD: 5,
  },
  base: {
    networkKey: "base",
    chainId: 8453,
    isMainnet: true,
    rpcUrl: "https://mainnet.base.org",
    verifierUrl: "https://api.basescan.org/api",
    defaultGasBudgetUSD: 5,
    defaultTier1BudgetUSD: 50,
  },
  sepolia: {
    networkKey: "sepolia",
    chainId: 11155111,
    isMainnet: false,
    rpcUrl: "https://eth-sepolia.public.blastapi.io",
    verifierUrl: "https://api-sepolia.etherscan.io/api",
    defaultGasBudgetUSD: 5,
    defaultTier1BudgetUSD: 25,
  },
  ethereum: {
    networkKey: "ethereum",
    chainId: 1,
    isMainnet: true,
    rpcUrl: "https://eth.public-rpc.com",
    verifierUrl: "https://api.etherscan.io/api",
    defaultGasBudgetUSD: 200,
    defaultTier1BudgetUSD: 800,
  },
  "0g-galileo": {
    networkKey: "0g-galileo",
    chainId: 16601,
    isMainnet: false,
    rpcUrl: "https://evmrpc-testnet.0g.ai",
    defaultGasBudgetUSD: 0.1,
    defaultTier1BudgetUSD: 0.5,
  },
  "0g-mainnet": {
    networkKey: "0g-mainnet",
    chainId: 16600,
    isMainnet: true,
    rpcUrl: "https://evmrpc.0g.ai",
    defaultGasBudgetUSD: 1,
    defaultTier1BudgetUSD: 10,
  },
};

/**
 * Read a deploy config by network key. Throws on unknown network.
 */
export function configFor(networkKey: string): ChainDeployConfig {
  const c = CHAIN_DEPLOY_CONFIG[networkKey];
  if (!c) {
    throw new Error(
      `No deploy config for '${networkKey}'. Known: ${Object.keys(CHAIN_DEPLOY_CONFIG).join(", ")}.`,
    );
  }
  return c;
}

/**
 * Resolve the active RPC URL: env override → catalog default.
 *
 * Env-var convention: MINDX_DEPLOY_RPC_<NETWORK_KEY_UPPER_UNDERSCORE>
 * e.g. MINDX_DEPLOY_RPC_BASE_SEPOLIA="https://...".
 */
export function activeRpcUrl(networkKey: string): string {
  const envKey = `MINDX_DEPLOY_RPC_${networkKey.replace(/[-]/g, "_").toUpperCase()}`;
  const fromEnv = typeof process !== "undefined" ? process.env?.[envKey] : undefined;
  return fromEnv || configFor(networkKey).rpcUrl;
}
