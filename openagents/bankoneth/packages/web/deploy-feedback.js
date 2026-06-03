// SPDX-License-Identifier: Apache-2.0
//
// deploy-feedback.js — "return from blockchain". Keyless-first: explorer links,
// receipts, confirmation counts and native cost come from public RPC + chains.js,
// no API key. USD value is best-effort (chainmarketcap local feed or a public
// price, falls back to native). Source-verification is an OPTIONAL toggle:
// keyless Blockscout where present, Etherscan V2 if a key is in localStorage.
import { ethers } from "./vendor/ethers.min.js";
import { CHAINS } from "./chains.js";

export const Feedback = {
  // explorer URLs (keyless)
  addressUrl(chainId, addr) { const e = CHAINS[chainId]?.explorer; return e ? `${e}/address/${addr}` : null; },
  txUrl(chainId, hash) { const e = CHAINS[chainId]?.explorer; return e ? `${e}/tx/${hash}` : null; },
  explorerHost(chainId) { try { return new URL(CHAINS[chainId].explorer).hostname; } catch { return "explorer"; } },

  // Poll confirmations for a tx via public RPC (no wallet, no key).
  async confirmations(chainId, hash) {
    try {
      const p = new ethers.JsonRpcProvider(CHAINS[chainId].rpc);
      const [rcpt, head] = await Promise.all([p.getTransactionReceipt(hash), p.getBlockNumber()]);
      if (!rcpt) return 0;
      return Math.max(0, head - rcpt.blockNumber + 1);
    } catch { return 0; }
  },

  // Best-effort native→USD. Tries the local chainmarketcap feed, else a keyless
  // public price, else null (UI shows native only — never blocks).
  async nativeUsd(chainId) {
    const sym = CHAINS[chainId]?.nativeSymbol || "ETH";
    if (CHAINS[chainId]?.nativeIsUsdc) return 1;
    // 1) local chainmarketcap feed if served alongside
    try {
      const r = await fetch(`/chainmarketcap/price/${sym}`, { signal: AbortSignal.timeout(2500) });
      if (r.ok) { const j = await r.json(); if (j?.usd) return Number(j.usd); }
    } catch {}
    // 2) keyless public spot (Coinbase) — degrade silently if offline
    try {
      const r = await fetch(`https://api.coinbase.com/v2/prices/${sym}-USD/spot`, { signal: AbortSignal.timeout(2500) });
      if (r.ok) { const j = await r.json(); const v = Number(j?.data?.amount); if (v) return v; }
    } catch {}
    return null;
  },

  fmtCost(weiBig, usd) {
    const eth = Number(ethers.formatEther(weiBig));
    const native = `${eth.toFixed(6)} `;
    return usd != null ? `${native}(~$${(eth * usd).toFixed(2)})` : native;
  },

  // OPTIONAL source-verification. Keyless Blockscout if the explorer is Blockscout-
  // family; Etherscan V2 multichain if localStorage has an "etherscan_key". Returns
  // { ok|skipped, url, reason } and NEVER throws — verification never blocks a deploy.
  async verify(chainId, address, name) {
    const explorer = CHAINS[chainId]?.explorer;
    const key = (typeof localStorage !== "undefined" && localStorage.getItem("etherscan_key")) || null;
    const etherscanFamily = /etherscan|basescan|arbiscan|polygonscan/.test(explorer || "");
    if (etherscanFamily && key) {
      // Etherscan V2 multichain accepts ?chainid= — full standard-json verify needs the
      // build input; we surface the prefilled verify URL and attempt the API if input is staged.
      return { skipped: true, url: `${explorer}/address/${address}#code`, reason: "Etherscan V2 key present — submit standard-json via the verify page (input not bundled at runtime)." };
    }
    if (/blockscout|arcscan|chainscan/.test(explorer || "")) {
      return { skipped: true, url: `${explorer}/address/${address}/contract-verification`, reason: "Keyless Blockscout — open the verification page (no key needed)." };
    }
    return { skipped: true, url: `${explorer}/address/${address}#code`, reason: "Verify on the explorer (optional)." };
  },
};

// ── gas-as-a-service helper: read the φ/priority fee + issue/drop on Base ───────
export const GasService = {
  ABI: [
    { type: "function", name: "quote_drop", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
    { type: "function", name: "quote_fee", stateMutability: "pure", inputs: [{ type: "uint256" }, { type: "uint256" }], outputs: [{ type: "uint256" }] },
    { type: "function", name: "quote_fee_priority", stateMutability: "pure", inputs: [{ type: "uint256" }, { type: "uint256" }, { type: "uint256" }], outputs: [{ type: "uint256" }] },
    { type: "function", name: "tier_mult", stateMutability: "pure", inputs: [{ type: "uint256" }], outputs: [{ type: "uint256" }] },
    { type: "function", name: "buy_gas", stateMutability: "payable", inputs: [{ type: "address" }, { type: "uint256" }, { type: "uint256" }], outputs: [{ type: "uint256" }] },
    { type: "function", name: "buy_gas_priority", stateMutability: "payable", inputs: [{ type: "address" }, { type: "uint256" }, { type: "uint256" }, { type: "uint256" }], outputs: [{ type: "uint256" }] },
    { type: "function", name: "allocate_gas", stateMutability: "nonpayable", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
  ],
  // Tier labels for the expedited UI (golden φ-stepped, capped at 3× cost).
  TIERS: [
    { tier: 0, label: "Normalized", note: "golden base φ/10 (16.18%)" },
    { tier: 2, label: "Fast", note: "≈ 42% (φ³/10)" },
    { tier: 4, label: "Express", note: "≈ 111% (φ⁵/10)" },
    { tier: 6, label: "Instant", note: "→ capped at 3× cost" },
  ],
  contract(addr, signerOrProvider) { return new ethers.Contract(addr, this.ABI, signerOrProvider); },

  // Buy `gasWei` of gas for `to`, at expedited golden tier (0 = normalized).
  async buy(addr, signer, to, gasWei, sides, tier = 0) {
    const c = this.contract(addr, signer);
    if (tier === 0) {
      const fee = await c.quote_fee(gasWei, sides);
      return c.buy_gas(to, gasWei, sides, { value: gasWei + fee });
    }
    const mult = await c.tier_mult(tier);
    const fee = await c.quote_fee_priority(gasWei, sides, mult);
    return c.buy_gas_priority(to, gasWei, sides, mult, { value: gasWei + fee });
  },
};
