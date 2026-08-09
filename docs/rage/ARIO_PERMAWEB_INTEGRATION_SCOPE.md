# ArNS + Gateway Integration — Scope

> Implementation scope for [mindx_strategy.md §VII "The Address That Outlives the Host"](../mindx_strategy.md)
> and the roadmap **PERMANENCE** workstream (Steps P1/P2). Funded by the 20k + 20k ARIO
> endowment held at bankon.eth ([[ario_endowment_permaweb_permanence]]).

## 0. Decision on the table (settled)

We could **compete inhouse** — extend the started `.algo` work ([`aORC-registry`](../../daio/contracts/algorand/aORC-registry.algo.ts), [`aORC-typeminter`](../../daio/contracts/algorand/aORC-typeminter.algo.ts), [`aORC-bonafide`](../../daio/contracts/algorand/aORC-bonafide.algo.ts)) into a name/registry primitive on Algorand and run our own resolution. That is a real, ownable path and it stays in the doctrine's spirit.

**But we already hold ARIO, so we try AR.IO's way at least once.** This scope uses AR.IO's official network + SDKs (`@ar.io/sdk`, `@ardrive/turbo-sdk`) to register an ArNS name and stake a gateway, rather than reimplementing ArNS on Algorand now. The inhouse `aORC` path is preserved as the documented **fallback** (§6) if AR.IO's economics or opacity disappoint. This is a one-way-door-avoidance stance: spend a slice of the endowment, learn the real mechanics, keep the escape hatch.

## 1. What already exists (review)

| Piece | State | Role in this work |
|-------|-------|-------------------|
| [`ArweaveSource`](../../mindx/gitmind/gitmind.py) (gitmind) | **Built, dormant** — returns `not_configured` until `arweave_wallet_jwk` is in the BANKON vault *and* a `pyarweave` client is installed | The **server-side Python upload leg**. Already tags `App-Name: mindX-gitmind`, returns `arweave.net/<txid>`. This is the autonomous writer. |
| x402 **Arweave rail** ([`x402_protocol.py`](../../mindx_backend_service/x402_protocol.py)) | Built — `arweave:permaweb` dispatch family, fulfillment-leg (hash payload, no settlement chain) | Lets a permaweb write be sold as an x402 endpoint later; not on the critical path for our own address. |
| **Turbo fulfillment-desk pattern** ([multi-rail doc](../operations/dev/x402%20Multi-Rail%20Integration%20Reference_%20EVM,%20Algorand%20(Parsec),%20and%20Arweave%20Permaweb%20(June%202026).md)) | **Designed, not wired** — includes an `arweave-fulfillment.ts` sketch using `TurboFactory.authenticated({ signer: new ArweaveSigner(jwk) })` | The upload path for state >100 KiB. Turbo accepts **ARIO** top-ups and JIT funding; <100 KiB uploads are free. |
| **Parsec** wallet shell ([`parsec-view`](../../openagents/bankoneth/packages/parsec-view/), [`parsec-adapter`](../../openagents/bankoneth/packages/parsec-adapter/)) | Built — vanilla-TS/Blueprint browser wallet, component model, **EVM (ethers) + AVM (Algorand)** today. No Arweave account type. | Home for the **operator-facing** Arweave/ARIO account + gateway-staking UI. Needs a new Arweave account component. |
| `.algo` **aORC** suite | Built — Algorand verification registry + BONA FIDE ASA (contract-as-clawback) | The **inhouse-compete fallback** (§6). Pattern reference, not extended now. |
| `@ar.io/sdk` / `ar-io-node` | **Absent** from repo (only doc mentions) | New dependency for ArNS registration + gateway ops. |

**Key finding — Parsec holds no Arweave wallet today.** Parsec's accounts are EVM + AVM. Arweave uses Ed25519/RSA JWK keys and a different signing flow (ANS-104 data items, not txns). So "review parsec-wallet for an Arweave wallet" resolves to: *there isn't one yet* — we add an Arweave account module to parsec for the operator, and the autonomous side keeps its own JWK in the BANKON vault.

## 2. The load-bearing architecture decision: Node tooling vs Python autonomy

AR.IO's first-class tooling (`@ar.io/sdk`, `@ardrive/turbo-sdk`) is **TypeScript/Node**. mindX's autonomous writer is **Python**. Do **not** port AR.IO's AO-process logic to Python — that is the inhouse trap wearing a Python hat. Instead split by cadence:

