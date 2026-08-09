# The Definitive DefiLlama API Integration Guide (Free & Pro)

## TL;DR
- DefiLlama exposes **two entirely separate API services**: the free, keyless public API (`https://api.llama.fi`, plus sibling hosts `coins.llama.fi`, `stablecoins.llama.fi`, `yields.llama.fi`, `bridges.llama.fi`) and the paid Pro API (`https://pro-api.llama.fi/{API_KEY}/...`), which unlocks ~38 additional endpoints (unlocks/emissions, token liquidity, treasuries, hacks, raises, derivatives, bridge detail, ETFs, DAT, RWA, equities) plus higher rate limits.
- The API subscription costs **$300/month or $3,000/year** (1,000 requests/minute, 1 million calls/month, then $0.60 per 1,000 additional calls). A **separate, cheaper Pro dashboard plan ($49/mo or $490/yr) does NOT include API access** — a common purchasing mistake. The free public API has a documented soft ceiling of 500 requests/minute.
- For an infrastructure developer: use the free endpoints for TVL, prices (multi-chain `{chain}:{address}` lookups), stablecoins, and DEX/fees overviews; you only need a Pro key for yields/pools at production scale, token unlocks, derivatives volume, bridge transaction-level data, and the analytics databases (hacks/raises/treasuries/emissions).

## Key Findings

### Two APIs, one mental model
DefiLlama's documentation is explicit: "The Free API and Pro API are entirely separate services." Do not mix them.

| Feature | Free API | Pro API |
|---|---|---|
| Base URL | `https://api.llama.fi` (+ `coins.`, `stablecoins.`, `yields.`, `bridges.`) | `https://pro-api.llama.fi/{KEY}` |
| Auth | None | API key in URL path |
| Price | Free | $300/mo or $3,000/yr |
| Rate limit | 500 requests/minute (soft limit) | 1,000 requests/minute, 1M calls/mo |
| Endpoint count | 31 | 38 exclusive + all 31 free (with prefix) |

**Authentication:** the Pro key is inserted between host and path — `https://pro-api.llama.fi/{YOUR_API_KEY}/api/protocols`. There is no header-based auth; the key lives in the URL path. Keys are obtained by signing in at `https://pro.llama.fi/` / subscribing at `https://defillama.com/subscription`. Per the Pro API subscription page (pro.llama.fi), "DefiLlama contributors will have free 3 month access to premium API" (the contributor tier is documented as 1,000 requests/minute, 200k calls/month, priority support).

**Path remapping (important gotcha):** when you upgrade a free call to Pro, the path changes. Free `/stablecoins` becomes Pro `/stablecoins/stablecoins`; free `/pools` becomes Pro `/yields/pools`; free `/protocols` becomes Pro `/api/protocols`; the coins endpoints get a `/coins` prefix. When your Pro key is set, per the docs, "free endpoints will be changed to pro version to bypass rate limits."

### Pricing tiers (from docs.llama.fi/pro-api)
- **Open (Free):** TVL, revenue/fees, prices; LlamaFeed; email + Discord support.
- **Pro ($49/mo or $490/yr, with a free 7-day trial):** LlamaAI conversational analysis (deep research 5 questions/day; 3/day during trial), Pro custom dashboards, CSV downloads, custom columns, LlamaFeed premium insights, and DefiLlama Sheets (Excel/Google Sheets). **The docs state verbatim: "Note: API access is not included in the Pro plan."**
- **API ($300/mo or $3,000/yr):** all Pro features + all API endpoints + higher limits. The docs specify: **1,000 requests per minute, 1 million API calls per month, and $0.60 per 1,000 additional calls after the 1M limit.**
- **Enterprise (contact sales@defillama.com):** the docs list "Direct raw access to our database … Hourly data … Access to non-public data, such as TVL breakdowns by token address … Custom data licensing agreements."

