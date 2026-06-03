# bankoneth

> **An agnostic, composable module for ENS subname issuance under `bankon.eth`,
> `.eth` 2LD purchase, and subdomain-minting-as-a-service for third-party
> `.eth` holders.**
>
> Not mindX-only. Not PARSEC-only. PARSEC is the canonical first consumer; mindX
> publishes from it; AgenticPlace lists from it; DAIO settles around it; any
> agent framework, wallet, or dApp composes it through the same interface.

`bankoneth` is the **genesis** of the BANKON ENS contract stack. It deploys
every contract necessary to put `bankon.eth` subname issuance into production
across the chains it needs to live on: **Ethereum mainnet** for the
NameWrapper-based registrar + resolver, **0G** for the ERC-7857 iNFT, and
**Algorand** (via the x402-avm facilitator) for the third payment rail.

## Three issuance flows, one UI

| Flow | What it does | Contract |
|---|---|---|
| **A — Subname** | Claim `alice.bankon.eth` and similar | `BankonSubnameRegistrar` |
| **B — `.eth` purchase** | Buy `newdomain.eth` end-to-end through bankoneth (wrapped ENS commit-reveal) | `BankonEthRegistrar` |
| **C — Host an existing `.eth`** | Subdomain-minting-as-a-service: external `.eth` holders enroll, bankoneth issues subnames under their parent | `BankonDomainHosting` |

