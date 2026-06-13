// SPDX-License-Identifier: Apache-2.0
//
// Canonical ENS contract address registry, pinned per chain.
//
// Sourced from ensdomains/ens-contracts deployments + docs.ens.domains:
//   https://docs.ens.domains/learn/deployments
//   https://github.com/ensdomains/ens-contracts/tree/staging/deployments
//
// The bankoneth deploy script (script/DeployEthereum.s.sol) has an internal
// `_verifyChainAddresses` guard that asserts NAME_WRAPPER + ETH_REGISTRAR
// match the mainnet pair below before broadcasting. Sepolia overrides are
// available via `ALLOW_TESTNET=true`. See docs/SEPOLIA_REHEARSAL.md.

import type { Address } from "viem";

/** ENS contracts deployed per chain. Augment when bankoneth lands on a new L2. */
export interface EnsAddresses {
  /** ENS Registry (V2). The root registry mapping namehash → resolver+owner. */
  registry:               Address;
  /** Wrapping registrar. ERC-1155 + fuses for wrapped names. */
  nameWrapper:            Address;
  /** Latest ETHRegistrarController. Commit-reveal for `.eth` 2LDs. */
  ethRegistrarController: Address;
  /** Default PublicResolver — latest revision. */
  publicResolver:         Address;
  /** ReverseRegistrar — primary-name setup for EOAs + contracts (ENSIP-15). */
  reverseRegistrar:       Address;
  /**
   * Universal Resolver (ENSv2-forward-compatible, ENS-DAO-upgradable proxy).
   * Bundles addr / text / contenthash / multichain into a single `resolve()`
   * call and follows CCIP-Read offchain resolvers automatically.
   */
  universalResolver:      Address;
  /** BulkRenewal — batch-renew multiple `.eth` 2LDs in one transaction. */
  bulkRenewal:            Address;
  /** BaseRegistrarImplementation — owns the .eth tree, called by the controller. */
  baseRegistrar:          Address;
}

// ── Mainnet (chainId 1) ──────────────────────────────────────────────

export const MAINNET: EnsAddresses = {
  registry:               "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",
  nameWrapper:            "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401",
  ethRegistrarController: "0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547",
  publicResolver:         "0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63",
  reverseRegistrar:       "0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb",
  universalResolver:      "0xeEeEEEeE14D718C2B47D9923Deab1335E144EeEe",
  bulkRenewal:            "0xa12159e5131b1eEf6B4857EEE3e1954744b5033A",
  baseRegistrar:          "0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85",
};

// ── Sepolia (chainId 11_155_111) ─────────────────────────────────────

export const SEPOLIA: EnsAddresses = {
  registry:               "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",
  nameWrapper:            "0x0635513f179D50A207757E05759CbD106d7dFcE8",
  ethRegistrarController: "0xfb3cE5D01e0f33f41DbB39035dB9745962F1f968",
  publicResolver:         "0x8FADE66B79cC9f707aB26799354482EB93a5B7dD",
  reverseRegistrar:       "0xA0a1AbcDAe1a2a4A2EF8e9113Ff0e02DD81DC0C6",
  universalResolver:      "0xeEeEEEeE14D718C2B47D9923Deab1335E144EeEe",
  bulkRenewal:            "0x4EF77b90762Eddb33C8Eba5B5a19558DaE53D7a1",
  baseRegistrar:          "0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85",
};

// ── Registry by chainId ──────────────────────────────────────────────

export const ENS_BY_CHAIN: Record<number, EnsAddresses> = {
  1:          MAINNET,
  11_155_111: SEPOLIA,
};

/** Lookup the canonical addresses for a chain. Throws if unknown. */
export function ensAddressesFor(chainId: number): EnsAddresses {
  const a = ENS_BY_CHAIN[chainId];
  if (!a) {
    throw new Error(
      `[bankoneth] No canonical ENS addresses pinned for chainId ${chainId}. ` +
      `Add an entry to packages/core/src/addresses.ts.`
    );
  }
  return a;
}

/** Sentinel — sentinel-equal in checks against zero-init storage. */
export const ZERO_ADDR: Address = "0x0000000000000000000000000000000000000000";

// ── USDC + CCTP per chain (payment conversion layer; see packages/web/chains.js) ──
// ARC (Circle's USDC-gas chain) from the use-arc skill: chain 5042002, USDC is
// the native gas token, CCTP domain 26. Used to accept any-denomination payment
// and bridge → settlement-chain USDC → x402.
export interface UsdcChain {
  usdc: Address;
  cctpDomain: number;
  nativeIsUsdc?: boolean;
  testnet?: boolean;
}

export const USDC_BY_CHAIN: Record<number, UsdcChain> = {
  1:       { usdc: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", cctpDomain: 0 },
  8453:    { usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", cctpDomain: 6 },
  42161:   { usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", cctpDomain: 3 },
  137:     { usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", cctpDomain: 7 },
  5042002: { usdc: "0x3600000000000000000000000000000000000000", cctpDomain: 26, nativeIsUsdc: true, testnet: true }, // Arc testnet
};
