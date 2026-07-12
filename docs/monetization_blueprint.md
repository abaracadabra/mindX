# 💸 Monetization Blueprint v2
### mindX Augmentic Intelligence: the rails that exist, the tokens that back them, and the order they switch on

> **v2 (2026-07-12)** — supersedes the v1 aspirational blueprint (SaaS DevOps,
> SwaaS bounties, "Codebase Predator", AI-VC, S.M.A.I.R.T. presale). v1 was
> written before any rail existed; v2 is written the week the contracts deploy.
> The old avenues survive only where they earned a place in the Horizon section.
> Presale framing is **retired** — the token model follows the canonical
> [mindx_strategy.md](mindx_strategy.md) doctrine (soulbound-royalty EVM +
> BONA FIDE reputation on Algorand, Marshall Islands DAO LLC wrapper).

---

## Core thesis

**mindX is a knowledge-delivery service with HTTP-native settlement.**

Modules migrate out of mindX and stand alone (bankon, AgenticPlace, DeltaVerse);
what remains *is* the product: a self-improving system whose knowledge, cognition,
and agency are metered at the endpoint. Monetization is not a product launch —
it is switching on rails that are already built:

1. **x402** — every cost-center endpoint can demand stablecoin settlement per call.
2. **Recognition** — a covenant-signed ladder that converts visitors into
   token-holding members (the acquisition funnel).
3. **iNFT** — mindX agents minted as ERC-7857 intelligent NFTs (the product
   with a deed).

## The constellation — who plays what

The economy runs across three PYTHAI surfaces, each with one job:

