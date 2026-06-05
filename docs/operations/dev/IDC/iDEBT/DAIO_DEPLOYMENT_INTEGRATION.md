# DAIO Blockchain Deployment & Integration Spec

**Scope:** Close the last gap in the AgenticPlace ↔ mindX ↔ BANKON triad by deploying the DAIO on-chain.
**Targets:** Polygon mainnet (EVM governance) + Algorand mainnet (Dojo reputation, x402 payments).
**Toolchain:** Foundry (EVM test + deploy), AlgoKit/algopy (Algorand), parsec + parsec-wallet (x402), allchain.html (chain registry oracle).

---

## 1. Architecture at a glance

```
                    ┌─────────────────────────┐
                    │  agenticplace.pythai.net│  ← marketplace UI, allchain.html (2500+ EVM)
                    └───────────┬─────────────┘
                                │  x402 402-gated calls
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    mindx.pythai.net (API)                    │
│  /agenticplace/*  /boardroom/*  /dojo/*  /governance/*       │
│  /vault/*         /bankon/*     /users/*                     │
└───────┬────────────────────┬─────────────────────┬──────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌────────────────┐    ┌──────────────────┐
│ BANKON Vault │     │   Polygon      │    │    Algorand      │
│  (off-chain) │     │   Mainnet      │    │    Mainnet       │
│  AES-256-GCM │     │                │    │                  │
│              │     │ Senatus.sol    │    │  $BANKON ASA     │
│              │     │ Censura.sol    │    │  BONAFIDE ASA    │
│              │     │ Fides.sol      │    │  (clawback=Fides)│
│              │     │ Tessera.sol    │    │  x402 Facilitator│
│              │     │ ChainOracle.sol│    │                  │
│              │     │ (allchain mirror)                       │
└──────────────┘     └────────────────┘    └──────────────────┘
                         ▲
                         │ Chainlink + authorized reporter
                         │ (feeds allchain IDs/RPCs)
                   bankon.pythai.net (wallet + payment UI)
```

**Split rationale**
- **EVM side (Polygon):** rich Solidity + OpenZeppelin tooling, Foundry dev loop, existing mindX ID Manager is Ethereum-compatible, and `allchain.html` is EVM-native (2500+ chains).
- **Algorand side:** ASA **clawback** is the exact primitive Dojo needs ("containment without kill switch" — per `DAIO.md`). x402 micropayments at sub-cent fees + 3.3s finality make per-call gating viable.

---

## 2. On-chain contract set

### 2.1 Polygon (Solidity / Foundry)

| Contract | Purpose | Notes |
|---|---|---|
| `Genius.sol` | Root authority, owns other contracts | UUPS upgradeable, multisig owner |
| `BonaToken.sol` | ERC20 governance token ($BANKON mirror) | Pegged 1:1 to Algorand $BANKON ASA via bridge attestation |
| `Senatus.sol` | On-chain Boardroom — mirrors `/boardroom/convene` | Stores session hash, 7-soldier votes, 0.666 threshold |
| `Censura.sol` | CEOAgent circuit breaker registry | Records the "5 BDI failures → open" state on-chain |
| `Fides.sol` | Bridge attester — verifies Algorand Dojo reputation proofs | Algorand state proofs → EVM |
| `SponsioPactum.sol` | Agent staking / slashing | Stake $BANKON to register an AgenticPlace agent |
| `Tabularium.sol` | Immutable Gödel-journal commitment | SHA-256 roots of improvement-journal entries |
| `Tessera.sol` | ERC-8004 agent identity registry | Agent DIDs, links to AlgoIDNFT on Algorand |
| `ChainOracle.sol` | Mirror of `allchain.html` chain registry | Pull-based: keeper pushes (chainId, rpcHash, status) |

All nine follow the Latin/Roman naming from BONAFIDE. Foundry is already listed as the toolchain in `DAIO.md`.

### 2.2 Algorand (algopy / TEAL)

