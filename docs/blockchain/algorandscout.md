# Algorandscout — reading Algorand through a Blockscout-shaped API

> **What this is:** [`OpenBDK/algorandscout`](https://github.com/openbdk/algorandscout) — a
> standalone, **BANKON-licensed** read service that serves [Algorand](https://algorand.co/)
> through a [Blockscout](https://github.com/blockscout/blockscout)-compatible REST surface,
> without pretending Algorand is an EVM chain.
>
> **Built 2026-08-08.** Version 0.1.0 · 12 `/api/v2` routes + native passthrough · 86 tests
> passing offline against fixtures captured live from Algorand mainnet · all endpoints
> verified end-to-end against mainnet.
>
> **Why mindX cares:** it closes the exact hole named in
> [blockscout.md §7](blockscout.md#7-chain-coverage--what-mindx-can-and-cannot-see) — Blockscout
> is EVM-only, and mindX's governance identity lives on Algorand.
>
> **Part of the [gated reference corpus](NAV.md)** — ingest-only, never published to `/docs.html`.

---

## 1. The gap this fills

[`docs/blockchain/blockscout.md`](blockscout.md) documents mindX's independent on-chain reader
and states its boundary plainly: **Blockscout is EVM-only.** All 17 of its chain types
(`ethereum`, `arbitrum`, `optimism`, `arc`, `zilliqa`, `zksync`, …) are EVM, because the core
schema assumes 20-byte addresses, gas, nonces, indexed log topics, and reorgs.

Algorand has none of those, and mindX has real state there:

- **`mindx.algo`** — the OVERSEER identity, Ed25519 → JWT (see the OVERSEER Algorand login path)
- **BONA FIDE** — the reputation-as-privilege layer that governs the DAIO hierarchy
- **[Parsec](https://parsec.pythai.net)** — the AVM wallet surface, and the
  [x402 v2 multi-rail](x402_rails.py) Parsec AVM rail
- ASA-denominated instruments in the [measurement-token](../mindx_strategy.md) stack

Every one of those was unreadable by the Blockscout path, and the honest instruction in
blockscout.md was *"never let a Blockscout-shaped answer imply coverage it does not have."*
Algorandscout is the other half: the same *shape* of answer, sourced from Algorand's own
[algod](https://developer.algorand.org/docs/rest-apis/algod/) and
[indexer](https://developer.algorand.org/docs/rest-apis/indexer/) APIs, with the mismatches
declared rather than papered over.

---

## 2. Why it is a separate service, not a Blockscout chain type

Two independent reasons, either one decisive.

### 2.1 Blockscout's licence forbids the merged build

Blockscout **re-licensed on 2026-04-22**. It is no longer GPL and no longer open source —
SPDX [`LicenseRef-Blockscout`](https://github.com/blockscout/blockscout/blob/master/LICENSE).
Clause 5 governs Derivative Works:

| Clause | Effect on a merged-in module |
|---|---|
| **5(a)** | Derivative Works permitted **solely for internal use** |
| **5(b)** | **No distribution** of Derivative Works to any third party without a Commercial Licence — publishing to a public repo *is* distribution |
| **5(c)** | Author grants Blockscout Limited a **perpetual, irrevocable, sublicensable** licence over any Derivative Work |
| **7(c)** | The Software "as a whole, and all parts thereof" is under their licence — contradicting a BANKON licence on a merged module |
| **4(a)** | No commercial, hosted, or monetised use without a Commercial Licence |

The same licence supplies the exit, in its own definition:

> *"For the avoidance of doubt, Derivative Works do not include works that remain **separable
> from**, or **merely link to**, the Software."*

Algorandscout is such a separable work: **separate repo, separate process, no Blockscout
source, no Blockscout dependency** — compatible response *shape* only. Interface compatibility
is not derivation. That is what makes the BANKON licence on it real rather than decorative, and
it is why `NOTICE` in that repo forbids ever merging it into a Blockscout tree.

> Engineering rationale, not legal advice. Anyone deploying Blockscout itself remains
> independently subject to its attribution (2c) and commercial-use (4a) terms.

### 2.2 Algorand does not fit the EVM schema

| EVM assumption | Algorand reality |
|---|---|
| 20-byte hex address | 58-character base32 Ed25519 |
| gas market | flat fee + fixed opcode budget — compute is not purchased |
| per-account nonce | first-valid/last-valid round window + genesis hash |
| logs with indexed topics | ordered array of **opaque** byte strings — nothing to filter on |
| reorgs, uncles | final on write |
| ERC-20 `approve`/`allowance` | ASA with **clawback**, freeze, manager, reserve roles |

That last row is the dangerous one. An ASA rendered as an ERC-20 hides that **clawback can move
a holder's balance without the holder signing.** Forcing Algorand into the EVM tables would
produce a schema of plausible-looking nulls plus one genuine misrepresentation of consent.

---

## 3. The surface

### Blockscout-shaped — `/api/v2/*`

| Route | Returns |
|---|---|
| `GET /api/v2/capabilities` | **Start here.** Machine-readable statement of what the chain cannot answer, and why |
| `GET /api/v2/stats` | Chain tip, indexer lag, block time, `is_evm: false` |
| `GET /api/v2/blocks` · `/blocks/{round}` | Rounds; `?include_transactions=` off by default |
| `GET /api/v2/transactions/{txid}` | One transaction, inner transactions recursed |
| `GET /api/v2/addresses/{address}` | Account: native balance, rekey target, counters; `?live=` reads the node |
| `GET /api/v2/addresses/{address}/transactions` | History; `after_time`/`before_time` (RFC-3339), `tx_type`, `asset_id` |
| `GET /api/v2/addresses/{address}/token-balances` | ASA holdings, metadata resolved by default |
| `GET /api/v2/tokens/{asset_id}` · `/holders` | ASA params, the four privileged roles, holder page |
| `GET /api/v2/smart-contracts/{app_id}` | Application: AVM programs, state schema, decoded global state |
| `GET /api/v2/search?q=` | Resolves by shape: address · txid · asset/app id · unit-name candidates |
| `GET /algorand/v2/*` | **Allowlisted** native indexer passthrough (allowlist, not prefix-match — never an open proxy) |
| `GET /health` | Both upstreams + how far the archive trails the node |

### The two rules that bite

1. **Holdings live on two surfaces.** `/addresses/{a}` carries the ALGO balance;
   `/addresses/{a}/token-balances` carries the ASAs. Neither subsumes the other — the same
   completeness fork [blockscout.md](blockscout.md#9-working-rules--the-short-list) warns about
   on EVM chains.
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

Retry policy matches the rule Blockscout publishes for its own upstreams: **5xx retried 3×,
4xx never.**

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
- **mindX** — [Blockscout (EVM side)](blockscout.md) · [Blockchain Agents](BLOCKCHAIN_AGENTS.md) · [x402 rails](x402_rails.py) · [reference-corpus NAV](NAV.md) · [master NAV](../NAV.md)
- **Algorand explorers** — [Allo](https://allo.info/) · [Pera Explorer](https://explorer.perawallet.app/) · [Lora](https://lora.algokit.io/) · [Bitquery](https://explorer.bitquery.io/algorand) — full landscape incl. dead domains in [§7](#7-the-algorand-explorer-landscape)
- **Algorand** — [developer docs](https://developer.algorand.org/) · [indexer REST API](https://developer.algorand.org/docs/rest-apis/indexer/) · [algod REST API](https://developer.algorand.org/docs/rest-apis/algod/) · [ARC standards](https://github.com/algorandfoundation/ARCs) · [AlgoNode](https://algonode.io/)
- **Licence** — [Blockscout Software Licence](https://github.com/blockscout/blockscout/blob/master/LICENSE) · [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) (the BANKON licence text)
