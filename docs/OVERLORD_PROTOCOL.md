# The OVERLORD Protocol

The mindX realm access protocol — a clean-room web3 signature gate (no external
dependency; the sovereignty doctrine). JWT is client-held and presented by
`Authorization: Bearer` or `?t=` — **no cookies**. Audited + locked down 2026-07-02
(Day 0).

## Two sovereign apexes — separate chains, equivalent, non-crossing

| | OVERLORD | OVERSEER |
|---|---|---|
| identity | **bankon.eth** | **mindx.algo** |
| chain | `.eth` / EVM | `.algo` / Algorand |
| nature | **pure cypherpunk2048** — immutable root, **does NOT proxy** | governs `.algo`; **MAY proxy** |
| reserved | **LORD of the REALM**: creates/owns the REALM, includes/excludes any participant (incl. the OVERSEER) | agent reputation via **BONA FIDE** + clawback |
| role | the **deployer** (deploys from `~/DeltaVerse` → iNFT + contracts) | community governance, moderation, editing, `.algo` domain issuance |
| login | `/auth/evm` or `/realm/verify` → EIP-191 → overlord-session JWT | `/auth/algorand` → Ed25519 → OVERSEER JWT |

They are **equivalent per-chain sovereigns** — each grants/revokes privilege on
its own chain; neither governs the other's. `.algo` adopts `.evm`, never the
reverse. The OVERSEER creates a **shadow-overlord** proxy that wields all of the
OVERLORD's operational powers *by proxy* — **except** the LORD-of-REALM reserved
privileges, which are never proxied. **Case convention: lowercase = a proxy,
UPPERCASE = the apex.**

## Tier ladder (`hierarchy.py`, ranked by `hierarchy.rank`)

`public → participant → paid → agent → member → model → overseer → overlord`

- **participant** — any wallet that signs the challenge (proves control). Reads docs.
- **member** — holds the membership token: a `*.bankon.eth` subname / EVM BonaFide on
  `.eth`, **or BONA FIDE (Algorand ASA) on `.algo`**. Reads the book.
- **overseer** — mindx.algo. **overlord** — bankon.eth.

## BONA FIDE — `.algo` reputation (mint = grant, clawback = revoke)

Holding **BONA FIDE** IS privilege. The OVERSEER mints it to grant and claws it
back to revoke. **NO TOKEN FOUND = ACCESS DENIED** — membership is never granted on
an absent/unverifiable token (fail-closed). Ships as an Algorand ASA
(`BonaFideDeployer` + `BonafideController`, clawback) and an EVM ERC-20
(`BonaFide.sol`). Balance check: `mindx_backend_service/bona_fide.py` (indexer read,
no algosdk). **Anticipated config** (Day 0 — activates on the OVERSEER's deploy):

    MINDX_BONAFIDE_ASA_ID        Algorand ASA id (int)
    MINDX_BONAFIDE_EVM_ADDRESS   EVM BonaFide ERC-20 address
    MINDX_ALGO_INDEXER_URL       Algorand indexer (default: public algonode)

## The gate + redirect

`main_service._tier_gate(request, min_tier, html_from)` resolves the tier from
**both** the EVM overlord-session (`_viewer_role`) **and** the Algorand OVERSEER JWT
(`overseer_auth.verify_overseer_jwt`), ranks it on `hierarchy.rank`, and allows when
`rank(role) >= rank(min_tier)`. On insufficient tier it serves **one harmonized
ACCESS DENIED page** (doorway portal + CONNECT (EVM) + separate `.algo` OVERSEER
path; no wallet → MetaMask; ACCESS DENIED flips to GRANTED on recognition). The same
page is served by `_tier_gate`, `_reference_gate`, and the strict arrival middleware —
so every gated HTML path (incl. `/agents/judgedread.agent`) shows it, never a bare
`/login`. Fail-open only on a rare import fault (docs never hard-lock).

**Gated:** `/docs.html`, `/doc/*`, `/automindx` → participant; `/book` → member.
**Public:** `/doc/THESIS`, `/doc/MANIFESTO`. The landing OVERLORD panel renders only
with a verified bankon.eth signature.

## Endpoints

- `GET /realm/challenge?address=` · `POST /realm/verify` — EVM tier session (participant/member/overlord).
- `GET /auth/evm/challenge` · `POST /auth/evm/verify` — OVERLORD (bankon.eth) admin login.
- `GET /auth/algorand/challenge` · `POST /auth/algorand/verify` — OVERSEER (mindx.algo, Pera/PARSEC) login.
- `/overseer` — the OVERSEER surface (Algorand deploy suites; PARSEC `parsec_signBytes` identity gate).

## Deploy order (surfaced to the OVERLORD post-login)

SCIENTIFIC first-light → **Algorand BONA FIDE proof-of-work** (A1–A4; unlocks EVM) →
EVM E1–E7 (settlement → registries → iNFT → payment infra → x402 + ENS → THOT → DAIO)
→ devolution. Source: `~/DeltaVerse/docs/PRODUCTION_DEPLOY_ORDER.md`. Mainnet is
OVERLORD-signed only (agents never sign real-chain).

### Deploy feedback loop
The handoff is a LIVE sequence, not a static plan. After the OVERLORD/OVERSEER signs
each step, the result is recorded: `POST /realm/deploy/feedback` (sovereign-gated —
overlord-session or OVERSEER JWT) stores `{step, contract, chain, tx_hash, address,
asa_id, status}` to an append-only ledger + a `deploy.feedback` catalogue event
(mindX improvement awareness). `GET /insight/deploy/feedback` surfaces it, and the
`/activity` OVERLORD deploy card renders plan + confirmed-on-chain results with
explorer tx links. BONA FIDE activation: the OVERSEER deploys `BonaFideDeployer` →
`mintBonafideAsa`, then `scripts/activate_bonafide.sh <ASA_ID> <net>` wires the real
ASA id into the running gate (fail-closed until then).
