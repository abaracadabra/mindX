# Integrating the CoinMarketCap API

### A definitive, project-agnostic guide, with mindX integration notes

*(c) 2026 BANKON — all rights reserved. Prose under the cypherpunk2048 documentation standard.*

---

## 1. Orientation

CoinMarketCap exposes one of the broadest market-data surfaces in the industry, advertising on the order of forty-eight million tracked assets, nine hundred-plus exchanges, and seventy-plus endpoints behind a single credentialed gateway at `https://pro-api.coinmarketcap.com`. For the purpose of integration the surface resolves into two product families and three access models, and understanding that two-by-three matrix before writing any code is what separates a clean integration from one that hemorrhages credits.

The two product families are the **Standard (crypto) API** and the **DEX API**. The Standard family is the long-established centralized-market surface: latest and historical quotes, ranked listings, global metrics, exchange data, categories, trending, and content. The DEX family, completed across two releases and now comprising eight endpoints, covers decentralized-exchange listings, network identification, spot-pair OHLCV, and trade-level data. The endpoint that originally motivated this guide, the second wave of five DEX endpoints, belongs to this family and is treated in detail in Section 5.

The three access models are orthogonal to the families and matter more for architecture than the endpoints themselves. The first is the **key-authenticated REST** model, the production default, where every request carries an `X-CMC_PRO_API_KEY` header and draws against a monthly credit pool. The second is the **keyless public** model, a fixed subset of production endpoints served from `https://pro-api.coinmarketcap.com/trial-pro-api` with no signup, useful for shape-checking a response before committing to a key. The third is **x402**, a pay-per-request model in which each call is settled in USDC on Base with no key and no account, designed expressly for autonomous agents. The x402 model is the one with direct bearing on the mindX and Parsec architecture, and it carries a settlement-chain caveat developed in Section 6.

---

## 2. Access and provisioning

For the key-authenticated path, a free Basic key is provisioned from the developer portal at `pro.coinmarketcap.com` with no subscription. An existing key already grants whatever the account's plan permits, including the DEX endpoints, so there is no separate DEX enrollment. The key is retrieved from the top-left of the portal dashboard, and the portal is also where usage, request logs, plan changes, and the ninety-five-percent-of-quota email notification are managed.

The keyless path requires nothing at all and is the fastest way to confirm an endpoint's response structure during development. Its endpoint subset is fixed by CoinMarketCap and excludes historical data, so it is a testing convenience rather than a production tier.

The x402 path requires only a funded wallet, treated in Section 6.

---

## 3. The credit and rate-limit model

The single most important operational fact about this API is that **a credit is not a request**. Credits are consumed as a function of what a call returns and how it is parameterised, and the multipliers are easy to trigger inadvertently. Each additional currency in the `convert` parameter beyond the first is billed as an extra unit of work; the Basic plan permits only one conversion per call, the higher tiers permit eight, forty, eighty, and one hundred twenty respectively. Pagination beyond a single page bills per page, and bundled multi-identifier queries bill per cohort of returned objects. The practical consequence is that a naive loop converting one asset at a time into three fiats across ten pages can cost an order of magnitude more than a single wide call returning the same data, even though the request count looks identical.

The plan ladder as published for 2026 begins with **Basic** at zero cost, granting roughly ten thousand monthly credits, thirty requests per minute, around thirty endpoints, and no historical data under a personal-use licence. **Hobbyist** at twenty-nine dollars monthly raises this to one hundred ten thousand credits, forty-plus endpoints, and twelve months of history, still personal-use. **Startup** at seventy-nine dollars is the first commercial-use tier, with three hundred thousand credits, fifty-plus endpoints, and twenty-four months of history. **Standard** at two hundred ninety-nine dollars opens all endpoints with 1.2 million credits, sixty requests per minute, and sixty months of history. **Professional** at six hundred ninety-nine dollars reaches three million credits, ninety requests per minute, and all-time history. **Enterprise** is custom across credits, rate limit, full-resolution history, and licence terms, with a published service-level agreement. Pricing changes, so the published page and the `402` response body are the authoritative source rather than any figure quoted here.

The rate limit is a separate ceiling from the credit pool, expressed in requests per minute and resetting every sixty seconds, and exhausting it returns HTTP `429` independently of how many credits remain. A correct client therefore defends both boundaries: it backs off on `429`, and it conserves the monthly pool through caching and wide queries.