### Official SDKs & source code
- **JavaScript/TypeScript:** `npm install @defillama/api` → `https://github.com/DefiLlama/api-sdk`
- **Python:** `pip install defillama-sdk` → `https://github.com/DefiLlama/python-sdk` (v0.1.4)
- **TVL-adapter SDK** (for *computing* TVL on-chain, not querying the data API): `npm install @defillama/sdk` → `https://github.com/DefiLlama/defillama-sdk`
- Data-source repos: `DefiLlama/DefiLlama-Adapters` (TVL), `DefiLlama/dimension-adapters` (volume/fees/revenue/aggregators/open-interest/active-users), `DefiLlama/yield-server` (yields), `DefiLlama/peggedassets-server` (stablecoins), `DefiLlama/bridges-server` (bridges), `DefiLlama/emissions-adapters` (unlocks), `DefiLlama/defillama-server` (core backend), `DefiLlama/api-docs` (the Scalar-based docs site).
- Official docs: `https://api-docs.defillama.com/` (interactive) and `https://docs.llama.fi/` (methodology + guides). Machine-readable OpenAPI specs are published at `/defillama-openapi-free.json` and `/defillama-openapi-pro.json`, with LLM indexes at `/llms-free.txt` and `/llms-pro.txt`.

---

## Details — Endpoint Reference by Category

Coin identifiers everywhere use the format `{chain}:{address}`, e.g. `ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` (USDC), `solana:So11111111111111111111111111111111111111112`, or `coingecko:ethereum` / `coingecko:bitcoin` for native/non-contract lookups.

### 1. TVL (`https://api.llama.fi`)

| Method/Path | Description |
|---|---|
| `GET /protocols` | All protocols with current TVL + metadata |
| `GET /protocol/{protocol}` | Full historical TVL + token & chain breakdowns for one protocol (slug) |
| `GET /tvl/{protocol}` | Simplified: current TVL number only for a protocol |
| `GET /v2/chains` | Current TVL of all chains |
| `GET /v2/historicalChainTvl` | Historical TVL of all DeFi (excludes liquid staking & double-count) |
| `GET /v2/historicalChainTvl/{chain}` | Historical TVL for one chain |
| `GET /charts/{chain}` | (legacy) historical TVL chart for a chain |

**`/protocols` response (array element):**
```json
{ "id":"2269","name":"Aave","symbol":"AAVE","category":"Lending",
  "chains":["Ethereum","Polygon"],"tvl":5200000000,
  "chainTvls":{"Ethereum":3200000000,"Polygon":2000000000},
  "change_1d":2.1,"change_7d":-5.3,"slug":"aave","gecko_id":"aave" }
```

**`/protocol/{slug}` response** includes `id, name, address, symbol, url, description, chain, logo, audits, gecko_id, cmcId, category, chains, module, twitter, listedAt, methodology, slug, tvl`, and a nested `chainTvls` object where each chain holds `tvl:[{date,totalLiquidityUSD}]` and `tokens:[{date,tokens:{SYMBOL:amount}}]`.

**`/v2/chains` element:** `{"gecko_id":"ethereum","tvl":65998652431.4,"tokenSymbol":"ETH","cmcId":"1027","name":"Ethereum","chainId":1}`

**`/tvl/{slug}`** returns a bare number, e.g. `5200000000`.

**cURL / Python / JS examples:**
```bash
curl https://api.llama.fi/protocols
curl https://api.llama.fi/protocol/aave
curl https://api.llama.fi/tvl/uniswap
curl https://api.llama.fi/v2/historicalChainTvl/Ethereum
```
```python
import requests
tvl = requests.get("https://api.llama.fi/tvl/uniswap").json()
protocols = requests.get("https://api.llama.fi/protocols").json()
top5 = sorted(protocols, key=lambda p: p.get("tvl", 0), reverse=True)[:5]
```
```javascript
import { DefiLlama } from '@defillama/api'
const client = new DefiLlama()
const protocols = await client.tvl.getProtocols()
const aave      = await client.tvl.getProtocol('aave')
const ethHist   = await client.tvl.getHistoricalChainTvl('Ethereum')
```

### 2. Coins & Prices (`https://coins.llama.fi`)

| Method/Path | Description |
|---|---|
| `GET /prices/current/{coins}` | Current prices by `{chain}:{address}` (comma-separated) |
| `GET /prices/historical/{timestamp}/{coins}` | Prices at a UNIX timestamp (`?searchWidth=6h`) |
| `GET /batchHistorical?coins={json}` | Prices for many tokens at many timestamps |
| `GET /chart/{coins}` | Time-series (`?start`/`end`, `span`, `period=24h`, `searchWidth=600`) |
| `GET /percentage/{coins}` | % price change (`?timestamp`, `lookForward`, `period=24h`) |
| `GET /prices/first/{coins}` | Earliest recorded price for coins |
| `GET /block/{chain}/{timestamp}` | Closest block to a timestamp |

