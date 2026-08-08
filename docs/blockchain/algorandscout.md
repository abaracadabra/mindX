# Algorandscout — mindX's Algorand explorer API

> **What this is:** [`OpenBDK/algorandscout`](https://github.com/openbdk/algorandscout) — an
> **independent, BANKON-licensed explorer API for [Algorand](https://algorand.co/)**: accounts,
> assets, applications, transactions and rounds, served over Algorand's own
> [algod](https://developer.algorand.org/docs/rest-apis/algod/) and
> [indexer](https://developer.algorand.org/docs/rest-apis/indexer/) APIs.
>
> **[v1.0.0](https://github.com/openbdk/algorandscout/releases/tag/v1.0.0) — released 2026-08-08.**
> 12 `/api/v2` routes + allowlisted passthrough · **185 tests** passing offline against fixtures
> captured live from Algorand mainnet · container, Prometheus metrics, liveness/readiness probes,
> checksum-validated inputs, CI on Python 3.10–3.12.
>
> **What 1.0.0 claims:** the `/api/v2` response shapes and configuration surface are stable under
> semver. **What it does not claim:** production operation — built and tested, not yet operated.
>
> **Why mindX cares:** mindX's governance identity lives on Algorand, and until this existed
> mindX had no way to verify it independently.
>
> **Part of the [gated reference corpus](NAV.md)** — ingest-only, never published to `/docs.html`.

---

## 1. Why mindX needs this

mindX holds real state on Algorand:

- **`mindx.algo`** — the OVERSEER identity, Ed25519 → JWT (see the OVERSEER Algorand login path)
- **BONA FIDE** — the reputation-as-privilege layer that governs the DAIO hierarchy
- **[Parsec](https://parsec.pythai.net)** — the AVM wallet surface, and the
  [x402 v2 multi-rail](x402_rails.py) Parsec AVM rail
- ASA-denominated instruments in the [measurement-token](../mindx_strategy.md) stack

Every one of those was previously unreadable. mindX's other chain reader
([blockscout.md](blockscout.md)) covers EVM chains only — 17 chain types, all EVM — because
its schema assumes 20-byte addresses, gas, nonces, indexed log topics and reorgs. Algorand has
none of those, so the coverage gap was structural, not an oversight.

The doctrine mindX had written for itself was *"never let an answer imply coverage it does not
have."* Algorandscout is the other half of honouring that: the same *kind* of answer, sourced
from Algorand's own APIs, with the chain's actual model preserved.

---

## 2. Why a standalone service

**It is an original work.** Algorandscout contains no third-party explorer source code, vendors
none, and links none. Its runtime dependencies are aiohttp, FastAPI and uvicorn. It is licensed
under the **BANKON License** (Apache-2.0) as part of [OpenBDK](https://github.com/openbdk), and
is free to be distributed, hosted and monetised on its own terms.

Its REST layout follows conventions common to explorer APIs (`/api/v2/addresses/…`,
`{items, next_page_params}` pages) so existing tooling interoperates without modification. That
is a compatibility property, not a lineage — interface convention is not derivation.

**Algorand's model governs.** Where the chain and a generic explorer model disagree, the chain
wins and the difference is *declared* at `/api/v2/capabilities` rather than papered over:

| Generic explorer assumption | Algorand |
|---|---|
| 20-byte hex address | 58-character base32 Ed25519 |
| gas market | flat fee + fixed opcode budget — compute is not purchased |
| per-account nonce | first-valid/last-valid round window + genesis hash |
| logs with indexed topics | ordered array of **opaque** byte strings |
| reorgs, uncles | final on write |
| token approve/allowance | ASA with **clawback**, freeze, manager, reserve roles |

That last row is why flattening matters. A **clawback** holder can move an asset out of an
account **without the holder signing** — by design, for regulated instruments. Rendered as a
generic token, the row has nowhere to go and silently disappears. Algorandscout reports the four
privileged roles always, and *names* a clawback transfer as one.

---

## 3. The surface

### The explorer API — `/api/v2/*`

| Route | Returns |
|---|---|
| `GET /api/v2/capabilities` | **Start here.** Machine-readable statement of what this API can and cannot answer, and why |
| `GET /api/v2/stats` | Chain tip, indexer lag, block time, `is_evm: false` |
| `GET /api/v2/blocks` · `/blocks/{round}` | Rounds; `?include_transactions=` off by default |
| `GET /api/v2/transactions/{txid}` | One transaction, inner transactions recursed |
| `GET /api/v2/addresses/{address}` | Account: native balance, rekey target, counters; `?live=` reads the node |
| `GET /api/v2/addresses/{address}/transactions` | History; `after_time`/`before_time` (RFC-3339), `tx_type`, `asset_id` |
| `GET /api/v2/addresses/{address}/token-balances` | ASA holdings, metadata resolved by default |
| `GET /api/v2/tokens/{asset_id}` · `/holders` | ASA params, the four privileged roles, holder page |
| `GET /api/v2/smart-contracts/{app_id}` | Application: AVM programs, state schema, decoded global state |
| `GET /api/v2/search?q=` | Resolves by shape: address · txid · asset/app id · unit-name candidates |
| `GET /algorand/v2/*` | **Allowlisted** indexer passthrough (allowlist, not prefix-match — never an open proxy) |
| `GET /health` | Both upstreams + how far the archive trails the node |

### The two rules that bite

1. **Holdings live on two surfaces.** `/addresses/{a}` carries the ALGO balance;
   `/addresses/{a}/token-balances` carries the ASAs. Neither subsumes the other — the same
   completeness fork that applies on any chain with two value surfaces.
2. **The address is not hex.** `hash` carries the 58-character base32 address verbatim. A client
   validating `^0x[0-9a-fA-F]{40}$` will reject it, and **that rejection is correct** — the
   module refuses to fabricate a hex-shaped address to keep such a client quiet.

---

## 4. Honesty invariants (enforced by tests)

The assertions that matter are the negative ones:

- `gas_used`, `gas_price`, `gas_limit`, `nonce`, `revert_reason` → **`null`**, never `0`
- `abi`, `source_code`, `compiler_version` → **`null`**; `is_verified: false` — there is no
  Etherscan-style verified-source registry for AVM programs
- a round's **own** block hash → **`null`**, because the indexer returns only the parent's;
  reusing the parent hash would be a plausible-looking lie
- NFT classification (`total=1, decimals=0`) is labelled a **convention**
  ([ARC-3](https://arc.algorand.foundation/ARCs/arc-0003)/[ARC-19](https://arc.algorand.foundation/ARCs/arc-0019)/[ARC-69](https://arc.algorand.foundation/ARCs/arc-0069)),
  not an on-chain type
- clawback transfers are **named as clawbacks**, not shown as ordinary transfers
- `uint64` amounts never touch a float — the USDC ASA total is 2⁶⁴−1 and a float would
  silently round it
- **read-only structurally**: no signing key, no write route; a test fails if a write-shaped
  method ever appears on the client

Fixtures are **real mainnet responses** captured 2026-08-08 — USDC ASA `31566704`, a
[Tinyman](https://tinyman.org/) application `1002541853`, round `63879000`, a live account — not
hand-written approximations.

---

## 5. Running it

```bash
git clone https://github.com/openbdk/algorandscout && cd algorandscout
pip install -e '.[service]'
python -m algorandscout --port 8100
curl localhost:8100/api/v2/capabilities
curl localhost:8100/api/v2/tokens/31566704
```

| Variable | Default | Notes |
|---|---|---|
| `ALGORAND_ALGOD_URL` | `https://mainnet-api.algonode.cloud` | the node — knows *now* |
| `ALGORAND_INDEXER_URL` | `https://mainnet-idx.algonode.cloud` | the archive — knows *history* |
| `ALGORAND_API_TOKEN` / `_HEADER` | *(empty)* / `X-Algo-API-Token` | [AlgoNode](https://algonode.io/) is keyless; other providers are not |
| `ALGORAND_NETWORK` | `mainnet` | `mainnet` · `testnet` · `betanet` · `localnet` |
| `OPENBDK_HOST` / `OPENBDK_PORT` | `127.0.0.1` / `8100` | service bind |

Retry policy: **5xx retried 3× with jittered backoff; 4xx never — except 429**, which describes
*when* a request arrived rather than what was in it (`Retry-After` honoured, clamped).

---

## 6. mindX integration status — honest

**Not yet wired.** Algorandscout is built, tested, and published; nothing in mindX calls it yet.
What it unlocks, in the order worth doing:

1. **OVERSEER identity verification** — read `mindx.algo`'s account, rekey state, and holdings
   independently of the login path that asserts them, the same way
   [`get_transaction_info`](blockscout.md#81-verify-a-memory-anchor-without-trusting-our-own-logs)
   independently verifies an Arc memory anchor.
2. **BONA FIDE reputation reads** — holdings and app state as the objective input to the
   privilege ladder, rather than self-reported governance state.
3. **A second `/insight/*` chain surface** — an Algorand analogue of `/insight/storage/*`, so the
   diagnostics dashboard stops being EVM-shaped.
4. **Parsec / AVM x402 rail settlement checks** — confirm an AVM-rail payment landed.

Until those exist, this document describes a **capability, not a deployment**. mindX asserts
nothing about Algorand state on the strength of it.

---

## 7. The Algorand explorer landscape

Algorandscout is a **machine** read surface. The list below is the **human** one — where a
person goes to look at an address, and where to send a reader in a published post. All URLs
probed live on **2026-08-08**; status is what this host actually got back, not what a
directory claims.

### Live general-purpose explorers

| Explorer | URL | Built by | Notes |
|---|---|---|---|
| **Allo** | [allo.info](https://allo.info/) | [AlgoNode](https://algonode.io/) | The de-facto default. Assets, accounts, apps, blocks, transactions, [NFDomains](https://app.nf.domains/), NFT rarity, token prices, and a **TEAL inspector** for reading AVM programs. Deep links work: `allo.info/block/{round}`, `/tx/{txid}`, `/account/{addr}`, `/asset/{id}` — **verified 200** |
| **Pera Explorer** | [explorer.perawallet.app](https://explorer.perawallet.app/) | [Pera Wallet](https://perawallet.app/) | Account-centric, with the **ASA verification database** — the closest thing Algorand has to an authenticity signal for assets. Deep links: `/address/{addr}`, `/tx/{txid}`, `/asset/{id}`. **Returns 403 to non-browser clients** (bot protection): fine for humans, unusable for scripted checks |
| **Lora** | [lora.algokit.io](https://lora.algokit.io/) | [Algorand Foundation](https://algorand.co/) / [AlgoKit](https://github.com/algorandfoundation/algokit-cli) | The official developer explorer and **successor to Dappflow**. Network-scoped paths (`/mainnet/block/{round}`) and it can point at **localnet or any custom node** — the one to use while developing. **Verified 200** |
| **Bitquery** | [explorer.bitquery.io/algorand](https://explorer.bitquery.io/algorand) | [Bitquery](https://bitquery.io/) | Multi-chain (40+ chains) with a **GraphQL API** over Algorand data. Useful when a question spans Algorand *and* an EVM chain. **403 to curl** |

### Adjacent — analytics, not explorers

| Tool | URL | What it is |
|---|---|---|
| **Vestige** | [vestige.fi](https://vestige.fi/) | DeFi and ASA market analytics — pools, prices, volume. **Verified 200** |
| **ASA Stats** | [asastats.com](https://www.asastats.com/) | Portfolio tracking and ASA holdings analytics. **Verified 200** |
| **AlgoScan** | [algoscan.app](https://algoscan.app/) | A **redirect utility** ("Algorand Explorer Redirect"), not an explorer of its own. **Verified 200** |

### Data endpoints — what the explorers (and this module) actually read

| Provider | URL | Notes |
|---|---|---|
| **AlgoNode** | [algonode.io](https://algonode.io/) | Free, **keyless** public algod + indexer. Algorandscout's defaults: `mainnet-api.algonode.cloud` / `mainnet-idx.algonode.cloud` |
| **Nodely** | [nodely.io](https://nodely.io/) | Free and paid tiers; the operator behind AlgoNode's infrastructure. **Verified 200** |
| **algod REST** | [developer.algorand.org/docs/rest-apis/algod](https://developer.algorand.org/docs/rest-apis/algod/) | The node API — knows *now* |
| **indexer REST** | [developer.algorand.org/docs/rest-apis/indexer](https://developer.algorand.org/docs/rest-apis/indexer/) | The archive API — knows *history* |

### Dead — do not link these

Several explorers still cited in blog posts, tutorials and LLM training data are **gone**.
Confirmed **NXDOMAIN** on 2026-08-08:

| Former explorer | Status |
|---|---|
| `algoexplorer.io` (+ `testnet.`/`www.` variants) | **NXDOMAIN.** Was the ecosystem default for years and is still the answer most sources give. It is not there. |
| `app.dappflow.org` | **NXDOMAIN** — superseded by [Lora](https://lora.algokit.io/) |
| `goalseeker.purestake.io` | **NXDOMAIN** — died with PureStake's API business |
| `blockpack.app` · `algorand.observer` · `explorer.algorand.org` | **NXDOMAIN** |
| `nftexplorer.app` | Unreachable from this host (DNS returns an IPv6 record only, no IPv4 answer). Treat as unverified rather than confirmed dead. |
| `algoranking.com` · `algoexplorerapi.io` | Resolve, but serve a **parked / domain-for-sale page** — not Algorand services |

**This is why the doctrine is to verify links rather than recall them.** The
[Algorand blog's own explorer guide](https://algorand.co/blog/algorand-block-explorers) and
several 2025–2026 search results still present AlgoExplorer and Dappflow as current; both are
NXDOMAIN. A published mindX post that cited them would be linking readers into nothing.

---

## See also

- **Repo** — [OpenBDK/algorandscout](https://github.com/openbdk/algorandscout) · [OpenBDK org](https://github.com/openbdk) · [OpenBDK whitepaper](https://github.com/openbdk/whitepaper)
- **mindX** — [EVM-side chain reader](blockscout.md) · [Blockchain Agents](BLOCKCHAIN_AGENTS.md) · [x402 rails](x402_rails.py) · [reference-corpus NAV](NAV.md) · [master NAV](../NAV.md)
- **Algorand explorers** — [Allo](https://allo.info/) · [Pera Explorer](https://explorer.perawallet.app/) · [Lora](https://lora.algokit.io/) · [Bitquery](https://explorer.bitquery.io/algorand) — full landscape incl. dead domains in [§7](#7-the-algorand-explorer-landscape)
- **Algorand** — [developer docs](https://developer.algorand.org/) · [indexer REST API](https://developer.algorand.org/docs/rest-apis/indexer/) · [algod REST API](https://developer.algorand.org/docs/rest-apis/algod/) · [ARC standards](https://github.com/algorandfoundation/ARCs) · [AlgoNode](https://algonode.io/)
- **Licence** — [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) (the BANKON License text) · [NOTICE](https://github.com/openbdk/algorandscout/blob/main/NOTICE)
