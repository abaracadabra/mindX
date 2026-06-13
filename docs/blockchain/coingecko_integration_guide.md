# Integrating the CoinGecko API

### A definitive, project-agnostic guide, with mindX integration notes

*(c) 2026 BANKON — all rights reserved. Prose under the cypherpunk2048 documentation standard.*

---

## 1. Orientation

CoinGecko is the broadest independent market-data surface in crypto, tracking
prices, market caps, volumes, supply, categories, exchanges, derivatives, NFTs,
and — through its GeckoTerminal acquisition — on-chain DEX pools. Where
CoinMarketCap resolves into a two-by-three matrix of product families and access
models, CoinGecko resolves more simply into **one REST shape across two tiers**,
and understanding that split before writing any code is what keeps an
integration both cheap and correct.

The two tiers are the **free/Demo** tier and the **Pro** tier. They share the
same `/api/v3` path vocabulary and the same raw-JSON response style, and differ
in three places only: the host, the name of the authentication header, and which
endpoints (and rate limits) are available. That narrow difference is exactly what
makes a clean separation between *public consumption* and *ingestion* possible:
the free tier is for live read-paths and dashboards, the Pro tier is for
bulk and range-bounded backfill.

The companion module `coingecko_client.py` encodes that separation as **two
classes** — `coingecko_public_client` and `coingecko_pro_client` — rather than a
flag. The class a caller holds *is* the tier: a public client handed to a
dashboard cannot reach a paid backfill endpoint, because those methods exist only
on the Pro client. This mirrors the two-class precedent in `cmc_client.py` and is
the structural answer to "keep free consumption and paid ingestion apart."

---

## 2. Access and provisioning

The **free/Demo** tier is served from `https://api.coingecko.com/api/v3`. It works
with no credentials at all; a free **Demo key**, provisioned from the developer
dashboard, is optional and is supplied through the `x-cg-demo-api-key` header to
lift the anonymous rate limit and stabilise throughput. The Demo plan publishes a
rate limit on the order of thirty calls per minute and a monthly call cap in the
low tens of thousands — generous for read-paths, tight for sweeps.

The **Pro** tier is served from a *different host*,
`https://pro-api.coingecko.com/api/v3`, and authenticates with a *different
header*, `x-cg-pro-api-key`. The key is required. The Pro tier raises the rate
limit substantially, unlocks range and OHLC endpoints suitable for backfill, and
exposes the on-chain (GeckoTerminal) surface under `/onchain`.

The two tiers must not be crossed: a Demo key sent to the Pro host, or a Pro key
to the Demo host, yields HTTP 401/403. The client binds the host and header name
to the class, so this mistake is unrepresentable once the right class is chosen.

---

## 3. The rate-limit model

Unlike CoinMarketCap, CoinGecko does not bill a multiplied "credit" per call;
the operative ceiling is the **requests-per-minute rate limit**, and the dominant
free-tier failure is HTTP 429. A correct client therefore defends the rate limit
rather than a credit pool: it backs off on 429, and it conserves calls through
two habits the client embodies.

The first is **batching**: `quotes_latest` / `simple_price` and `coins_markets`
accept comma-separated id lists and wide `per_page` values, so a single call
returns what a naive per-asset loop would spend dozens of calls on. The second is
**short-TTL caching**: hot price paths cache for sixty seconds, per-asset detail
for two minutes, and the rarely-changing id and platform directories for one
hour. A single avoided `/simple/price` on the Demo tier directly extends the
runway under the per-minute ceiling.

On the Pro tier the rate limit is higher and plan-gated; treat a plan-limit
response (HTTP 429, occasionally with a body-level error document) the same way —
back off and retry — and prefer wide ingestion pages over many narrow ones.

---

## 4. Authentication and the raw-JSON body

The free tier sends the optional Demo key as `x-cg-demo-api-key`; the Pro tier
sends the required Pro key as `x-cg-pro-api-key`. The key is never placed in the
query string.

The single most important structural fact for a client author is that
**CoinGecko returns raw JSON with no envelope**. There is no
`{"status": {...}, "data": {...}}` wrapper to unwrap as there is on
CoinMarketCap; the decoded body *is* the payload. The client's `_get` therefore
returns `response.json()` verbatim, and reads failure from the HTTP status —
429 to a rate-limit error, 401/403 to an auth error, any other non-2xx to the
base error — rather than from a status field. A body-level `status.error_message`
or `error` is consulted only opportunistically on a 4xx, never required.

---

## 5. The endpoint catalogue

### Free / Demo — public consumption (`coingecko_public_client`)

