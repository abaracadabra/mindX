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
pnpm install && pnpm -r build
pnpm --filter @bankoneth/tauri-app dev  # reference desktop dApp
```

For integration patterns see [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).
For the architecture, see [`BANKONETH.md`](BANKONETH.md). For deployment, see
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Layout

```
contracts/         Solidity (Foundry) — canonical source
script/            DeployEthereum + DeployZeroG + WireCrossChain
test/              Foundry test suite (Flow A × B × C × payment rails)
packages/          pnpm workspace
  core/              @bankoneth/core — pure viem v2 client
  ui/                @bankoneth/ui — Lit 3 Web Components
  cli/               @bankoneth/cli — bankoneth-cli
  parsec-adapter/    @bankoneth/parsec-adapter — PARSEC wallet component
  tauri-app/         reference desktop (Tauri 2 + Vite + Lit)
integrations/
  mindx/             mindX agent tool wrapper
  parsec/            PARSEC integration notes (code in packages/parsec-adapter)
examples/
  claim-alice/       reproducible "claim alice.bankon.eth" snippet
  local-anvil/       full E2E driver against local anvil
docs/                ARCHITECTURE, DEPLOYMENT, INTEGRATIONS, DAIO_HANDOFF, ADDR_REFERENCE
  specs/             canonical ENS subname registrar specs (.md + .pdf) — what bankoneth implements
```

## License

Apache-2.0 — see [`LICENSE`](LICENSE).

## Status

PROTOTYPE / pre-mainnet. No deployment yet. The contracts compile and the
test suite passes against forked mainnet ENS. Production deploy is an
operator-gated follow-up requiring Treasury Safe signing + post-deploy
address-reference verification.
