// SPDX-License-Identifier: Apache-2.0
//
// cmc-proxy.mjs — server-side CoinMarketCap price proxy. Keeps the CMC API key SERVER-SIDE
// (env CMC_API_KEY, never shipped to the browser) and serves prices ONLY to a verified
// *.bankon.eth / bankon.eth holder (per the privilege model in bankon.js). Public visitors
// use the keyless path in price.js and never reach this.
//
// CMC best practices applied:
//   • key in the X-CMC_PRO_API_KEY header (not the query string)
//   • base https://pro-api.coinmarketcap.com, /v1/cryptocurrency/quotes/latest
//   • BATCH every needed symbol in one call + cache ≥ TTL (respects Basic: 30/min, 10k/mo)
//   • convert=USD only (Basic allows 1 conversion/request); 429 → serve stale cache
//
// Run:  CMC_API_KEY=<key> node packages/web/bankonchains/cmc-proxy.mjs   # :8799
// The key lives in bankonchains/.env (gitignored). NEVER commit it.
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { ethers } from "../vendor/ethers.min.js";
import { CHAINS } from "./chains.js";

// Load the CMC key SERVER-SIDE from OUTSIDE the web root (so a static host can never serve it):
// process env first, then $CMC_ENV_FILE, then the bankoneth-root .bankonchains.env (gitignored).
function loadEnv() {
  if (process.env.CMC_API_KEY) return;
  const file = process.env.CMC_ENV_FILE
    ? new URL("file://" + process.env.CMC_ENV_FILE)
    : new URL("../../../.bankonchains.env", import.meta.url); // bankonchains → web → packages → bankoneth/
  try {
    for (const line of readFileSync(file, "utf8").split("\n")) {
      const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2];
    }
  } catch {}
}
loadEnv();

const KEY = process.env.CMC_API_KEY || "";
const PORT = Number(process.env.CMC_PROXY_PORT || 8799);
const TTL = 120_000;                              // cache window (ms)
const MAX_AGE = 300;                              // holder-proof freshness (s)
const SYMBOLS = (process.env.CMC_SYMBOLS || "ETH,POL,GLMR,INJ,USDC,USDT").split(",");
const ALLOWLIST = new Set((process.env.CMC_HOLDERS || "").toLowerCase().split(",").filter(Boolean));

const L1 = () => new ethers.JsonRpcProvider(CHAINS[1].rpc);
let _cache = { t: 0, data: {} };

async function isHolder(address) {
  if (ALLOWLIST.has(address.toLowerCase())) return true;        // operator allowlist (optional)
  try {
    const p = L1();
    const [owner, name] = await Promise.all([
      p.resolveName("bankon.eth").catch(() => null),
      p.lookupAddress(address).catch(() => null),
    ]);
    if (owner && owner.toLowerCase() === address.toLowerCase()) return true;
    if (name && /\.bankon\.eth$/i.test(name)) return true;
  } catch {}
  return false;
}

// One batched CMC call for all SYMBOLS, cached. Returns { SYM: usd }.
async function quotes() {
  if (Date.now() - _cache.t < TTL && Object.keys(_cache.data).length) return _cache.data;
  const url = `https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=${SYMBOLS.join(",")}&convert=USD`;
  const r = await fetch(url, { headers: { "X-CMC_PRO_API_KEY": KEY, "Accept": "application/json", "Accept-Encoding": "gzip" } });
  if (r.status === 429) return _cache.data;                     // rate-limited → serve stale
  if (!r.ok) throw new Error("cmc " + r.status);
  const j = await r.json();
  const out = {};
  for (const s of SYMBOLS) { const q = j?.data?.[s]; if (q?.quote?.USD?.price != null) out[s] = q.quote.USD.price; }
  _cache = { t: Date.now(), data: out };
  return out;
}

const json = (res, code, obj) => { res.writeHead(code, { "content-type": "application/json", "access-control-allow-origin": "*", "access-control-allow-headers": "content-type" }); res.end(JSON.stringify(obj)); };

createServer(async (req, res) => {
  if (req.method === "OPTIONS") return json(res, 204, {});
  if (!KEY) return json(res, 503, { error: "CMC_API_KEY not configured" });
  const u = new URL(req.url, "http://x");
  const symbol = (u.searchParams.get("symbol") || "ETH").toUpperCase();
  let body = ""; for await (const c of req) body += c;
  let proof = {}; try { proof = JSON.parse(body || "{}"); } catch {}

  // verify the holder proof: signature recovers to `address`, fresh, and holder on-chain.
  try {
    const { address, ts, sig } = proof;
    if (!address || !ts || !sig) return json(res, 401, { error: "holder proof required" });
    if (Math.abs(Math.floor(Date.now() / 1000) - Number(ts)) > MAX_AGE) return json(res, 401, { error: "proof expired" });
    const recovered = ethers.verifyMessage(`BANKON holder proof ${ts}`, sig);
    if (recovered.toLowerCase() !== String(address).toLowerCase()) return json(res, 401, { error: "bad signature" });
    if (!(await isHolder(recovered))) return json(res, 403, { error: "not a bankon.eth holder" });
  } catch (e) { return json(res, 401, { error: "proof verification failed" }); }

  try { const q = await quotes(); return json(res, 200, { symbol, usd: q[symbol] ?? null, source: "coinmarketcap", cachedAt: _cache.t }); }
  catch (e) { return json(res, 502, { error: String(e.message || e) }); }
}).listen(PORT, () => console.log(`cmc-proxy on :${PORT} (holder-gated, key ${KEY ? "loaded" : "MISSING"})`));
