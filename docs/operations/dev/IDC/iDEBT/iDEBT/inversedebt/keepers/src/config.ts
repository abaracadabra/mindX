/**
 * DELTAVERSE Keeper Configuration
 *
 * Shared configuration module imported by all four keeper bots. Loads
 * environment variables, validates them, and constructs the viem clients
 * that every keeper uses to talk to the blockchain.
 *
 * This file is intentionally the only place where `process.env` is read,
 * so that swapping environments (mainnet/testnet/local) only requires
 * changing the .env file, not touching any keeper logic.
 */

import { createPublicClient, createWalletClient, http, type Address, type Chain } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { mainnet, polygon, arbitrum, base } from 'viem/chains';
import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Resolve a viem Chain object by chain ID. Add new chains here as the
 * protocol expands. The DELTAVERSE stack is deployed across EVM chains
 * and this function is the single source of truth for which ones are
 * supported.
 */
function getChain(chainId: number): Chain {
  switch (chainId) {
    case 1:     return mainnet;
    case 137:   return polygon;
    case 42161: return arbitrum;
    case 8453:  return base;
    default:    throw new Error(`Unsupported chain ID: ${chainId}`);
  }
}

/**
 * Helper that reads a required environment variable and throws a clear
 * error if it is missing. Without this, a missing RPC URL silently
 * becomes `undefined` and causes mysterious failures later.
 */
function required(key: string): string {
  const value = process.env[key];
  if (!value) throw new Error(`Missing required env var: ${key}`);
  return value;
}

/**
 * Parse the contract address map that the keeper needs. This comes from
 * the same allchain.json convention used by the frontend, but the keeper
 * reads it directly from environment variables for operational simplicity
 * (no filesystem dependency in a container).
 */
export const contracts = {
  rwa:      required('RWA_ADDRESS')      as Address,
  oracle:   required('ORACLE_ADDRESS')   as Address,
  vault:    required('VAULT_ADDRESS')    as Address,
  perp:     required('PERP_ADDRESS')     as Address,
  protocol: required('PROTOCOL_ADDRESS') as Address,
  pyth:     required('PYTH_ADDRESS')     as Address,
  stablecoin: required('STABLECOIN_ADDRESS') as Address,
};

/**
 * The Pyth feed IDs map each of our oracle's sub-indices to the
 * corresponding Pyth price feed. Pyth feed IDs are 32-byte hex strings
 * that identify a specific price feed on the Pyth network. Setting
 * these to actual values is part of the post-deployment wiring — they
 * may be placeholder until the governance team chooses which Pyth
 * feeds best proxy each sub-index (e.g., US 10Y Treasury yield as
 * the YSI proxy).
 */
export const pythFeedIds: Record<string, `0x${string}`> = {
  SDR: (process.env.PYTH_FEED_SDR || '0x0') as `0x${string}`,
  YSI: (process.env.PYTH_FEED_YSI || '0x0') as `0x${string}`,
  CSI: (process.env.PYTH_FEED_CSI || '0x0') as `0x${string}`,
  MDI: (process.env.PYTH_FEED_MDI || '0x0') as `0x${string}`,
  RPI: (process.env.PYTH_FEED_RPI || '0x0') as `0x${string}`,
};

/**
 * The chain configuration. chainId determines which network we connect
 * to and which default block explorer we link events to.
 */
export const chainId = parseInt(required('CHAIN_ID'));
export const chain = getChain(chainId);

/**
 * viem publicClient is the read-only interface. All eth_call, eth_getLogs,
 * and similar read operations go through this client. It is safe to share
 * across keepers and does not require a private key.
 */
export const publicClient = createPublicClient({
  chain,
  transport: http(required('RPC_URL')),
});

/**
 * viem walletClient is the write interface. It signs transactions with
 * the keeper's private key and broadcasts them. Each keeper is expected
 * to have its own dedicated hot wallet with enough native token to pay
 * gas, but not significant assets that would be attractive to an attacker
 * if the key is compromised.
 */
const account = privateKeyToAccount(required('KEEPER_PRIVATE_KEY') as `0x${string}`);

export const walletClient = createWalletClient({
  account,
  chain,
  transport: http(required('RPC_URL')),
});

export const keeperAddress = account.address;

/**
 * Tuning parameters. These control the frequency and thresholds of
 * keeper actions. They are all overridable via environment variables
 * so that different deployments can use different settings without
 * code changes.
 */
export const config = {
  // How often the Pyth updater runs, in milliseconds.
  pythUpdateIntervalMs: parseInt(process.env.PYTH_UPDATE_INTERVAL_MS || '60000'),

  // How often the sub-index finalizer runs, in milliseconds.
  subIndexIntervalMs: parseInt(process.env.SUB_INDEX_INTERVAL_MS || '14400000'), // 4h

  // How often the fee router runs.
  feeRouterIntervalMs: parseInt(process.env.FEE_ROUTER_INTERVAL_MS || '3600000'), // 1h

  // Minimum pending fees (in stablecoin wei) before routing. Below this
  // the gas cost exceeds the routed amount and routing would be a loss.
  feeRouteThreshold: BigInt(process.env.FEE_ROUTE_THRESHOLD || '100000000'), // 100 USDC

  // How often the liquidator scans for underwater positions.
  liquidatorIntervalMs: parseInt(process.env.LIQUIDATOR_INTERVAL_MS || '30000'), // 30s

  // Maximum gas the keeper is willing to pay per transaction.
  maxGasPriceWei: BigInt(process.env.MAX_GAS_PRICE_WEI || '100000000000'), // 100 gwei

  // Log level for the keeper's structured logger.
  logLevel: process.env.LOG_LEVEL || 'info',
};

/**
 * A minimal structured logger. In production this would be replaced with
 * a proper logging library like pino, but for keepers the key requirements
 * are: (1) timestamps, (2) log level, (3) JSON format for log aggregators.
 * This fulfills those minimums without adding dependencies.
 */
export const log = {
  info:  (msg: string, meta?: object) => console.log(JSON.stringify({ ts: new Date().toISOString(), level: 'info',  msg, ...meta })),
  warn:  (msg: string, meta?: object) => console.log(JSON.stringify({ ts: new Date().toISOString(), level: 'warn',  msg, ...meta })),
  error: (msg: string, meta?: object) => console.log(JSON.stringify({ ts: new Date().toISOString(), level: 'error', msg, ...meta })),
};