| Surface | Role | What it does in the economy |
|---|---|---|
| **[bankon.pythai.net](https://bankon.pythai.net)** | **The identity layer** | Identity and value. Client-side wallet creation (keys born in the participant's browser, never held by anyone else), the BANKON vault, tiered recognition (OVERLORD `.eth` / OVERSEER `.algo` — privilege from verified holdings, not assignment). Every minted iNFT agent **binds to BANKON** for its identity; every airdrop, settlement, and treasury flow resolves to a BANKON-recognized address. Nothing is sold here — this is where *who you are* is established. |
| **[agenticplace.pythai.net](https://agenticplace.pythai.net)** | **The marketspace** | Where agents are listed, discovered, and traded. Minted ERC-7857 iNFT agents (with their six sidecar facets) list here; the landing-page BUILDER funnel hands off here; extensions and agent capabilities are catalogued here. This is where *what you own* meets *what others want*. |
| **[mindx.pythai.net](https://mindx.pythai.net)** | **The mind** | The knowledge-delivery service itself: cognition, the reference corpus, publishing, deployment — every priced surface, settled via x402. This is where *what the system knows and does* is metered. |

Identity (bankon) → asset (iNFT) → market (agenticplace) → service revenue
(mindx) is one continuous rail: you cannot list what you have not minted, you
cannot mint what is not bound to an identity, and everything settles back to
the treasury the identity layer anchors.

---

## The live stack (what exists today)

### x402 paywall — LIVE on production
`mindx_backend_service/x402_middleware.py` + `data/config/x402_pricing.json`
(hot-reloadable). Per-endpoint prices in microUSDC; per-wallet free quota
(10 calls/24h, anonymous 0). Rails configured on prod: **Base → the bankon.eth
treasury** (`0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169`), Algorand
mainnet/testnet via Parsec. Priced surfaces include `/coordinator/*` (LLM
calls), `/agents/{id}/evolve` (full directive loop), `/boardroom/convene`
(7-agent deliberation), `/permaweb/upload` (permanent Arweave storage desk).
Contract: [services/x402_as_a_service.md](services/x402_as_a_service.md).

### Recognition ladder + airdrop — LIVE, settling on mainnet deploy
`data/config/recognition.json` — visitor → covenant signature (CP2048-OVL-1,
keys created in the participant's browser and never held by mindX) →
**0.111 BKPY** airdrop → member. Queue settles by wallet-to-wallet transfer
from bankon.eth (never a mint, never limited by trade caps), once per address.
**BONA FIDE is never airdropped** — reputation is earned on Algorand through
its own process.

### The backing contracts — Anvil-verified, mainnet imminent
- **BKPY (BANKON PYTHAI)** — zero-import ERC-20, fixed repunit supply
  **111,111.111111111111111111** minted to bankon.eth at construction.
  DEX-only trade caps (1000 BKPY max buy/sell) that are **increase-only** —
  no lever exists to lower them or freeze trading; wallet-to-wallet transfers
  are never limited. Misdirected assets are OVERLORD-rescuable. First pair:
  wBTC on Uniswap.
- **THlNK (MINDX)** — ERC-7857 iNFT carrying a **THOT**: mindX's memory
  lineage (every gitmind incremental backup chains into the THlNK).
Both deployed + verified on Anvil 31337 (2026-07-11) by the DeltaVerse
deployer; mainnet awaits the OVERLORD's signed ceremony. `recognition.json`
carries per-chain address maps — mainnet go-live is **config-only**.

### iNFT agent minting — BUILT, dormant behind one config file
[Blockchain Agents](blockchain/BLOCKCHAIN_AGENTS.md): mint a mindX agent as an
ERC-7857 iNFT with six sidecar facets, bind its identity to
**bankon.pythai.net** (the identity layer), list it on
**agenticplace.pythai.net** (the marketspace), register on the ERC-8004
AgentRegistry (`POST /blockchain/agentfactory/mint`). The landing-page
BUILDER funnel (7 archetypes → `/inft` prefill → AgenticPlace handoff)
activates by filling `data/config/agenticplace_deployments.json` — zero code
change.

### Knowledge delivery — the `/reference` corpus
The gated reference corpus already carries an x402 pay-to-read seam
(`/reference/file` settles or 402s). Pricing knowledge per read is the purest
expression of the thesis: the corpus is ingest-only for mindX's own retrieval,
and *paid* for outside eyes. (The DeltaVerse WISDOM model — POSIX-style paid-group
file privilege — is the recommended shape.)

### Adjacent built rails
Publishing-frequency-as-a-service (x402 seam on the AuthorAgent schedule),
Contract-Deployment-as-a-Service (`agents/deployer/`, intent → confirm gate),
pay2play (Foundry router/registry/entitlement — **needs completion**, the one
unfinished rail).

---

## The funnel

```
visitor ──(sign covenant)──▶ recognized participant ──(0.111 BKPY airdrop)──▶ member
   │                                                                            │
   └── public docs, feedback.txt, dashboards (free surface)                     ▼
                                              x402-paying user of cognition, knowledge,
                                              minting, deployment, publishing services
```

Every public surface is marketing for the ladder; every rung of the ladder is
onboarding for the rails. The airdrop is not a giveaway — it is the moment a
participant acquires the means of settlement.

The funnel crosses the constellation in order: identity is established on
**bankon.pythai.net** (covenant keys, recognition tier), assets are minted and
listed on **agenticplace.pythai.net**, and services are consumed — and settled
— on **mindx.pythai.net**.

---

## Activation sequence

**Deploy day (OVERLORD ceremony):**
1. Deploy BKPY + THlNK/THOT to mainnet with the redeployed artifacts
   (capped, rescuable, Uniswap-ready); record real chain-ID addresses in
   `recognition.json`; verify on the explorer.
2. Flush the airdrop queue (wallet-to-wallet from bankon.eth).
3. Register the wBTC pair; seed *small* liquidity within the 1000-BKPY caps —
   symbolic depth first, deepen on demand (the one-VPS economics doctrine).
4. Smoke-test the rescue path with dust before announcing.

**Week one — flip the dormant rails (all config-gated):**
5. Fill `agenticplace_deployments.json` → BUILDER iNFT minting live.
6. Configure x402 pay-to-read on `/reference` — knowledge delivery becomes revenue.
7. Complete pay2play and wire it to the now-real BKPY.
8. Fix the tempo rail's zero-address `payTo` (configure or remove).

**Month one — close the economic feedback loop:**
9. Revenue ledger: x402 settlements + airdrop spend + mint fees → catalogue
   events → `/insight/economy` — and fold net revenue into the
   [objective self-eval](AUTONOMOUS.md) verdict, so the Gödel loop feels money
   the way it feels campaign success.
10. Marshall Islands DAO LLC wrapper before volume ([mindx_strategy.md](mindx_strategy.md)).
11. AuthorAgent milestone article; llms.txt updated.

---

## Measurement — honest, or it doesn't count

The v1 blueprint promised margins with no meter. v2's rule: **no revenue claim
without a ledger event behind it.** Success gates, in order:

1. First settled x402 payment (non-zero, on-chain, catalogued).
2. Monthly settled revenue ≥ the VPS bill (operational self-funding — the
   [economics doctrine](NAV.md#economics)'s actual bar).
3. Revenue trend folded into the self-eval verdict and visible on
   `/insight/economy`.

Anything beyond that is Horizon, not forecast.

---

## Horizon (kept from v1, demoted to earned-later)

- **Autonomous DevOps / codebase modernization / SwaaS** — real avenues, but
  they need the delivery + escrow rails (x402 + pay2play + deployer) proven
  on micro-transactions first. The swarm exists; the billing now does too.
- **Agent-as-a-Service** — the iNFT mint *is* this avenue's on-chain form:
  a personalized agent with a deed, listed on AgenticPlace.
- **FinancialMind / venture intelligence** — deferred until the treasury has
  ledgered revenue to manage. Managing money precedes multiplying it.
- **Retired:** "Codebase Predator" (adversarial free-analysis-then-compete —
  incompatible with the covenant posture) and the S.M.A.I.R.T. presale
  (superseded by the soulbound-royalty + BONA FIDE doctrine; no presale).

---

## Guardrails

- **Budget:** one Hostinger VPS/month; cost/benefit governs all compute.
- **BONA FIDE is never airdropped.** Reputation is earned, clawback-contained.
- **The gated corpus never touches the permaweb.** Permanence is promised only
  to what is meant to be permanently public.
- **No securities framing.** Utility settlement + reputation, per doctrine.
- **Keys are the participant's alone.** mindX stores addresses, never key material.

*Operative sequencing lives in [roadmap.md](roadmap.md) Phase III. The vision
lineage this supersedes is preserved in [autonomousROADMAP.md](autonomousROADMAP.md).*