**`/prices/current` response:**
```json
{"coins":{"ethereum:0xA0b8...eb48":{"decimals":6,"symbol":"USDC","price":1.0,"timestamp":1700000000,"confidence":0.99}}}
```
The `confidence` field (0–1) reflects price reliability — filter on `>= 0.8` for production. Per DefiLlama's methodology, prices for major tokens are sourced from CoinGecko/CoinMarketCap, while thinly traded tokens are priced from DEX pool data (e.g. Uniswap V2 pool weights).

```bash
curl "https://coins.llama.fi/prices/current/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,coingecko:bitcoin"
curl "https://coins.llama.fi/prices/historical/1704067200/ethereum:0xdac17f958d2ee523a2206206994597c13d831ec7?searchWidth=6h"
```
```python
def get_solana_prices(mints):
    coins = ",".join(f"solana:{m}" for m in mints)
    data = requests.get(f"https://coins.llama.fi/prices/current/{coins}").json()["coins"]
    return {m: data[f"solana:{m}"]["price"] for m in mints if f"solana:{m}" in data}
```

### 3. Stablecoins (`https://stablecoins.llama.fi`)

| Method/Path | Description |
|---|---|
| `GET /stablecoins?includePrices=true` | All stablecoins + circulating amounts |
| `GET /stablecoincharts/all` | Historical mcap sum of all stablecoins |
| `GET /stablecoincharts/{chain}` | Historical mcap on one chain (`?stablecoin={id}`) |
| `GET /stablecoin/{asset}` | Historical mcap + chain distribution for one stablecoin (by numeric id) |
| `GET /stablecoinchains` | Current mcap of all stablecoins per chain |
| `GET /stablecoinprices` | Historical prices of all stablecoins |
| `GET /stablecoins/stablecoindominance/{chain}` | **Pro** — dominance + largest coin per chain |

**`/stablecoins` element:** `{"id":"1","name":"Tether","symbol":"USDT","gecko_id":"tether","pegType":"peggedUSD","priceSource":"defillama","pegMechanism":"fiat-backed","circulating":{...},"chains":["Tron","Ethereum","BSC",...]}`

**`/stablecoincharts/{chain}` element:** `{"date":"1707955200","totalCirculating":{"peggedUSD":88365136},"totalCirculatingUSD":{"peggedUSD":88718597},"totalBridgedToUSD":{"peggedUSD":88718597}}`

Known stablecoin IDs: USDC=`1`, USDT=`2`, PYUSD=`115` (always verify via `/stablecoins`).

### 4. Yields / Pools (`https://yields.llama.fi` free host; Pro paths under `/yields/`)

| Method/Path | Description | Tier |
|---|---|---|
| `GET /pools` | All pools with APY, TVL, predictions | Free host / Pro |
| `GET /chart/{pool}` | Historical APY & TVL for a pool (by UUID) | Free host / Pro |
| `GET /poolsOld` | Pools incl. older pool IDs | Pro |
| `GET /poolsBorrow` | Borrow-side APY data | Pro |
| `GET /chartLendBorrow/{pool}` | Historical lend/borrow rates | Pro |
| `GET /perps` | Perp funding rates | Pro |
| `GET /lsdRates` | Liquid-staking rates | Pro |

> Note: `yields.llama.fi/pools` and `/chart/{pool}` respond on the free host, but DefiLlama's own free/pro matrix classifies yields as a Pro data category. Treat production yields workloads as requiring a Pro key.

**`/pools` response:** `{"status":"success","data":[{...}]}` where each pool has:
```json
{"chain":"Ethereum","project":"aave-v3","symbol":"USDC","tvlUsd":1234567890,
 "apy":4.21,"apyBase":3.81,"apyReward":0.40,"rewardTokens":["0x..."],
 "pool":"0x...-ethereum","stablecoin":true,"ilRisk":"no","apyMean30d":4.1,
 "predictions":{...}}
```
The pool schema (from yield-server) also supports `apyBaseBorrow, apyRewardBorrow, totalSupplyUsd, totalBorrowUsd, ltv, underlyingTokens, poolMeta`. DefiLlama only displays pools with >10k TVL; the main yields page applies a stricter >1M TVL + audited-protocols filter.

