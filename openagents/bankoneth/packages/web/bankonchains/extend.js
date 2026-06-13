// SPDX-License-Identifier: Apache-2.0
//
// extend.js — make the BANKON chain set EXTENSIBLE to any EVM chain at runtime,
// mirroring agenticplace.pythai.net/allchain.html: it resolves unknown chain ids from
// chainid.network/chains.json (RPC + explorer + native currency). Curated CHAINS are
// the headline set; anything else is fetched on demand and merged into a runtime overlay.
import { CHAINS } from "./chains.js";

// Chains that host Uniswap V3 (from allchain.html's UNISWAP_CHAIN_IDS) — the auto-convert
// router only works where this is true; elsewhere the deployer leaves the router unset.
export const UNISWAP_CHAIN_IDS = new Set([1, 10, 56, 137, 324, 480, 8453, 42161, 42220, 43114, 81457, 7777777]);

const CDN_URL = "https://chainid.network/chains.json"; // same source allchain.html uses
const EXTRA = {};      // runtime overlay for CDN-resolved chains
let _cdn = null;       // cached full chain list

// cfg(id) — curated config first, then any CDN-resolved overlay.
export function cfg(chainId) { return CHAINS[chainId] || EXTRA[chainId] || null; }
export function allChains() { return { ...EXTRA, ...CHAINS }; }

// Resolve a chain id we don't curate, from the CDN (cached). Returns a CHAINS-shaped entry
// (or null). Merged into the overlay so cfg()/the deployer can use it like any other chain.
export async function addChainById(chainId) {
  const id = Number(chainId);
  if (cfg(id)) return cfg(id);
  if (!_cdn) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 8000);
    _cdn = await fetch(CDN_URL, { signal: ctrl.signal }).then((r) => r.json()).catch(() => []);
    clearTimeout(t);
  }
  const c = (_cdn || []).find((x) => x.chainId === id);
  if (!c) return null;
  const rpc = (c.rpc || []).filter((r) => typeof r === "string" && r.startsWith("https") && !r.includes("${"))[0];
  if (!rpc) return null;
  EXTRA[id] = {
    key: c.shortName || c.name?.toLowerCase().replace(/[\s.\-]/g, "") || `chain-${id}`,
    name: c.name || `Chain ${id}`,
    nativeSymbol: c.nativeCurrency?.symbol || "ETH",
    usdc: null, cctpDomain: null,
    rpc,
    explorer: c.explorers?.[0]?.url || null,
    extended: true, uniswap: UNISWAP_CHAIN_IDS.has(id),
  };
  return EXTRA[id];
}
