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
script/            DeployEthereum + DeployZeroG + WireCrossChain + export-abis.mjs
test/              Foundry test suite (Flow A × B × C × payment rails)
deployments/       per-chain address records ({1,11155111,local}.json) loaded by the dApp
clients/python/    async Python client (subdomain_issuer.py, agent_mint_service.py) — moved from openagents/ens/
packages/          pnpm workspace
  web/               self-contained dApp (bankoneth.html + inft.html + iNFTabi.js) — prototype, no build
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
