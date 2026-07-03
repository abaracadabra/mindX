# bankonchains

The canonical **chain registry + price layer** for the BANKON dApp.

## Files
| File | Role |
|---|---|
| `chains.js` | Canonical curated registry (ETH, Base, Moonbeam/GLMR, Polygon/POL, Arbitrum/ARB, Optimism/OP, Blast, Injective EVM/INJ, 0G, Arc/Circle + testnets). `../chains.js` re-exports it. |
| `extend.js` | **Extensibility** — `addChainById(id)` resolves *any* EVM chain from `chainid.network/chains.json` (the same source as `agenticplace.pythai.net/allchain.html`); `cfg(id)` returns curated-or-extended; `UNISWAP_CHAIN_IDS`. |
| `price.js` | Native→USD. **Public:** keyless spot (Coinbase). **Holder:** CoinMarketCap via the proxy. TTL-cached. |
| `cmc-proxy.mjs` / `cmc-proxy.php` | Server-side CMC proxy — holds the API key, gates to holders. |
| `.env.sample` → `.env` | CMC key config (`.env` is **gitignored**). |

## Price privilege model
- **Public** (`index.html` + wallet connect): keyless spot prices, public dApp surface.
- **Holder** (owns `bankon.eth` or a `*.bankon.eth` subname): **CoinMarketCap** prices. `bankon.js`
  determines holder status (ENS owner / reverse-record) and signs a freshness-bounded **holder proof**;
  the proxy verifies the signature + re-checks holder status on-chain before returning CMC data.

## CoinMarketCap API key handling (proper, per CMC best practices)
- **Server-side only, OUTSIDE the web root.** A static host serves *every* file under `packages/web/`,
  so the real key must NOT live there. It lives in the bankoneth-root **`.bankonchains.env`** (gitignored,
  not web-served) or as an environment variable; the proxies load it via `loadEnv()` (`$CMC_ENV_FILE` →
  `../../../.bankonchains.env`). `.env.sample` here is only a template; `.htaccess` blocks any stray secret.
- **Header auth:** the proxy sends `X-CMC_PRO_API_KEY` (not a query param), base
  `https://pro-api.coinmarketcap.com`, endpoint `/v1/cryptocurrency/quotes/latest?symbol=…&convert=USD`.
- **Credit-frugal** for the Basic plan (30 req/min, 10k/month): all needed symbols are **batched into one
  call** and **cached ≥120s**; on HTTP 429 the proxy serves the stale cache.
- **Public default stays keyless** — the dApp works with no key at all; CMC is the holder upgrade.

## Run the proxy
```bash
cp bankonchains/.env.sample bankonchains/.env   # then set CMC_API_KEY
node packages/web/bankonchains/cmc-proxy.mjs     # :8799  (holder-gated, on-chain verified)
# or PHP host: point /cmc → cmc-proxy.php (allowlist-gated; see file header)
```
Point the dApp at it via `localStorage["bankon.cmc_proxy"] = "http://localhost:8799"` (default `/cmc`).

## Extending chains
`addChainById(7777777)` (or any id) pulls RPC + explorer from `chainid.network` and merges it into the
runtime overlay — the deployer's chain picker and the dApp then treat it like any curated chain.
