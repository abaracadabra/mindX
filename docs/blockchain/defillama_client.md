# DefiLlama client — design note

*(c) 2026 BANKON — all rights reserved. Prose under the cypherpunk2048 documentation standard.*

This note documents only the **client design** of `defillama_client.py`. The
authoritative API reference is the official integration guide at
[`docs/publications/pdf/DefiLlama Integration Guide for Agentic AI Systems.pdf`](../publications/pdf/DefiLlama%20Integration%20Guide%20for%20Agentic%20AI%20Systems.pdf)
— consult it for the full endpoint catalogue, pricing, and rate-limit history.
What follows is the part the PDF does not cover: how the companion module is
shaped, and the traps the shape exists to avoid.

---

## Two classes, two services

The defining requirement is a **clear separation between free-tier public
consumption and authenticated API calls for ingestion**, and with DefiLlama that
separation is not a stylistic choice — the free and Pro tiers are, by DefiLlama's
own statement, *entirely separate services*. The module therefore ships **two
classes**, mirroring the two-class precedent in `cmc_client.py`:

| Class | Tier | Auth | Hosts | Purpose |
|---|---|---|---|---|
| `defillama_public_client` | Free | none | five host roots | public consumption / read-paths |
| `defillama_pro_client` | Pro | key **in URL path** | `pro-api.llama.fi/{key}` | ingestion / backfill |

The class a caller holds *is* the tier. A read-path that holds a
`defillama_public_client` cannot reach a paid ingestion endpoint, because those
methods live only on the Pro client.

---

## The free tier is multi-host

The free surface is not one base URL — it spans five host roots, mapped in the
`FREE_HOSTS` constant:

```python
FREE_HOSTS = {
    "tvl":         "https://api.llama.fi",        # protocols, chains, TVL, fees, dexs
    "coins":       "https://coins.llama.fi",      # prices (current/historical/first/chart)
    "stablecoins": "https://stablecoins.llama.fi",
    "yields":      "https://yields.llama.fi",     # /pools, /chart/{pool}
    "bridges":     "https://bridges.llama.fi",
}
```

Because no single `base_url` serves all five, `defillama_public_client` builds an
**absolute URL per call** and routes each method to the right host. The shared
`_get(url, ...)` therefore takes a full URL rather than a path. A consequence
worth stating: if a caller injects their own `httpx.Client`, it must be
**base-url-less** — a base URL on the injected client would corrupt the absolute
routing.

---

## The Pro key goes in the path, never a header

The Pro tier authenticates by **embedding the key in the URL path**
(`https://pro-api.llama.fi/{API_KEY}/...`), not by a header. The client
interpolates the key once into the httpx `base_url` at construction. Two safety
rules follow and are encoded:

- The full base URL — which carries the secret — is **never logged**.
- Pro cache keys are prefixed `pro:` and built from the **path only**, so the key
  never lands in cache state either.
- The Pro client **never falls back to a free host**, and the free client never
  reaches the Pro service. The two services stay disjoint.

The key falls back to the `DEFILLAMA_API_KEY` environment variable and is
required; construction raises `DefillamaError` when it is absent.

---

## No credit concept; raw JSON

DefiLlama bills no multiplied "credit" per call and has **no analogue to
CoinMarketCap's HTTP 402 / error code 1008**, so the error tree deliberately
omits a credit-exhaustion class. It carries only:

- `DefillamaError` — base
- `DefillamaRateLimitError` — HTTP 429 (free tier ≈ 500 req/min per IP)
- `DefillamaAuthError` — HTTP 401/403 (bad Pro key in path)

Responses are **raw JSON with no envelope**; `_get` returns the decoded body
verbatim. The ingestion (`_max_retries = 4`) path applies a bounded exponential
backoff to 429/5xx; the consumption path uses zero retries (`_max_retries = 0`)
and raises immediately, so a read-path fails fast rather than stalling.

---

## Agnostic protocols

DeFi/TVL data is not asset-quotes, so the module does **not** force the
CoinMarketCap `market_data_provider` protocol. It defines two narrow,
`@runtime_checkable` protocols instead, and `defillama_public_client` conforms to
both:

- `tvl_data_provider` — `protocols()`, `protocol(slug)`, `chains()`
- `price_data_provider` — `prices_current(coins)`

`price_data_provider` is a vendor-neutral price seam distinct from CMC's
quote-by-id seam, because DefiLlama keys prices by the `{chain}:{address}` coin
identifier (e.g. `ethereum:0xA0b8...`, captured in the `COIN_ID_FORMAT` constant).
The shared `ttl_cache` is reused from `cmc_client`, not duplicated.

---

## Cache TTLs

Following the PDF's guidance (TVL ≈ hourly, prices high-frequency, lists slow):

| Surface | Examples | TTL |
|---|---|---|
| Hot prices | `prices_current` | 60s |
| Percentages / perps / inflows | `prices_percentage`, `yields_perps`, `inflows` | 120s |
| Most analytics | `protocol`, `charts`, `overview_*`, `stablecoin*`, ETFs | 300s |
| Slow lists | `protocols`, `chains`, `yield_pools`, `bridges` | 600s |
| Static history | `prices_first` | 3600s |

---

## Method map (Pro / ingestion)

`defillama_pro_client` exposes the Pro-exclusive ingestion endpoints (paths are
relative to `/{key}`): `emissions` (`/api/emissions`), `categories`, `oracles`,
`hacks`, `raises`, `treasuries`, `entities`, `inflows(protocol, ts)`,
`yields_pools_old` (`/yields/poolsOld`), `yields_perps`, `etfs_snapshot`,
`etfs_flows`, and `historical_liquidity(token)`. See the PDF §2.8 for the full
Pro-exclusive catalogue.

---

## Tests

`test_defillama_client.py` exercises the design offline against an injected mock
transport (no network): protocol conformance, multi-host routing, cache expiry,
typed error paths, the consumption path's no-retry behaviour, and — the security
crux — that the Pro key lands in the **URL path and never in a header**, and never
in a cache key.
