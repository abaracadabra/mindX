// SPDX-License-Identifier: Apache-2.0
//
// price.js — native-token USD price for the dApp, with a two-tier model:
//   • PUBLIC (everyone): keyless spot price (Coinbase). No key, no proxy, no privilege.
//   • HOLDER (*.bankon.eth / bankon.eth): CoinMarketCap prices via the cmc-proxy, which
//     holds the CMC API key SERVER-SIDE and only serves a verified holder proof (see
//     bankon.js + cmc-proxy.*). The key is NEVER shipped to the browser.
// Small TTL cache respects the CMC Basic plan (30 req/min, 10k/month).
const TTL = 120_000; // ms
const _cache = new Map();
function cached(k){ const e=_cache.get(k); return e && (Date.now()-e.t)<TTL ? e.v : null; }
function put(k,v){ _cache.set(k,{v,t:Date.now()}); return v; }

// public, keyless — Coinbase spot. Returns a number (USD) or null.
export async function keylessUsd(symbol){
  if (symbol === "USDC" || symbol === "USDT" || symbol === "DAI") return 1;
  const k = "kl:"+symbol; const c = cached(k); if (c!=null) return c;
  try {
    const r = await fetch(`https://api.coinbase.com/v2/prices/${symbol}-USD/spot`, { signal: AbortSignal.timeout(2500) });
    if (r.ok){ const j = await r.json(); const v = Number(j?.data?.amount); if (v) return put(k, v); }
  } catch {}
  return null;
}

// holder-only — CoinMarketCap via the proxy. `proof` = { address, ts, sig } from bankon.js.
// proxyUrl defaults to localStorage("bankon.cmc_proxy") or "/cmc". Returns USD or null.
export async function cmcUsd(symbol, proof, proxyUrl){
  const url = proxyUrl || (typeof localStorage!=="undefined" && localStorage.getItem("bankon.cmc_proxy")) || "/cmc";
  const k = "cmc:"+symbol; const c = cached(k); if (c!=null) return c;
  try {
    const r = await fetch(`${url}?symbol=${encodeURIComponent(symbol)}`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(proof || {}), signal: AbortSignal.timeout(4000),
    });
    if (r.ok){ const j = await r.json(); const v = Number(j?.usd); if (v) return put(k, v); }
  } catch {}
  return null;
}

// Unified: holders (proof present) get CMC, falling back to keyless; public gets keyless.
export async function nativeUsd(symbol, { proof, proxyUrl } = {}){
  if (proof) { const v = await cmcUsd(symbol, proof, proxyUrl); if (v != null) return { usd: v, source: "coinmarketcap" }; }
  const v = await keylessUsd(symbol);
  return { usd: v, source: v != null ? "coinbase" : null };
}