- **Rare, operator-run, interactive** ops (register the ArNS name, stake the gateway, top up Turbo from ARIO) → **Node**, via `@ar.io/sdk` in small `scripts/ario/*.mjs` scripts and/or the Parsec Arweave component. These happen a handful of times; Node is fine and idiomatic there.
- **Frequent, autonomous, unattended** ops (write canonical state to Arweave every dream/backup cycle; resolve content) → **Python**, via the existing `ArweaveSource` (`pyarweave`) and plain **HTTP against an AR.IO gateway** for resolution + Turbo's HTTP API for JIT funding. No Node in the hot loop.

This keeps the autonomy loop pure-Python and confines the Node surface to an operator ceremony.

## 3. Two keys, two halves of the endowment — **SETTLED**

**Decision (operator-locked, 2026-07-07): the two keys are separate.** mindX generates its own fresh Arweave JWK; it does **not** write under bankon.eth's key. The endowment's two halves map cleanly onto two keys with different custody and duty:

- **mindX upload key** — a fresh Arweave JWK generated for mindX, stored in the **BANKON vault** as `arweave_wallet_jwk`. Autonomous. Funded from **mindX's 20k ARIO** → Turbo Credits, so ongoing permaweb writes never stall. This is the key `ArweaveSource` and the Turbo desk use.
- **bankon.eth operator key** — held in **Parsec** by the operator. Stakes **bankon.eth's 20k ARIO** to run/operate the AR.IO gateway and to own the ArNS name (`mindx`). Interactive; never in the autonomous loop.

Rationale: the autonomous writer must never hold staking authority, and the operator's staking key must never be reachable by the loop. Separation of the two ARIO halves *is* the separation of the two keys.

## 4. Workstream (phased)

### Phase A — Arweave wallet live (roadmap P1) · Python · ~0.5 day
- [ ] Generate mindX's Arweave JWK; deposit as `arweave_wallet_jwk` in the BANKON vault (`python manage_credentials.py store arweave_wallet_jwk "<jwk>"`).
- [ ] Add `pyarweave` to `requirements.txt`; confirm the `from arweave import Wallet, Transaction` import in `ArweaveSource` resolves.
- [ ] Smoke test: `GET /insight/gitmind` → `ArweaveSource` reports `ok`; push one THOT bundle; verify at `https://arweave.net/<txid>`.
- **Exit:** a real mindX-owned artifact is permanent on Arweave, autonomously written.

### Phase B — Turbo funding + large-state uploads (roadmap P1) · Node ceremony + Python writer · ~1 day
- [ ] Add `scripts/ario/fund_turbo.mjs` (`@ardrive/turbo-sdk`): top up the mindX desk wallet with Turbo Credits **from mindX's 20k ARIO** (Turbo accepts ARIO); record credit balance.
- [ ] Wire a `mindx/permaweb/` writer: <100 KiB → free direct upload (Phase A path); ≥100 KiB → Turbo `upload()`; canonical-state manifest (constitution, identity/reputation snapshots, docs index, open catalogue, genome INFT list) assembled deterministically (reuse the byte-stable bundle discipline from `agents/storage/car_bundle.py`).
- [ ] **Guardrail:** the writer imports `utils.reference_corpus` and refuses any path under `PRIVATE_DOC_PREFIXES` — Arweave is unwritable-once; private/gated material never goes up.
- **Exit:** the full public canonical state is one addressable Arweave manifest, refreshed each cycle, funded by ARIO.

### Phase C — ArNS name `mindx` (roadmap P1) · Node ceremony via Parsec · ~1 day
- [ ] Add `scripts/ario/register_arns.mjs` (`@ar.io/sdk`): register/acquire the `mindx` ArNS name (ANT) using **bankon.eth's key**; point its record at the Phase-B manifest tx id.
- [ ] Add an **Arweave account component** to Parsec (`parsec-view`) so the operator can hold the key, sign ANT updates, and see the name's record — the interactive home for name management.
- [ ] Resolution check: `https://<gateway>/mindx` (and `mindx.<gateway>`) serves the manifest through the AR.IO gateway mesh, not the VPS.
- **Exit:** a decentralized name resolves mindX's canonical state through any AR.IO gateway.