```python
data = requests.get("https://yields.llama.fi/pools").json()["data"]
usdc_eth = [p for p in data if p["chain"] == "Ethereum" and p["symbol"] == "USDC"]
```

### 5. Volumes — DEX, Options, Derivatives (`https://api.llama.fi`)

| Method/Path | Description | Tier |
|---|---|---|
| `GET /overview/dexs` | All DEXs + volume summaries | Free |
| `GET /overview/dexs/{chain}` | DEX volumes filtered by chain | Free |
| `GET /summary/dexs/{protocol}` | One DEX's volume + history | Free |
| `GET /overview/options` | Options DEXs volume overview | Free |
| `GET /overview/options/{chain}` | Options volume by chain | Free |
| `GET /summary/options/{protocol}` | One options protocol summary | Free |
| `GET /overview/open-interest` | Open-interest across perp DEXs | Free |
| `GET /overview/derivatives` | Perps/derivatives volume overview | **Pro** |
| `GET /summary/derivatives/{protocol}` | One derivatives protocol summary | **Pro** |

**Common query params:** `excludeTotalDataChart=true`, `excludeTotalDataChartBreakdown=true`, `dataType=dailyVolume` (options also accepts `dailyPremiumVolume`, `dailyNotionalVolume`).

**`/summary/dexs/{protocol}` top-level fields:** `defillamaId, name, displayName, disabled, logo, address, url, category, twitter, gecko_id, total24h, total48hto24h, total7d, total14dto7d, total30d, total60dto30d, total1y, average1y, totalAllTime (often null), change_1d, change_7d, module, protocolType, chains, breakdown24h, totalDataChart, totalDataChartBreakdown, methodology`. The `/overview/dexs` response wraps per-protocol objects under a `protocols` array, plus top-level `totalDataChart` and `totalDataChartBreakdown`.

```bash
curl "https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
curl "https://api.llama.fi/summary/dexs/uniswap"
```
```python
r = requests.get("https://api.llama.fi/overview/dexs?excludeTotalDataChart=true&dataType=dailyVolume").json()
dexs = [p["name"] for p in r["protocols"]]
```

### 6. Fees & Revenue (`https://api.llama.fi`)

| Method/Path | Description | Tier |
|---|---|---|
| `GET /overview/fees` | All protocols + fee/revenue summaries | Free |
| `GET /overview/fees/{chain}` | Fees/revenue by chain | Free |
| `GET /summary/fees/{protocol}` | One protocol's fees + history | Free |

**`dataType` values:** `dailyFees` (default), `dailyRevenue`, `dailyHoldersRevenue`, `dailySupplySideRevenue`, `dailyProtocolRevenue`, `dailyUserFees`, `dailyBribesRevenue`, `dailyTokenTaxes`, `dailyAppFees`, `dailyAppRevenue`, plus `totalFees`/`totalRevenue`.

**`/summary/fees/{protocol}` top-level fields:** `name, defillamaId, displayName, module, category, chains, gecko_id, id, protocolType, total24h, total48hto24h, total7d, total30d, total1y, annualized1y, totalAllTime, change_1d, totalDataChart ([[timestamp,value]]), totalDataChartBreakdown, methodology, latestFetchIsOk`.

Example (live) `GET /summary/fees/ethereum?dataType=dailyFees`:
```json
{ "name":"Ethereum","defillamaId":"chain#ethereum","displayName":"Ethereum",
  "module":"ethereum","category":"Chain","chains":["Ethereum"],"gecko_id":"ethereum",
  "protocolType":"chain","total24h":307227,"total7d":2279175,"total30d":11323758,
  "total1y":294621194,"totalAllTime":20545485976,
  "totalDataChart":[[1438905600,50],[1438992000,91]],
  "methodology":{"UserFees":"Gas fees paid by users","Revenue":"Amount of ETH burned"} }
```

