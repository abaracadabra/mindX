# dato — a DAIO-owned data-DAO + permanence-naming suite

> A **separate modular extension for consideration as inclusion**. Nothing here is
> wired into the live DAIO or running services until a governance proposal opts it
> in (see [INTEGRATION.md](INTEGRATION.md)). The suite runs and tests standalone.

A **dato** is a *data controller* the DAIO spawns and owns. It holds data at a
**permanence tier**, carries a **tiered name**, records the **spawning participant/
client wallet**, and admits members via a **request-to-join** flow that takes a
**fee + settings**. It is modeled on the
[AO DAO pattern](https://cookbook_ao.arweave.net/tutorials/begin/dao.html)
(spawn → configure → join → govern → commit).

## Permanence spectrum

| Tier | Meaning | Proof |
|------|---------|-------|
| **immortal** | permanent ANS-104 Arweave upload — the **~200-year data-integrity guarantee**; never changes | Arweave tx id |
| **immutable** | content `sha256` is hash-locked + anchored (recorded on `DatoCore`/ledger); bytes not Arweave-stored; re-commit with different bytes is rejected | `anchor:<sha256>` |
| **mutable** | editable bytes kept in dato state; version bumps on update | none |

## Tiered, extensible naming

Names are **`<handle>.<tier>.<root>`** — the middle label is the permanence tier, so
the name *declares* its permanence (e.g. `archive.immortal.blockchain`). Roots are
extensible: `blockchain` ships enabled; the DAIO owner can `add_root("eth")`,
`add_root("ar")`, … so the namespace grows without code/contract changes.

## Three substrates, one concept (unified by the Python SDK)

- **Python orchestrator** (`dato/core/`) — the canonical, runnable implementation (the AO lifecycle as methods). Persists to `dato/data/dato_registry.json`.
- **AO Lua process** (`dato/ao/dato.lua` + `spawn.py`) — the cookbook-faithful process; `spawn.py` is dry-run-safe when no AO toolchain is present. **Real-AO deploy** (spawn `dato.lua` as a live AO process, signed by a parsec wallet): see [`dato/ao/DEPLOY.md`](ao/DEPLOY.md) → `~/parsec/parsec-wallet/scripts/deploy-dato-ao.ts`.
- **EVM contracts** (`dato/contracts/`) — `DatoCore` (owner = DAIO), `DatoNamingRegistry` (tiered/extensible), `DatoMembership` (join-with-fee). Zero-import Solidity 0.8.24; **built + tested, not deployed**.
- **UI** (`dato/ui/`) — a zero-build, parsec-wallet-ready UI for dato **naming · data · commerce · deploy** (plain ESM JS, parsec view idiom). ar.io ARNS names surface as a **purchase** with handoff to parsec's ario flow; the commerce view does **request-to-join with an x402 fee**; the deploy view **hands the dato contracts to the DeltaVerse OVERLORD deployer** and binds on-chain. Standalone (`python -m http.server` in `dato/ui`) or include via `registerDatoViews()`. See [`dato/ui/README.md`](ui/README.md).
- **CLI** (`dato/cli.py`) — headless **agentic commerce**: spawn / join-with-x402-fee / commit / name / ls, JSON output for agents. See below.

## Quickstart (Python)

```python
from dato.core.dato_process import DatoRegistry
from dato.core.model import Settings, PermanenceTier
from dato.core import membership

reg = DatoRegistry()                                   # state in dato/data/ (gitignored)
dato = reg.spawn("archive", tier="immortal",           # DAIO owns it; deployer wallet recorded
                 deployer_wallet="0x…", owner_daio="daio",
                 settings=Settings(default_tier=PermanenceTier.IMMORTAL, join_fee_microusd=10000))

membership.join(reg, dato.dato_id, "0x…member",        # request-to-join (fee enforced via x402 /dato/join)
                fee_tx="0x…receipt", fee_paid_microusd=10000, settings={"role": "reader"})

rec = reg.commit(dato.dato_id, "doc1", b"…bytes…", tier="immortal")   # → Arweave tx id (200-yr)
```

## Reuse (does not reinvent)
- immortal uploads → `tools/arweave_turbo.py` (`ArweaveTurboDesk`).
- join-fee settlement → the existing x402 rails (`/dato/join` in `data/config/x402_pricing.json`).
- participant wallet → `agents/core/id_manager_agent.py` / session recognition.
- naming/spawn/fee patterns → `daio/contracts/{ens/v1/BankonSubnameRegistrar, daio/governance/DAIO_BranchManager, daio/treasury/TreasuryFeeCollector}`.

## Tests
```bash
python -m pytest dato/tests -v          # Python suite
cd dato/contracts && forge test         # EVM suite (8 tests)
```

## CLI — agentic commerce

`dato/cli.py` lets an autonomous agent transact the full dato lifecycle headlessly,
with `--json` output. The join fee is settled over **x402** (the agent mints a
signed EIP-3009 payment authorization via `tools/x402_rails`), and `immortal`
commits perform a real ANS-104 Arweave upload via `tools/arweave_turbo`.

```bash
# spawn a DAIO-owned dato with a paid membership (10000 µUSD = $0.01)
python -m dato.cli spawn guild --tier immutable --join-fee 10000 --wallet 0xAgent --json
python -m dato.cli quote <dato_id>
# request-to-join, settling the fee over x402 (agentic commerce):
python -m dato.cli join <dato_id> --wallet 0xMember --pay --rail base
#   (--simulate records a receipt when no signing key is configured)
# commit data at a permanence tier (immortal → real Arweave upload):
python -m dato.cli commit <dato_id> report --tier immutable --data "…"
python -m dato.cli name vault --tier immortal --root ar     # ARNS → purchase notice
python -m dato.cli ls --json
```

Wallet/keys: x402 signing uses `BASE_X402_PRIVATE_KEY` / the BANKON vault
(`base_x402_private_key`); Arweave (immortal) uses `ARWEAVE_JWK` / `ARWEAVE_JWK_PATH`
/ vault. State persists to `$DATO_REGISTRY` (default `dato/data/dato_registry.json`, gitignored).

## Deploy the EVM contracts (DeltaVerse OVERLORD deployer)

The dato contracts are a registered suite (`dato`) in DeltaVerse `deploy/suites.json`
(`DatoCore → DatoNamingRegistry → DatoMembership`, DatoCore owned by the DAIO). The
`dato-deploy` UI view hands off to the deployer (`pages/deploy.html`). **On deploy-to-live,
a per-chain on-chain-verification store is written** to `DeltaVerse/live/verify/<ChainName>/<Contract>/`
— exact `.sol` source + complete `abi.json` + Solidity `standard-input.json` + `deployment.json`
(address, compiler, optimizer) — ready for Etherscan / `forge verify-contract`. Generated by
`DeltaVerse/scripts/verify-bundle.mjs` (auto-run by `deploy-stack-anvil.mjs`; or
`node scripts/verify-bundle.mjs --prepare --suite dato --chain Base` to pre-stage).

## Deploy `dato.lua` to a real AO process

`dato.lua` deploys to a live AO process **signed by a parsec wallet** (the modular
wallet option). See [`dato/ao/DEPLOY.md`](ao/DEPLOY.md):

```bash
cd ~/parsec/parsec-wallet && node_modules/.bin/tsx scripts/deploy-dato-ao.ts
```

The pipeline (parsec wallet derivation → ANS-104 signing → `On-Boot` bundling of
`dato.lua` → aoconnect spawn) is verified; supports `AO_MODE=legacy|mainnet`. The
spawned process id lands in `dato/data/ao_process.json`. As of 2026-06-17 the
legacynet MU is returning a server-side 500 on spawn (endpoint-side, reproduced
with a bare spawn) — rerun when it recovers or target a HyperBEAM mainnet node
(`AO_MODE=mainnet AO_URL=…`). Full status in DEPLOY.md.