The commercial-use clause deserves a deliberate read for any revenue-bearing deployment. The licence on the commercial tiers is limited, non-exclusive, and non-transferable, and it forbids redistributing or reselling the data as a standalone service such as one's own API or data feed. The data must be an integrated component of a larger product. For a system like AgenticPlace or mindX that surfaces market data to end users as one feature among many, this is satisfied; for any design that would re-expose CMC data as a priced data endpoint of its own, it is not, and the Enterprise licence conversation is the correct path.

---

## 4. Authentication and envelope

Every key-authenticated request carries the key in the `X-CMC_PRO_API_KEY` header and an `Accept: application/json` header against the `https://pro-api.coinmarketcap.com` base. The key is never placed in the query string. Responses share a uniform envelope of the form `{"status": {...}, "data": {...}}`, where `status` carries an `error_code`, an `error_message`, a timestamp, and the credit cost of the call, and `data` carries the payload. A non-zero `error_code` is the failure signal even when the HTTP status is `200`; credit exhaustion in particular surfaces as code `1008`. A robust client inspects `status.error_code` on every response rather than trusting the transport status alone, which is precisely what the companion client's `_get` does before returning the bare `data` body.

---

## 5. The endpoint catalogue and the five DEX additions

The Standard family is organised under versioned cryptocurrency, exchange, global-metrics, and content groupings. The two workhorses are `/v2/cryptocurrency/quotes/latest`, which returns current quotes for a set of identifiers, and `/v1/cryptocurrency/listings/latest`, which returns a ranked market slice. Historical variants of each exist and are plan-gated by depth and interval resolution. For chain mapping and DEX work, the eight `/v4/dex/*` endpoints are the relevant surface, and the five that completed the suite are these.

`/v4/dex/listings/quotes` returns the decentralized exchanges with their latest aggregate market data, including market share, pair counts, and open interest, and is the basis for comparing venues. `/v4/dex/listings/info` returns static metadata for a DEX, including launch date, logo, official and social links, and fee information, and is the reference-data complement to the quotes endpoint. `/v4/dex/networks/list` returns every network with its unique CoinMarketCap identifier and is the most architecturally significant of the five, because those identifiers are the stable join key that the other DEX endpoints expect; building against chain slugs rather than these identifiers is a recurring source of breakage. `/v4/dex/pairs/ohlcv/historical` returns historical OHLCV candles with market cap for a spot pair under a time-interval parameter, suitable for backfilling charts and backtesting. `/v4/dex/pairs/trade/latest` returns up to the latest one hundred trades for a spot pair, each carrying its on-chain transaction hash, which makes it usable for settlement audit rather than display alone.

During the suite's soft-launch periods CoinMarketCap has repeatedly offered elevated free allocations and rate limits; whether such an allocation is active is worth checking against the current academy announcements before sizing a plan, since it materially changes the economics of a DEX-heavy integration.

---

## 6. The x402 pay-per-request path, and the Algorand caveat

The x402 model is an open protocol, originated by Coinbase, that turns the dormant HTTP `402 Payment Required` status into a working payment handshake. A client issues an ordinary request; the server answers `402` and attaches a base64 `payment-required` header describing the settlement terms; the client decodes those terms, signs an EIP-3009 `transferWithAuthorization` for the named amount with its wallet, and resends the identical request with the signed authorization in the canonical x402 `X-PAYMENT` header — `base64(JSON({x402Version, scheme, network, payload}))`, the same envelope the rest of the BANKON stack uses. On verification the server returns `200` with the data. No key, account, or onboarding is involved, because the payment itself — the **signature** — is the access control, which is exactly the property an autonomous agent wants.