> Known issue (`DefiLlama/defillama-server` #4168): `dataType=totalFees`/`totalRevenue` can return `null` charts for some protocols; `dailyFees`/`dailyRevenue` are the reliable configs.

**Pro fee-charting extensions** (`pro-api.llama.fi/{KEY}/api/...`, exposed in the SDK): `getChart`, `getChartByChain`, `getChartByProtocol`, `getChartByProtocolChainBreakdown`, `getChartByProtocolVersionBreakdown`, `getChartByChainProtocolBreakdown`, `getChartChainBreakdown`, `getMetrics`.

### 7. Bridges (`https://bridges.llama.fi`)

| Method/Path | Description | Tier |
|---|---|---|
| `GET /bridges?includeChains=true` | All bridges + volume summaries | Free (list) |
| `GET /bridge/{id}` | One bridge detail (with tx counts + chain breakdown) | Pro |
| `GET /bridgevolume/{chain}?id={id}` | Historical daily volume for a chain/bridge | Pro |
| `GET /bridgedaystats/{timestamp}/{chain}?id={id}` | 24h token/address breakdown | Pro |
| `GET /transactions/{id}` | Transaction-level bridge data | Pro |

**`/bridges` element:** `{"id":26,"name":"zksync","displayName":"zkSync Era Bridge","icon":"chain:zksync era","volumePrevDay":55186404,"volumePrev2Day":46093693,"lastHourlyVolume":1449731.85,"currentDayVolume":30964194.86,"lastDailyVolume":55186404,"dayBeforeLastVolume":46093693,"weeklyVolume":310121296,"monthlyVolume":1274364417,"chains":["Ethereum","zkSync Era"],"destinationChain":"zkSync Era"}`. A single-bridge (`/bridge/{id}`) response adds `lastHourlyTxs, currentDayTxs, prevDayTxs, dayBeforeLastTxs, weeklyTxs, monthlyTxs` (each `{deposits, withdrawals}`) plus a `chainBreakdown` object keyed by chain.

**`/bridgevolume/{chain}` element:** `{"date":"1704758400","depositUSD":14309807,"withdrawUSD":2193118,"depositTxs":237,"withdrawTxs":43}`

**`/bridgedaystats/{ts}/{chain}` fields:** `date, totalTokensDeposited, totalTokensWithdrawn, totalAddressDeposited, totalAddressWithdrawn` (the token/address objects map identifiers → USD volume/amount).

```python
# slurpxbt/defillama_library-style construction
base = "https://bridges.llama.fi"
vol   = requests.get(f"{base}/bridgevolume/Ethereum?id=1").json()
stats = requests.get(f"{base}/bridgedaystats/1704067200/Ethereum?id=1").json()
```

### 8. Pro-only analytics & datasets (`https://pro-api.llama.fi/{KEY}/...`)

| Category | Endpoints |
|---|---|
| TVL extras | `/api/tokenProtocols/{symbol}`, `/api/inflows/{protocol}/{timestamp}`, `/api/chainAssets` |
| Token Unlocks / Emissions | `/api/emissions` (all), `/api/emission/{protocol}` |
| Protocol analytics DBs | `/api/categories`, `/api/forks`, `/api/oracles`, `/api/hacks`, `/api/raises`, `/api/treasuries`, `/api/entities` |
| Token liquidity | `/api/historicalLiquidity/{token}` |
| ETFs | `/etfs/snapshot`, `/etfs/flows` (+ BTC/ETH overview & history, `/fdv/performance/{period}` in SDK) |
| Digital Asset Treasuries | `/dat/institutions`, `/dat/institutions/{symbol}` |
| Equities | `/equities/v1/companies-list`, `/statements`, `/dimensions`, `/price-history`, `/ohlcv`, `/summary`, `/filings` |
| Real World Assets | `/rwa/current`, `/rwa/stats`, `/rwa/list`, `/rwa/chain/{chain}`, `/rwa/chart/chain/{chain}`, `/rwa/chart/chain-breakdown` |
| API key mgmt | `/usage/{APIKEY}` (returns credits left) |

**Inflows response** (`/api/inflows/{protocol}/{timestamp}`): `{"outflows":-160563462.2,"oldTokens":{"date":...,"tvl":{...}},"currentTokens":{"date":...,"tvl":{...}}}`.

**Pro SDK examples:**
```python
from defillama_sdk import DefiLlama
pro = DefiLlama({"api_key": "YOUR_KEY"})
pools       = pro.yields.getPools()
unlocks     = pro.emissions.getByProtocol("arbitrum")
treasuries  = pro.ecosystem.getTreasuries()
hacks       = pro.ecosystem.getHacks()
raises      = pro.ecosystem.getRaises()
mstr        = pro.dat.getInstitution("MSTR")
usage       = pro.account.getUsage()
```
```bash
curl "https://pro-api.llama.fi/YOUR_KEY/api/emissions"
curl "https://pro-api.llama.fi/YOUR_KEY/yields/pools"
curl "https://pro-api.llama.fi/YOUR_KEY/api/protocols"   # free endpoint via pro host = higher limits
```

**Error handling (both SDKs)** expose typed classes: `ApiKeyRequiredError`, `RateLimitError` (has `retry_after`/`retryAfter`), `NotFoundError`, `ApiError`.

---

## Recommendations (staged)

1. **Start free, keyless.** For an EVM/Algorand/cross-chain infrastructure layer, build against `api.llama.fi`, `coins.llama.fi`, and `stablecoins.llama.fi` first. TVL, multi-chain token prices (via `{chain}:{address}`), stablecoin supply, and DEX/fees overviews are all free and cover most infra needs. Cache aggressively — TVL/borrows/treasury/stablecoin/CEX/oracle and yields all update hourly, so a 5–15 minute cache TTL is safe and eliminates most rate-limit risk.
2. **Add a Pro key only when you hit a Pro-gated need:** production yields/pool APY monitoring, token unlock schedules (`/api/emissions`), perp/derivatives volume (`/api/overview/derivatives`), bridge transaction-level flows (`/bridge/*`, `/bridgevolume`, `/bridgedaystats`, `/transactions`), or the hacks/raises/treasuries databases. Threshold: subscribe ($300/mo) once you need >500 requests/min sustained or any of those gated paths.
3. **Wrap calls with retry + backoff.** Handle HTTP 429 with exponential backoff plus jitter; respect any `Retry-After` header. Prefer the official SDKs' typed error classes over hand-rolled logic.
4. **Filter on `confidence >= 0.8`** for price data, and treat low-confidence/exotic token prices skeptically since those are derived from DEX pool weights rather than CoinGecko/CMC feeds.
5. **Pin to slugs, not display names.** Protocol slugs come from `/protocols`; chain names must match `/v2/chains`. Persist these mappings rather than guessing.
6. **Benchmarks that would change the plan:** if monthly calls exceed 1M on the API tier, budget the $0.60/1,000 overage or move to Enterprise for raw DB access, hourly data, and token-address-level TVL breakdowns.

## Caveats
- **Free vs Pro path divergence is the #1 integration bug.** The same logical endpoint has different paths on the two hosts (e.g. `/stablecoins` → `/stablecoins/stablecoins`, `/pools` → `/yields/pools`, `/protocols` → `/api/protocols`). Never hardcode a free path onto the Pro host.
- **The $49 Pro dashboard plan is NOT the API plan.** API access requires the $300/mo "API" tier — the docs state plainly that "API access is not included in the Pro plan."
- **Rate-limit specificity:** The 500 requests/minute free limit comes from DefiLlama's own X/Twitter announcement (Jan 1, 2023): "Starting tomorrow we'll impose a limit of 500 requests/min in our API." The current docs page describes the free tier only qualitatively ("Standard" vs. the Pro tier's "Higher"), so treat 500/min as a soft ceiling, not a contractual guarantee.
- **Yields host ambiguity:** `yields.llama.fi/pools` responds without a key, yet DefiLlama's own free/pro matrix lists yields as Pro. Don't rely on the free host for production yield workloads.
- **`totalAllTime` is frequently `null`** in DEX/fees summary responses, and the `totalFees`/`totalRevenue` dataTypes can return null charts. Use `dailyFees`/`dailyRevenue`.
- **CORS & key hygiene:** the public API is widely called from browsers, but for production — and to keep your Pro key secret — always proxy Pro calls through your own server, since the key sits in the URL path and would leak in client-side code.
- **Data lag:** website vs API values can differ by up to 1 hour due to page caching; the API updates first. Volume/fees are mostly hourly, some protocols only daily at 00:00 UTC.
- **Populated bridge breakdown schema** (`totalTokensDeposited`/`totalAddressDeposited` inner values) is documented in prose rather than shown fully populated — verify against a live call for your specific target bridge and chain slug.
- **API surface evolves.** DefiLlama ships fast; new endpoints (e.g. beta v2 TVL/token-breakdown and treasury endpoints, MiCA exchanges, CEX transparency) appear regularly. Reconcile against `https://api-docs.defillama.com/` and the `/llms-free.txt` / `/llms-pro.txt` indexes before locking a schema.