| Method | Endpoint | Purpose | Cache |
|---|---|---|---|
| `quotes_latest(ids, convert)` | `/simple/price` | Protocol method: latest prices by id | 60s |
| `simple_price(ids, vs_currencies, …)` | `/simple/price` | Prices with optional mcap/vol/change | 60s |
| `coins_markets(vs_currency, ids, per_page, page, order)` | `/coins/markets` | Ranked market slice | 60s |
| `coin(id, …)` | `/coins/{id}` | Per-asset detail | 120s |
| `coins_list(include_platform)` | `/coins/list` | Full id directory (the canonical id map) | 3600s |
| `asset_platforms()` | `/asset_platforms` | Chains/platforms with their ids | 3600s |
| `dex_networks_list()` | `/asset_platforms` | Protocol alias of `asset_platforms` | 3600s |
| `market_chart(id, vs_currency, days)` | `/coins/{id}/market_chart` | Windowed price/mcap/volume chart | 120s |

### Pro — ingestion (`coingecko_pro_client`)

Inherits every consumption method (routed against the Pro host and header) and
adds the bulk/range surface. Each is Pro-gated and raises an auth error on a Demo
key:

| Method | Endpoint | Purpose |
|---|---|---|
| `market_chart_range(id, vs_currency, from_ts, to_ts)` | `/coins/{id}/market_chart/range` | Range-bounded backfill |
| `ohlc(id, vs_currency, days)` | `/coins/{id}/ohlc` | OHLC candles |
| `coins_markets_paged(vs_currency, page, per_page)` | `/coins/markets` | Wide ingestion pages (per_page→250) |
| `onchain(path_suffix, params)` | `/onchain/{suffix}` | GeckoTerminal on-chain pass-through |

The `/asset_platforms` ids are the stable join key for on-chain lookups; persist
them rather than chain slugs, exactly as the CoinMarketCap guide persists DEX
network ids. The `onchain` helper takes a path suffix rather than enumerating the
GeckoTerminal sub-paths, because those shift over time; the unstable part stays a
parameter.

---

## 6. The reference client

`coingecko_client.py` is the concrete artifact of this guide, written to the
cypherpunk2048 standard: Apache 2.0 header, Python 3.12 target, flat snake_case
layout, Google-style docstrings, `httpx` with no SDK dependency. Its design
choices are three.

First, **agnosticism by protocol**: `coingecko_public_client` implements the
vendor-neutral `market_data_provider` protocol imported from `cmc_client`, so a
consumer that depends on the protocol can swap CoinGecko for CoinMarketCap as a
registration change rather than a refactor. `quotes_latest` maps to
`/simple/price` and `dex_networks_list` aliases `/asset_platforms` to satisfy the
contract honestly.

Second, **tier separation by class**: the public and Pro surfaces are two
classes, not a flag, so the consumption/ingestion boundary is enforced by which
object a caller holds. The Pro class requires its key and binds the Pro host and
header; the public class works keyless and binds the Demo host and header.

Third, **conservation by construction**: the shared `ttl_cache` is reused (not
duplicated), batching is the documented default, and TTLs are tuned to each
endpoint's volatility. Every piece is exercised by the offline test suite
(`test_coingecko_client.py`), which confirms protocol conformance, cache expiry,
typed error paths, raw-JSON passthrough, and per-tier header selection — all
against an injected mock transport, with no network.

---

## 7. mindX integration patterns

The same four patterns that make the CoinMarketCap integration durable apply
here. **Agnosticism by protocol**: import `market_data_provider`, never
`coingecko_public_client`, so the source is a registration detail. **Chain
mapping by platform id**: persist `asset_platforms` once and join on the platform
id rather than the chain slug. **Conservation as a first-class concern**: wide
batched calls, single vs-currencies unless a multi-currency view is genuinely
needed, and short-TTL caching on hot price paths. **Tier separation**: read-paths
hold a `coingecko_public_client`; only the ingestion/backfill projector holds a
`coingecko_pro_client`, so a paid endpoint can never be reached from a free
read-path by accident.

The result is a market-data layer any project can adopt unchanged, that conserves
the rate budget by construction, that maps cleanly onto the existing all-chain
enumeration, and that keeps free public consumption cleanly partitioned from paid
ingestion.

---

## 8. Pitfalls

The recurring failures are predictable. Crossing the tiers — a Demo key against
the Pro host or the reverse — fails at 401/403 and is the first. Looking for a
`data` envelope to unwrap, as one would on CoinMarketCap, is the second, and it
produces an `AttributeError` rather than a clean read. Treating the rate limit as
a credit pool and looping per-asset is the third, and it exhausts the per-minute
ceiling an order of magnitude faster than a batched call. Addressing on-chain
endpoints by chain slug instead of platform id is the fourth. And calling a
Pro-gated range or OHLC endpoint from a free client is the fifth — though the
two-class design turns that from a runtime 401 into a method that simply does not
exist on the object in hand, which is the cheapest place to catch it.