Decoding a real CoinMarketCap challenge makes the terms concrete. The `payment-required` header on `/x402/v3/cryptocurrency/quotes/latest` resolves to a document whose first accepted term names `network: eip155:8453`, `asset: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, and `amount: 10000`. That network identifier is Base mainnet, that asset is the canonical USDC contract on Base, and that amount is ten thousand of USDC's six minor units, which is one cent. The `exact` scheme and a thirty-second timeout complete the term. The currently x402-enabled endpoints are the cryptocurrency quotes-latest and listing-latest pair, the DEX pairs-quotes-latest and DEX-search pair, and the MCP endpoint, each at one cent per call subject to change and rate-limited per wallet.

Here is the caveat that matters for this ecosystem specifically. **CoinMarketCap's x402 settles in USDC on Base, an EVM chain.** The Parsec and GoPlausible x402 rails in the BANKON architecture settle on **Algorand**. These are the same protocol over two different settlement layers, and they do not interoperate at the payment step: an Algorand USDC authorization cannot satisfy a challenge that names `eip155:8453`. Consuming CoinMarketCap data over x402 therefore requires either a Base-side wallet funded with USDC held alongside the Algorand-native treasury, or a fallback to the key-authenticated path for CMC specifically while reserving the Algorand x402 rails for first-party AgenticPlace and mindX services. The cleanest design keeps the two as distinct payment adapters behind a common interface, so that "pay for outbound data" and "charge for inbound service" never assume a single chain. CoinMarketCap's own documentation hints at Solana as a second settlement chain in places while elsewhere naming Base alone as currently supported; neither is Algorand, so the caveat stands until CMC publishes otherwise, and the `402` response body remains the authority on which chains are live.

The companion client encodes this separation deliberately. The `cmc_x402_client` performs the full `402`-decode-resign-resend cycle but delegates signing to an injected `wallet_sign` callable, so the module itself carries no chain dependency and the Base-versus-Algorand decision lives entirely in whichever wallet the integrator supplies. The concrete Base wallet is `x402_signer.x402_wallet_signer`: it reads its signing key from `.env` (`X402_WALLET_PRIVATE_KEY`, never hard-coded), produces the EIP-3009 / EIP-712 authorization, returns the `X-PAYMENT` payload, and enforces a per-call USDC ceiling so an autonomous agent cannot overspend — declining (an empty signature, surfaced as `CmcPaymentRequired`) rather than paying past budget.

---

## 7. The reference client

The companion module `cmc_client.py` is the concrete artifact of this guide and is written to the cypherpunk2048 standard: Apache 2.0 header, Python 3.12 target, flat snake_case layout, and Google-style docstrings. Its design choice is that consumers depend on a narrow `market_data_provider` protocol rather than on CoinMarketCap directly, which keeps mindX agnostic and lets a competing source be substituted without disturbing call sites. The `cmc_client` class implements that protocol over the key-authenticated surface, normalises the response envelope, raises typed `CmcRateLimitError` and `CmcCreditError` exceptions on the two distinct exhaustion conditions, and fronts the quote and DEX-network calls with a TTL cache because a single avoided call reclaims real credits on the Basic pool. A `keyless=True` flag reroutes the same methods to the public base path for development. The `cmc_x402_client` class implements the pay-per-request path with the delegated-signing design described above, and the standalone `decode_payment_challenge` function is the offline-verifiable core of the x402 handshake. Every one of these pieces is exercised by the offline test suite, which confirms the real CMC challenge decodes to Base USDC at one cent, the cache expires on schedule, the protocol conformance holds, and the error paths raise the correct types.

---

## 8. mindX integration patterns

Four patterns make this integration durable inside the mindX and AgenticPlace context. The first is **agnosticism by protocol**: every consumer imports `market_data_provider`, never `cmc_client`, so that the eventual addition of an on-chain oracle or a CoinGecko adapter is a registration change rather than a refactor. The second is **chain mapping by CoinMarketCap identifier**: the `dex_networks_list` result is persisted once and used as the canonical map between the chains enumerated in `allchain.html` and the network identifiers that the DEX endpoints demand, so that SPINTRADE and DELTAVERSE pair lookups address chains by stable identifier rather than by slug. The third is **credit conservation as a first-class concern**: wide single calls over narrow loops, single `convert` currencies unless a multi-currency view is genuinely needed, and short-TTL caching on hot quote paths, all of which the client embodies and all of which directly extend the runway of a free or low tier. The fourth is **payment-adapter separation**: outbound data payments to CoinMarketCap over x402 settle on Base and belong to a Base wallet adapter, while inbound service charges on AgenticPlace settle on Algorand through Parsec; sharing the `wallet_sign` seam but not the chain keeps both honest and prevents the architecture from silently assuming a single settlement layer.

The result is a market-data layer that any project can adopt unchanged, that conserves the credit pool by construction, that maps cleanly onto the existing all-chain enumeration, and that keeps the Base-settled CoinMarketCap x402 path cleanly partitioned from the Algorand-native payment rails that define the rest of the stack.

---

## 9. Pitfalls

The recurring failures are predictable. Treating credits as requests is the first and most expensive. Trusting the HTTP status while ignoring a non-zero `status.error_code` is the second, and it produces silent data loss rather than a loud failure. Addressing DEX endpoints by chain slug instead of CoinMarketCap network identifier is the third. Assuming the x402 path can be paid from an Algorand wallet is the fourth, and it fails at the signature step rather than at integration time, which makes it costly to discover late. And designing in a way that re-exposes CoinMarketCap data as a standalone feed is the fifth, a licence violation rather than a technical fault, and the one that scales worst. A client that inspects the envelope, respects both ceilings, joins on identifiers, partitions its payment adapters by chain, and keeps the data integrated rather than resold avoids all five.