| Asset / Contract | Purpose |
|---|---|
| `$BANKON` ASA | Native economic unit; total supply fixed; reserve = Genius-owned vault address |
| `BONAFIDE` ASA | Reputation token, **clawback = Fides app address**. Dojo rank = balance tier |
| `Dojo.algo` (app) | Ranks, privilege escalation, writes reputation deltas → clawback moves |
| `x402Facilitator.algo` | Implements x402 settlement per parsec spec (see §4) |
| `AlgoIDNFT.algo` | Soulbound W3C-DID-compliant identity (per existing BANKON spec) |

---

## 3. mindX wiring (API deltas)

Three new route groups. All additive — no existing endpoint changes.

```
POST  /daio/deploy/polygon            # Foundry-driven deploy from CEOAgent
POST  /daio/deploy/algorand           # AlgoKit deploy
GET   /daio/contracts                 # addresses on every connected chain
POST  /daio/boardroom/commit          # push a /boardroom/sessions result on-chain to Senatus
POST  /daio/dojo/clawback             # sign + submit BONAFIDE clawback from /dojo/reputation update
GET   /daio/chain-oracle/{chainId}    # read-through to ChainOracle.sol / allchain.html
POST  /x402/settle                    # parsec-wallet callback target
GET   /x402/quote/{endpoint}          # price in microAlgos / $BANKON for a given API call
```

The `CEOAgent` becomes the signer. Its existing circuit-breaker (open after 5 BDI failures) gets a shadow record on `Censura.sol` so that when the EVM-side vote fires, external observers can verify why execution was paused.

---

## 4. x402 via parsec on Algorand

Wire parsec-wallet as the browser-side facilitator, parsec's x402 middleware as the server-side enforcer.

**Flow for a paid AgenticPlace agent call:**

1. Client hits `POST /agenticplace/agent/call` with no payment header
2. mindX returns **`402 Payment Required`** with a `X-PAYMENT-ALGO` header:
   ```
   X-PAYMENT-ALGO: {
     "scheme": "algorand-asa",
     "asset": "$BANKON",
     "amount": "1000000",
     "recipient": "<x402Facilitator.algo>",
     "nonce": "<uuid>",
     "resource": "/agenticplace/agent/call#<agent_id>",
     "expires": 1765000000
   }
   ```
3. parsec-wallet signs an atomic group (payment + app-call to `x402Facilitator.algo`), submits
4. Client retries with `X-PAYMENT-PROOF: <txid>`
5. mindX middleware verifies via Algod indexer → serves the call
6. Facilitator emits an event consumed by the **Dojo.algo** reputation updater: successful paid calls = +reputation; charge-backs = clawback

Gating policy:
- Endpoints under `/agenticplace/*` and `/inference/multi-stream` → paid (per-call quote)
- Governance endpoints (`/boardroom/*`, `/governance/*`) → paid at higher tier + SponsioPactum stake check
- Read-only endpoints (`/dojo/standings`, `/health`, `/inference/status`) → free

---

## 5. Chain mapping: allchain.html → ChainOracle.sol

`allchain.html` is the human-readable face of a 2500+ entry registry. On-chain we keep a **curated subset** (chains mindX agents actually transact on) rather than mirror the full set — gas cost.

Pipeline:
```
allchain.html JSON feed  ──►  mindX keeper  ──►  ChainOracle.sol.push(chainId, rpcUrl, status)
                              │
                              └── parsec-wallet reads the same feed for client-side MetaMask add
```

Keeper cadence: hourly, diff-only commits. The `CEOAgent` has write authority; `Censura.sol` can pause the keeper if the CEO breaker is open.

---

## 6. Foundry test plan

Project layout (recommend a fresh repo `openBDK-daio` under the LAIR3-BDK org):

```
daio-contracts/
├── foundry.toml
├── src/
│   ├── Genius.sol
│   ├── BonaToken.sol
│   ├── Senatus.sol
│   ├── Censura.sol
│   ├── Fides.sol
│   ├── SponsioPactum.sol
│   ├── Tabularium.sol
│   ├── Tessera.sol
│   └── ChainOracle.sol
├── test/
│   ├── Senatus.t.sol              # 7-soldier vote, 0.666 threshold, CISO/CRO 1.2x veto
│   ├── Censura.t.sol              # 5-failure breaker, recovery path
│   ├── Fides.t.sol                # Algorand state-proof verification (mock)
│   ├── SponsioPactum.t.sol        # stake/slash, min-stake by agent tier
│   ├── ChainOracle.t.sol          # keeper writes, stale-read guards
│   └── Integration.t.sol          # full governance cycle: Senatus → Censura → Fides → clawback event
├── script/
│   ├── DeployPolygon.s.sol
│   └── VerifyAll.s.sol
└── lib/
    └── openzeppelin-contracts/
```

