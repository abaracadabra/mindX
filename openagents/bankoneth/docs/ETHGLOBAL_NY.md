# BANKON · ETHGlobal New York 2026 — submission

**Universal, open-source, client-side connection rails for sovereign agents.**

> An agent gets a **name** (`agent.bankon.eth` ENS subname) → a **wallet** (ERC-6551 TBA) → an
> **intelligence** (canonical ERC-7857 iNFT) → **earns/pays** in any token on any chain (Uniswap
> auto-convert + Circle/Arc USDC + LI.FI/GLMR bridge) → a golden-ratio **BANKON fee** rakes **home** to
> `bankon.eth` → it **lands ready** on Base via gas-as-a-service → every connection holds **its own
> client-side keypair**. 100% open source, framework-free, self-custodial, no backend, no API key.

## The Continuity-Track feature we shipped: a go-LIVE deployer

The headline artifact is a **single-page, client-side contract deployer** (`packages/web/deploy.html`) with a
**two-button DEPLOY → LAUNCH → RETURN** flow:

1. **① DEPLOY (arm)** — pick a chain + a deploy set; the page reads creation bytecode + constructor ABI from
   a generated manifest, predicts each contract's address (`getCreateAddress`) and gas, and shows the ordered
   sequence. *No broadcast.*
2. **② LAUNCH (confirm)** — broadcasts each creation tx straight from the user's wallet, **threading each
   deployed address into the next constructor**, then runs post-deploy wiring (`setMinter`, …).
3. **RETURN** — live explorer feedback from the target chain: tx hashes, deployed addresses, gas used,
   confirmations, clickable explorer links (basescan/etherscan/arcscan/blockscout), optional source-verify.

Pure client-side: no backend, **no API key required** (public RPC + the wallet). The deployer *is* the thesis
— sovereign rails you run yourself.

## Sponsor qualification map

| Sponsor | What we ship | Where |
|---|---|---|
| **ENS** | `agent.bankon.eth` subname registrar + naming-as-a-service + ENS-as-agent-identity; owner resolved live via ENS | `contracts/inft7857/`, `name-service.html`, deployer owner-resolution |
| **Arc / Circle** | USDC-native settlement on Arc (5042002); chain-abstracted USDC (CCTP domains in `chains.js`); USDC economy in ARC set | `chains.js`, `contracts/arc/`, `backend/x402.py` |
| **Ledger** | Client-side hardware signing — every deploy/pay tx is signed in the user's wallet (Ledger via the EIP-6963 provider); x402 agent payments | `deploy.js` connect path, `contracts/x402/` |
| **Uniswap (Stack Contribution)** | `bankon_autoconvert` reuses the Uniswap V3 SwapRouter to convert any token → settlement, open source | `contracts/cp2048/bankon_autoconvert.sol` |

## The financial primitives (cypherpunk2048 standard, `contracts/cp2048/`)

- **Golden-ratio BANKON fee** — φ in the digits following the cost. Normalized **φ/10 = 16.18%**; expedited
  priority climbs by golden steps, **capped at 3× the contract cost**.
- **SCIENTIFIC token** — 18+18 precision rail; single-issuance; immutable beneficiary; owner-renounce;
  `self_purge` only-to-owner.
- **RAKE** — collects home to `bankon.eth` only when value beats the chain cost (pair-priced).
- **bankon_oracle** — USD value straight from the Uniswap pair.
- **bankon_autoconvert / bridge_collect** — any token → settlement (Uniswap V3) / LI.FI-GLMR cross-chain,
  golden fee → RAKE.
- **Gas-as-a-service** (`bankon_gas_service`, Base) — drops **one transaction** of gas (live `basefee × units`)
  to an address arriving with a bridged asset; plus custom client-paid buy. **9+ / golden-fee verified.**

**Treasury / owner / RAKE home = `bankon.eth` = `0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169`** (verified via
Blockscout + Etherscan ENS), immutable across every contract and chain.

## Architecture

```
                 ┌──────────── deploy.html (client-side, no backend/key) ────────────┐
                 │   ① DEPLOY (arm: predict addr+gas)   ②  LAUNCH (broadcast seq)    │
   wallet  ──────┤   reads bankon.bytecodes.json + abis/*  →  eth_sendTransaction      │
 (Ledger/MM)     │   threads deployed addr → next ctor → wire() → RETURN (explorer)   │
                 └───────────────────────────────┬───────────────────────────────────┘
                                                 ▼  livenet (Base ∥ Ethereum ∥ Arc …)
  identity:  agent.bankon.eth (ENS) → ERC-6551 TBA → ERC-7857 iNFT  ── inft7857/
  economy:   pay any token → bankon_autoconvert (Uniswap V3) ┐
             pay any chain → bridge_collect (LI.FI/GLMR)      ├─ φ fee ─► RAKE ─► bankon.eth
             land on Base  → bankon_gas_service (one-tx drop) ┘            (only when value > cost)
```

## Demo flow (one connect)

connect (client-side / Ledger) → claim `agent.bankon.eth` → mint iNFT + TBA → DEPLOY+LAUNCH the treasury set
live on **Base** → pay in any token (auto-convert, φ fee) → bridge from Ethereum, **land with one tx of Base
gas** → fee rakes home to `bankon.eth` → list on the ARC marketspace.

## Run it

```bash
forge build && forge test                      # contracts (cp2048 21/21 + iNFT + ARC)
node script/export-abis.mjs                     # emit ABIs + bankon.bytecodes.json + deploy sequences
python3 -m http.server -d packages/web 6680     # serve the dApp; open /deploy.html
```
Connect a wallet on **Base**, pick **Treasury (cp2048)**, **① DEPLOY** → **② LAUNCH**. Capture the TxIDs.

## On-chain proof (fill after go-LIVE)

| Contract | Chain | Address | Tx |
|---|---|---|---|
| scientific_token | Base | `0x…` | `0x…` |
| rake | Base | `0x…` | `0x…` |
| bankon_oracle | Base | `0x…` | `0x…` |
| bankon_autoconvert | Base | `0x…` | `0x…` |
| bankon_gas_service | Base | `0x…` | `0x…` |

(Repeat on Ethereum for parity; optionally Arc testnet for the Circle prize.)

## Quantum posture (honest)

This EVM submission is **CP2048-QR Tier-A** — *crypto-agile / post-quantum-**upgrade-ready***, **never
PQ-today**. secp256k1 signing is classical; the PQC swap seam is the pluggable `IERC7857DataVerifier`
(`OracleType{TEE,ZKP}`). Genuine Tier-Q (Falcon, client-side per-connection keys) lives on the **Algorand /
PARSEC** track — *not* here. No PQ-washing. See `docs/QUANTUM_READINESS.md`.

## Open source

Apache-2.0. Every contract, the deployer, the manifest generator, the financial primitives, and the
cypherpunk2048 standard are public and auditable — the rails are sovereign because you can read and run them.
