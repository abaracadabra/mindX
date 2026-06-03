// SPDX-License-Identifier: Apache-2.0
//
// bankonchains/chains.js — the CANONICAL BANKON chain registry (USDC + CCTP + RPC +
// explorer). The old packages/web/chains.js re-exports this for backward compat.
// The set is EXTENSIBLE to any EVM chain at runtime via extend.js (chainid.network),
// mirroring agenticplace.pythai.net/allchain.html. Price data + the CoinMarketCap API
// key live in this folder too (price.js + cmc-proxy.*, key kept server-side).
export const CHAINS = {
  1:        { key: "ethereum",      name: "Ethereum",            nativeSymbol: "ETH",  usdc: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", cctpDomain: 0,    rpc: "https://ethereum-rpc.publicnode.com",      explorer: "https://etherscan.io" },
  8453:     { key: "base",          name: "Base",                nativeSymbol: "ETH",  usdc: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", cctpDomain: 6,    rpc: "https://base-rpc.publicnode.com",          explorer: "https://basescan.org" },
  1284:     { key: "moonbeam",      name: "Moonbeam (GLMR)",     nativeSymbol: "GLMR", usdc: null,                                           cctpDomain: null, rpc: "https://moonbeam-rpc.publicnode.com",      explorer: "https://moonscan.io" },
  137:      { key: "polygon",       name: "Polygon",             nativeSymbol: "POL",  usdc: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", cctpDomain: 7,    rpc: "https://polygon-bor-rpc.publicnode.com",   explorer: "https://polygonscan.com" },
  42161:    { key: "arbitrum",      name: "Arbitrum One",        nativeSymbol: "ETH",  usdc: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", cctpDomain: 3,    rpc: "https://arbitrum-one-rpc.publicnode.com",  explorer: "https://arbiscan.io" },
  10:       { key: "optimism",      name: "OP Mainnet",          nativeSymbol: "ETH",  usdc: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", cctpDomain: 2,    rpc: "https://optimism-rpc.publicnode.com",      explorer: "https://optimistic.etherscan.io" },
  43114:    { key: "avalanche",     name: "Avalanche C-Chain",   nativeSymbol: "AVAX", usdc: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", cctpDomain: 1,    rpc: "https://avalanche-c-chain-rpc.publicnode.com", explorer: "https://snowtrace.io" },
  56:       { key: "bnb",           name: "BNB Smart Chain",     nativeSymbol: "BNB",  usdc: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", cctpDomain: null, rpc: "https://bsc-rpc.publicnode.com",           explorer: "https://bscscan.com" }, // Binance-Peg USDC (18dp)
  81457:    { key: "blast",         name: "Blast",               nativeSymbol: "ETH",  usdc: null,                                           cctpDomain: null, rpc: "https://blast-rpc.publicnode.com",         explorer: "https://blastscan.io" }, // native stable USDB 0x4300…0003
  1776:     { key: "injective-evm", name: "Injective EVM",       nativeSymbol: "INJ",  usdc: null,                                           cctpDomain: null, rpc: "https://sentry.evm-rpc.injective.network", explorer: "https://blockscout.injective.network" },
  5042002:  { key: "arc",           name: "Arc (Circle)",        nativeSymbol: "USDC", nativeIsUsdc: true, usdc: "0x3600000000000000000000000000000000000000", cctpDomain: 26, rpc: "https://rpc.testnet.arc.network", explorer: "https://testnet.arcscan.app", faucet: "https://faucet.circle.com", testnet: true },
  16661:    { key: "0g-aristotle",  name: "0G Aristotle Mainnet", nativeSymbol: "0G",   usdc: null,                                           cctpDomain: null, rpc: "https://evmrpc.0g.ai",                     explorer: "https://chainscan.0g.ai" },
  16601:    { key: "0g-galileo",    name: "0G Galileo Testnet",  nativeSymbol: "0G",   usdc: null,                                           cctpDomain: null, rpc: "https://evmrpc-testnet.0g.ai",             explorer: "https://chainscan-galileo.0g.ai", testnet: true },
  11155111: { key: "sepolia",       name: "Sepolia",             nativeSymbol: "ETH",  usdc: "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238", cctpDomain: 0,    rpc: "https://ethereum-sepolia-rpc.publicnode.com", explorer: "https://sepolia.etherscan.io", faucet: "https://sepoliafaucet.com", testnet: true },
  84532:    { key: "base-sepolia",  name: "Base Sepolia",        nativeSymbol: "ETH",  usdc: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", cctpDomain: 6,    rpc: "https://base-sepolia-rpc.publicnode.com",  explorer: "https://sepolia.basescan.org", faucet: "https://www.alchemy.com/faucets/base-sepolia", testnet: true },
};

export const SETTLEMENT_CHAIN_ID = 1; // where the bankon registrar/router settle

export function usdcFor(chainId) { return CHAINS[chainId]?.usdc || null; }
export function chainName(chainId) { return CHAINS[chainId]?.name || `chain ${chainId}`; }

// Standard ERC-20 (USDC) minimal ABI for balances/transfers/approve.
export const ERC20_ABI = [
  { type: "function", name: "balanceOf", stateMutability: "view", inputs: [{ name: "a", type: "address" }], outputs: [{ name: "", type: "uint256" }] },
  { type: "function", name: "decimals", stateMutability: "view", inputs: [], outputs: [{ name: "", type: "uint8" }] },
  { type: "function", name: "transfer", stateMutability: "nonpayable", inputs: [{ name: "to", type: "address" }, { name: "v", type: "uint256" }], outputs: [{ name: "", type: "bool" }] },
  { type: "function", name: "approve", stateMutability: "nonpayable", inputs: [{ name: "s", type: "address" }, { name: "v", type: "uint256" }], outputs: [{ name: "", type: "bool" }] },
];