**Invariants to fuzz (forge-invariant):**
- `Senatus`: supermajority threshold is never bypassable; CISO/CRO 1.2x weight preserved across arbitrary voter permutations
- `Censura`: breaker cannot be closed without multisig co-sign (fixes the known "permanently non-functional" issue in `CEO.md`)
- `SponsioPactum`: total slashed ≤ total staked at all times
- `ChainOracle`: chainId uniqueness; no downgrade from mainnet→testnet without timelock

**Coverage target:** ≥ 95% line, ≥ 90% branch before mainnet.

**Fork tests:** `forge test --fork-url $POLYGON_RPC` against mainnet state to sanity-check OpenZeppelin upgrades path.

---

## 7. Deployment sequence

Executed from CEOAgent via `/daio/deploy/polygon` and `/daio/deploy/algorand`. Recommended order:

1. **Algorand first** (cheaper, faster finality, the clawback primitive anchors everything):
   - Mint $BANKON ASA (reserve → Genius multisig)
   - Mint BONAFIDE ASA with `clawback = <Fides app addr>` — the address is pre-computed since TEAL apps have deterministic addresses
   - Deploy `Dojo.algo`, `AlgoIDNFT.algo`, `x402Facilitator.algo`
   - Seed initial reputation for the 7 soldiers + CEOAgent from existing Postgres `/dojo/standings`

2. **Polygon mainnet:**
   - `forge script DeployPolygon --broadcast --verify`
   - Deploy order: `Genius` → `BonaToken` → `Tessera` → `Tabularium` → `SponsioPactum` → `Senatus` → `Censura` → `Fides` → `ChainOracle`
   - Transfer ownership of all eight to `Genius`
   - `Fides.setAlgorandBridge(<indexer endpoint>, <state proof verifier addr>)`

3. **mindX config:**
   - Write deployed addresses to `data/config/daio_contracts.json`
   - Restart CEOAgent; it will pick up new contract ABIs from `daio/contracts/`
   - Flip the `DAIO_ONCHAIN=true` feature flag

4. **Smoke test on mainnet:**
   - Convene a no-op boardroom session → `/daio/boardroom/commit` → verify Senatus event
   - Trigger one reputation delta → verify BONAFIDE clawback txn on Algorand
   - Run one `x402`-gated agent call end-to-end via parsec-wallet

---

## 8. Risk / open items

| Risk | Mitigation |
|---|---|
| Algorand → Polygon state proof verifier is non-trivial | Start with a trusted relayer (Fides authorized reporter) for v1; swap to full state proofs in v2 |
| x402 spec is still maturing | Pin to parsec's current spec version in a single middleware module so upgrades are one-file changes |
| CEOAgent circuit breaker deadlock (known issue, `CEO.md`) | `Censura.sol` adds multisig-closable breaker — *fixes* the off-chain bug by making on-chain recovery authoritative |
| allchain.html 2500+ chains → gas cost if mirrored naively | ChainOracle stores only chains with > 0 agent activity (~50-100 realistically); rest stay off-chain in allchain |
| $BANKON peg between Algorand ASA and Polygon ERC20 | One-way mint-burn bridge via Fides, rate-limited; no automated market making in v1 |

---

## 9. What ships when

- **Week 1-2:** Foundry repo scaffolded, all 9 contracts compile, unit tests ≥ 80%
- **Week 3:** Invariant fuzzing, fork tests, internal audit pass
- **Week 4:** Algorand contracts on testnet, Polygon contracts on Amoy
- **Week 5:** End-to-end x402 flow working on testnets against mindx.pythai.net staging
- **Week 6:** Mainnet deployment (Algorand first, then Polygon), CEOAgent cuts over, feature flag on

Aligns with the 24-week DeltaVerse roadmap: DAIO on-chain = weeks 17-22 in that plan, which this spec covers.
