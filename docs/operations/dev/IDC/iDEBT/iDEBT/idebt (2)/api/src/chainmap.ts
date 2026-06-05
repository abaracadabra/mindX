/**
 * Canonical chain table mirroring `src/libraries/ChainMapping.sol` and
 * `agenticplace.pythai.net/allchain.html`.
 *
 * Keep this file in 1:1 sync with the Solidity library — the on-chain table
 * is authoritative.
 */

export type ChainFamily = "EVM" | "ALGORAND" | "COSMOS" | "SOLANA" | "SUI";

export interface ChainRecord {
  chainId:      number;
  family:       ChainFamily;
  name:         string;
  nativeGas:    string;
  stableAnchor: string;
  rpcHint:      string;
}

// ---- EVM ----
export const ETHEREUM         = 1;
export const OPTIMISM         = 10;
export const BSC              = 56;
export const POLYGON          = 137;
export const FANTOM           = 250;
export const ZKSYNC_ERA       = 324;
export const POLYGON_ZKEVM    = 1101;
export const BASE             = 8453;
export const ARBITRUM_ONE     = 42_161;
export const AVALANCHE_C      = 43_114;
export const SEPOLIA          = 11_155_111;
export const ARC              = 5_042_002;

// ---- Non-EVM sentinels ----
export const ALGORAND_MAINNET = 4_160_001;
export const ALGORAND_TESTNET = 4_160_002;
export const SOLANA_MAINNET   = 5_001_001;
export const COSMOS_HUB       = 6_001_001;
export const SUI_MAINNET      = 7_001_001;

export const CHAINS: ReadonlyArray<ChainRecord> = [
  { chainId: ETHEREUM,         family: "EVM",      name: "Ethereum",         nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://eth.llamarpc.com" },
  { chainId: OPTIMISM,         family: "EVM",      name: "Optimism",         nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://mainnet.optimism.io" },
  { chainId: POLYGON,          family: "EVM",      name: "Polygon PoS",      nativeGas: "MATIC",stableAnchor: "USDC",  rpcHint: "https://polygon-rpc.com" },
  { chainId: POLYGON_ZKEVM,    family: "EVM",      name: "Polygon zkEVM",    nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://zkevm-rpc.com" },
  { chainId: ARBITRUM_ONE,     family: "EVM",      name: "Arbitrum One",     nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://arb1.arbitrum.io/rpc" },
  { chainId: BASE,             family: "EVM",      name: "Base",             nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://mainnet.base.org" },
  { chainId: BSC,              family: "EVM",      name: "BNB Smart Chain",  nativeGas: "BNB",  stableAnchor: "USDT",  rpcHint: "https://bsc-dataseed.binance.org" },
  { chainId: AVALANCHE_C,      family: "EVM",      name: "Avalanche C",      nativeGas: "AVAX", stableAnchor: "USDC",  rpcHint: "https://api.avax.network/ext/bc/C/rpc" },
  { chainId: ZKSYNC_ERA,       family: "EVM",      name: "zkSync Era",       nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://mainnet.era.zksync.io" },
  { chainId: FANTOM,           family: "EVM",      name: "Fantom",           nativeGas: "FTM",  stableAnchor: "USDC",  rpcHint: "https://rpc.ftm.tools" },
  { chainId: ARC,              family: "EVM",      name: "Arc Network",      nativeGas: "USDC", stableAnchor: "USDC",  rpcHint: "https://rpc.arc.network" },
  { chainId: SEPOLIA,          family: "EVM",      name: "Sepolia",          nativeGas: "ETH",  stableAnchor: "USDC",  rpcHint: "https://rpc.sepolia.org" },
  { chainId: ALGORAND_MAINNET, family: "ALGORAND", name: "Algorand Mainnet", nativeGas: "ALGO", stableAnchor: "USDCa", rpcHint: "https://mainnet-api.algonode.cloud" },
  { chainId: ALGORAND_TESTNET, family: "ALGORAND", name: "Algorand Testnet", nativeGas: "ALGO", stableAnchor: "USDCa", rpcHint: "https://testnet-api.algonode.cloud" },
  { chainId: SOLANA_MAINNET,   family: "SOLANA",   name: "Solana",           nativeGas: "SOL",  stableAnchor: "USDC",  rpcHint: "https://api.mainnet-beta.solana.com" },
  { chainId: COSMOS_HUB,       family: "COSMOS",   name: "Cosmos Hub",       nativeGas: "ATOM", stableAnchor: "USDC",  rpcHint: "https://rpc-cosmoshub.blockapsis.com" },
  { chainId: SUI_MAINNET,      family: "SUI",      name: "Sui",              nativeGas: "SUI",  stableAnchor: "USDC",  rpcHint: "https://fullnode.mainnet.sui.io:443" }
];

const byId = new Map<number, ChainRecord>(CHAINS.map(c => [c.chainId, c]));

export function chainOf(id: number): ChainRecord | undefined { return byId.get(id); }
export function isEvm(id: number): boolean { return chainOf(id)?.family === "EVM"; }
export function isKnown(id: number): boolean { return byId.has(id); }