Every flow pays through one of three rails (ETH / USDC permit / x402-avm
Algorand USDC), optionally wraps the result as a unified ERC-7857 iNFT with a
deterministic ERC-6551 token-bound account, and optionally publishes the
result as a marketplace listing on
[agenticplace.pythai.net](https://agenticplace.pythai.net).

## Quick use

```bash
git clone https://github.com/bankon-eth/bankoneth
cd bankoneth
forge build && forge test
node script/export-abis.mjs                      # regenerate ABIs + manifest for the dApp
cd packages/web && python3 -m http.server 8788   # open http://localhost:8788/bankoneth.html
```

## Canonical iNFT + ARC agent economy (ETHGlobal NYC)

A **modular, extensible** canonical **EIP-7857 + ERC-6551** iNFT stack lives in
[`contracts/inft7857/`](contracts/inft7857/) (interfaces, pluggable verifier, Mode A unified +
Mode B parallel iNFT, mint registrar, lean TBA account + registry proxy, metadata resolver,
CREATE2 deployer). The **ARC agent economy** ([`contracts/arc/`](contracts/arc/) — "Agent
Reputation Collection", copied from `daio/contracts/arc/` and expanded) turns an iNFT into a
tradable, reputation-bearing, escrow-able agent: `bankon_agent_market` + `AgentReputationRegistry`
+ `AgenticMarketplaceEscrow` + `SubscriptionManager` + `BonaFide`. Two new modular UIs ship beside
the simple MVP storefront: [`name-service.html`](packages/web/name-service.html) (ENS naming as a
service + iNFT/TBA) and [`marketspace.html`](packages/web/marketspace.html) (the ARC marketspace).
0G **Aristotle mainnet 16661** is wired. **Quantum posture:** this EVM module is **Tier-A
(crypto-agile / PQ-ready)** per [CP2048-QR](https://github.com/cypherpunk2048) — secp256k1 today, with
the pluggable `IERC7857DataVerifier` (`OracleType{TEE,ZKP}`) as the documented Falcon/ML-DSA swap point;
**never claimed PQ-today**. Genuine quantum-native (Tier-Q) is the Algorand/PARSEC track, not this
submission. See [`QUANTUM_READINESS.md`](docs/QUANTUM_READINESS.md). Docs: [`INFT7857_MODULE`](docs/INFT7857_MODULE.md),
[`ARC_AGENT_ECONOMY`](docs/ARC_AGENT_ECONOMY.md), [`INFT_CANONICAL_VS_LEGACY`](docs/INFT_CANONICAL_VS_LEGACY.md),
[`NAME_SERVICE_UI`](docs/NAME_SERVICE_UI.md). `forge test` **238/238** (+ x402evm **6/6**).

```bash
forge test                                   # 238 green (47 suites); cd x402evm && forge test → 6/6
forge script script/deploy_bankon_inft.s.sol --rpc-url <fork> --broadcast   # deploy the canonical stack
```

## go-LIVE deployer + golden-ratio treasury (ETHGlobal NY)

A **single-page, client-side, WebGL-skinned deployer** — [`packages/web/deploy.html`](packages/web/deploy.html)
— takes the whole stack LIVE with a **two-button DEPLOY → LAUNCH → RETURN** flow. **① DEPLOY** arms the
ordered sequence (reads creation bytecode + ctor ABI from the generated manifest, predicts addresses + gas,
no broadcast); **② LAUNCH** broadcasts each creation tx straight from the wallet, threading each deployed
address into the next constructor + post-deploy wiring; **RETURN** is live explorer feedback (tx hashes,
addresses, confirmations, explorer links, optional verify). **No backend, no API key** — public RPC + your
wallet. LIVE target **Base at parity with Ethereum**; multi-chain picker.

The **cypherpunk2048 financial primitives** ([`contracts/cp2048/`](contracts/cp2048/)) are the golden-ratio
treasury: **golden-ratio BANKON fee** (φ in the digits following the cost — normalized **φ/10 = 16.18%**,
expedited priority tiers up to **3× the cost**); **SCIENTIFIC** token (18+18 precision rail, single-issuance,
immutable beneficiary, `self_purge`→owner); **RAKE** (collects home to `bankon.eth` only when value beats the
chain cost); **bankon_oracle** (price straight from the Uniswap pair); **bankon_autoconvert** (any token →
settlement via Uniswap V3) + **bridge_collect** (LI.FI/GLMR); and **gas-as-a-service**
([`bankon_gas_service`](contracts/cp2048/bankon_gas_service.sol)) — drops **one transaction** of Base gas to
an address arriving with a bridged asset, φ-fee funded. **treasury + remittance**
([`bankon_custody`](contracts/cp2048/bankon_custody.sol)) — safe multi-asset vaults (native/ERC-20/721/1155,
any chain) that redeem **only to the immutable bankon.eth**, with a reconfigurable renounce state machine
(1:1 → 2:2/2:3/3:3 multisig, 3:3-can-instate-1:1, optional permanent lock-out). Treasury / owner / RAKE home = **bankon.eth**
`0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169` (immutable, every chain). Docs:
[`ETHGLOBAL_NY`](docs/ETHGLOBAL_NY.md), [`SCIENTIFIC_AND_RAKE`](docs/SCIENTIFIC_AND_RAKE.md). cp2048 + custody **31/31**.

```bash
node script/export-abis.mjs                  # emit ABIs + bankon.bytecodes.json + deploy sequences
python3 -m http.server -d packages/web 6680  # open /deploy.html → connect on Base → ① DEPLOY → ② LAUNCH
```

## Multichain registry, prices, x402 & MCP

**[`packages/web/bankonchains/`](packages/web/bankonchains/)** — the canonical chain registry (ETH, Base,
Moonbeam/GLMR, Polygon/POL, Arbitrum/ARB, Optimism/OP, Avalanche/AVAX, BNB, Blast, Injective-EVM/INJ, 0G,
Arc/Circle + testnets). `extend.js addChainById(id)` resolves **any** EVM chain from `chainid.network` (the
`allchain.html` source), so the deployer toggle is extensible. **Prices are two-tier:** public visitors get
keyless spot (Coinbase); **holders of `bankon.eth` / `*.bankon.eth`** get **CoinMarketCap** prices via a
server-side proxy (`cmc-proxy.{mjs,php}`). The **CMC API key is server-side only, OUTSIDE the web root**
(gitignored bankoneth-root `.bankonchains.env`) — never shipped to the browser. Privilege via
[`bankon.js`](packages/web/bankon.js).

**[`packages/web/dapp/`](packages/web/dapp/)** — a framework-free web3 dApp prototype: secure-by-default
`index.html` (wallet login → redirect), `dapp.html` (load any contract **by name or address**; RAKE actions;
ENS search → Etherscan inject), per-contract `abis/<name>.abi.js` modules, `admin.html`/`.php`/`.ipfs`. After
go-LIVE the deployer wires live addresses into the dApp (localStorage + a committable `deployments/<id>.json`).

**[`x402evm/`](x402evm/)** — self-contained module (sibling of `pay2play/`, **6/6 tests**) that generalizes
HTTP-402 settlement to **every EVM rail (Base ∥ Arc ∥ …)**: `X402EVMFacilitator` + `X402ChainRegistry`
(EIP-712 receipt, monotonic-nonce + spent-digest guards). Plus `clients/` — the EIP-3009 USDC **x402 payer**
for keyless CoinMarketCap ingestion + a wrapper over the `cmc` Go CLI. Docs:
[`X402_EVM`](docs/blockchain/X402_EVM.md), [`COINMARKETCAP_X402`](docs/operations/COINMARKETCAP_X402.md).

**[`bankonMCP/`](bankonMCP/)** — the AgenticPlace **payment processor** for MCP service delivery (TS, adapted
from `openCMC/x402-mcp-proxy`): proxies MCP tool calls, **auto-pays x402** on the cheapest adaptive rail, and
rakes the **golden φ/10 fee** home to `bankon.eth`. Serves bankon + mindX tools behind x402.

## Hierarchical login (admin / member / visitor)

The product UI is a **server-gated, three-tier** dApp — the single front-end for both
bankon.eth and the **BANKON Vault**:

- **admin** (owns `bankon.eth`) → console: pricing/fees/hosting/registry setters + vault
  (credentials, cabinet, signing). Non-owners **never receive** these pages.
- **member** (holds `*.bankon.eth`) → dashboard: names, records, agent identity.
- **visitor** → storefront: buy a subname, paying **any denomination** (ETH / USDC / x402 /
  bridge from ARC), converted to settle on-chain.

Tiers are resolved **on-chain** (live `NameWrapper.ownerOf`) and enforced by the gate in
[`backend/`](backend/); the BANKON Vault + shadow-overlord auth is fully imported into
[`vault_module/`](vault_module/). See [`docs/TIERED_LOGIN.md`](docs/TIERED_LOGIN.md),
[`docs/BANKON_VAULT.md`](docs/BANKON_VAULT.md), [`docs/PAYMENTS.md`](docs/PAYMENTS.md),
[`docs/ADMIN_ROLES.md`](docs/ADMIN_ROLES.md), [`docs/ETHERSCAN.md`](docs/ETHERSCAN.md).

```bash
export BANKON_GATE_SECRET=$(openssl rand -hex 24)
uvicorn backend.app:app --port 8800        # open http://localhost:8800/
```

## Interactive dApp (developer explorer)

A **self-contained, framework-free** explorer is at
[`packages/web/bankoneth.html`](packages/web/bankoneth.html) — MetaMask login
(EIP-6963, allchain.html-style), guided mint/buy/host/register-agent/resolve
flows, **and** a generic ABI explorer (load any contract → read/write forms).
The ERC-7857 iNFT lives on a separate page,
[`packages/web/inft.html`](packages/web/inft.html) (+ its own `iNFTabi.js`),
because it deploys on 0G. No build step to run — see
[`docs/DAPP.md`](docs/DAPP.md). For parsec-wallet, use the native
[`@bankoneth/parsec-view`](packages/parsec-view/) (the Lit `parsec-adapter` is
superseded). The Lit `@bankoneth/ui` components + `tauri-app` remain for
embedded/desktop use (`pnpm --filter @bankoneth/tauri-app dev`).

For integration patterns see [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).
For the architecture, see [`BANKONETH.md`](BANKONETH.md). For deployment, see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Layout

```
contracts/         Solidity (Foundry) — canonical source
  cp2048/            golden-ratio treasury: φ fee, SCIENTIFIC, RAKE, oracle, autoconvert, bridge_collect, gas_service
  inft7857/  arc/    canonical EIP-7857 iNFT + ERC-6551 stack · ARC agent economy
script/            DeployEthereum + DeployZeroG + WireCrossChain + export-abis.mjs (ABIs + bytecodes + deploy sequences)
test/              Foundry test suite (Flow A × B × C × payment rails × cp2048 × custody) — 238 green
deployments/       per-chain address records ({1,11155111,local}.json) loaded by the dApp
clients/python/    async Python client (subdomain_issuer.py, agent_mint_service.py) — moved from openagents/ens/
pay2play/          self-contained x402 pay-to-play module (Arc settlement → entitlement)
x402evm/           self-contained x402 EVM settlement module (Base/Arc/… facilitator) + CMC x402 ingestion
bankonMCP/         MCP × x402 adaptive-rails proxy (AgenticPlace processor; TS, needs pnpm install)
.bankonchains.env  CMC API key — GITIGNORED, outside the web root (loaded by the cmc proxies)
packages/          pnpm workspace
  web/               self-contained dApp — prototype, no build:
                       deploy.html (go-LIVE two-button deployer) + deploy.js + deploy-feedback.js
                       dapp/ (web3 prototype: index/dapp/admin + per-contract abis/<name>.abi.js)
                       bankonchains/ (chain registry + chainid.network extend + CMC price proxy) + bankon.js
                       bankoneth.html + inft.html + iNFTabi.js + name-service/marketspace
  parsec-view/       @bankoneth/parsec-view — native parsec-wallet view (TS, production)
  react/             @bankoneth/react — <BankonDeploy/> React component (TSX, production)
  core/              @bankoneth/core — pure viem v2 client
  ui/                @bankoneth/ui — Lit 3 Web Components
  cli/               @bankoneth/cli — bankoneth-cli
  parsec-adapter/    @bankoneth/parsec-adapter — Lit component (SUPERSEDED by parsec-view)
  tauri-app/         reference desktop (Tauri 2 + Vite + Lit)
integrations/
  mindx/             mindX agent tool wrapper
  parsec/            PARSEC integration notes
examples/
  claim-alice/       reproducible "claim alice.bankon.eth" snippet
  local-anvil/       full E2E driver against local anvil
docs/                ARCHITECTURE, DAPP, IDENTITY_AAS, CONSOLIDATION, DEPLOYMENT, INTEGRATIONS, …
  design/            re-homed ENS design docs (BANKON_ARCHITECTURE, BANKON_ENS) — moved from openagents/docs/ens/
  specs/             canonical ENS subname registrar specs (.md + .pdf) — what bankoneth implements
```

## License

Apache-2.0 — see [`LICENSE`](LICENSE).

## Status

PROTOTYPE / pre-mainnet. No deployment yet. The contracts compile and the
test suite passes against forked mainnet ENS. Production deploy is an
operator-gated follow-up requiring Treasury Safe signing + post-deploy
address-reference verification.