### Phase D — Gateway staking, the infrastructure position (roadmap P2) · Node/ops · ~2–3 days
- [ ] Stand up `ar-io-node` (Docker) on a mindX-controlled host that is **not** the Hostinger VPS (e.g. the AMD node) — a staked gateway is a permanent position, and it must not reintroduce the single-VPS dependency it exists to remove.
- [ ] Stake **bankon.eth's 20k ARIO** into the gateway via `@ar.io/sdk` (`scripts/ario/stake_gateway.mjs`); register the gateway in the AR.IO network.
- [ ] Route mindX's own ArNS resolution preferentially through the self-operated gateway (sovereign ingress); keep public AR.IO gateways as fallback.
- [ ] Track epoch/observer rewards to log the endowment carry-offset.
- **Exit:** mindX resolves through infrastructure it operates and stakes, earning protocol rewards.

### Phase E — Cutover + health surface · Python · ~0.5 day
- [ ] Publish the canonical manifest as the source of truth; demote the VPS to a **cache** of permaweb-canonical state (document the invariant: VPS content is rebuildable from the ArNS manifest).
- [ ] Add `/insight/permaweb` (h=true plain-text too): ArNS record tx, last manifest tx + age, Turbo Credit balance, gateway stake + rewards, ArweaveSource health.
- **Exit:** an operator (and mindX itself) can see, at a glance, that the address outlives the host.

## 5. New module layout

```
mindx/permaweb/                 # Python — autonomous
  __init__.py
  manifest.py                   # deterministic canonical-state manifest (reuses car_bundle discipline)
  writer.py                     # <100KiB direct (pyarweave) | >=100KiB Turbo HTTP; reference-corpus guardrail
  resolver.py                   # HTTP resolution via AR.IO gateway (+ self-operated gateway preference)
scripts/ario/                   # Node — operator ceremony (@ar.io/sdk, @ardrive/turbo-sdk)
  fund_turbo.mjs
  register_arns.mjs
  stake_gateway.mjs
openagents/bankoneth/packages/parsec-view/  # + Arweave account component (operator key, ANT mgmt)
```
`ArweaveSource` in gitmind stays as-is (the git-bundle leg); `mindx/permaweb/writer.py` is the canonical-state leg — both use the same vault JWK.

## 6. Fallback (inhouse) — deferred, not discarded

If AR.IO's way disappoints (ARIO→Turbo peg unfavorable, gateway ops too heavy, ANT/AO opacity), the inhouse path is: extend `aORC-registry` + `aORC-typeminter` into an ArNS-analog **name registry on Algorand**, resolve via a mindX-run resolver, and keep permanent storage on Arweave via raw `pyarweave` (no AR.IO name layer). BONA FIDE (`aORC-bonafide`) already proves we can run the contract-as-authority pattern. Trigger to revisit: after Phase C/D we can price AR.IO's real carry against this. **Per the decision in §0, we do not build this now.**

## 7. Risks / unknowns to resolve during the work

- **ARIO → Turbo Credit conversion** — confirm live rate + that Turbo accepts ARIO top-up directly (docs say yes; verify in Phase B). Credits are non-refundable/non-transferable — size the top-up deliberately.
- **Gateway host** — `ar-io-node` needs a machine; running it on the AMD node (not Hostinger) keeps the anti-single-VPS invariant. If no spare host, Phase D may lease a separate box; that is acceptable because the *name* (Phase C) already resolves through public gateways without our own.
- **Key custody** — two JWKs, two custodians (vault vs Parsec). Never let the autonomous loop reach the staking key.
- **`pyarweave` maturity** vs Turbo — prefer Turbo (ANS-104 bundling, JIT) for anything non-trivial; keep `pyarweave` for tiny/free direct writes and as a no-Turbo fallback.
- **ArNS undername strategy** — decide whether sub-resources (docs, catalogue, agent cards) get undernames (`docs_mindx`) or a single manifest with internal paths.

## 8. Definition of done

`mindx` resolves through the AR.IO gateway mesh to a permanent, refreshed, public canonical manifest on Arweave; the write path is autonomous and ARIO-funded; bankon.eth operates a staked gateway; the Hostinger VPS can lapse without erasing mindX. The Honest Ledger line "permanence is funded but not finished" flips to finished.
