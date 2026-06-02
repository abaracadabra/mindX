# marketinga.agent — marketing capabilities on the CEO + Seven Soldiers boardroom

The marketing Counsellor is not a parallel cabinet. It is the **existing** CEO + Seven Soldiers boardroom (`daio/governance/boardroom.py:Boardroom`) with each soldier carrying a marketing-specific skill. A campaign brief becomes a boardroom directive; each soldier votes; soldiers whose vote was `approve` AND who own a marketing skill execute that skill; per-soldier outputs assemble into the campaign envelope; the CEO signs the `MarketingAttributionReceipt` post-consensus, with the `BoardroomSession` id now an indexed on-chain field.

This is HBR's "layered system of specialized agents" thesis instantiated on the boardroom we already operate.

## The cabinet IS the boardroom

```
                              CEO (brief composer + post-consensus signer)
                                            │
              ┌─────────┬─────────┬─────────┼─────────┬─────────┬─────────┐
            CPO       CTO       COO       CFO       CISO       CLO       CRO
          (1.0)     (1.0)     (1.0)     (1.0)    (1.2 veto) (0.8)   (1.2 veto)
            │         │         │         │         │         │         │
         content   experiment dist'n   reporting  voice      regs     spend
          (HBR1)   (HBR2)    (HBR3)    (HBR4)     gate     gate      gate
```

| Soldier | Weight | Marketing skill | Skill module |
|---|---|---|---|
| CEO | n/a | Brief composition + consensus signer | `agents/marketing/skills/ceo.py` |
| CPO Product | 1.0 | HBR L1 — content drafting | `agents/marketing/skills/cpo.py` |
| CTO Technology | 1.0 | HBR L2 — experimentation | `agents/marketing/skills/cto.py` |
| COO Operations | 1.0 | HBR L3 — distribution | `agents/marketing/skills/coo.py` |
| CFO Finance | 1.0 | HBR L4 — reporting + treasury | `agents/marketing/skills/cfo.py` |
| CISO Security | 1.2× **veto** | Identity gate + voice violation scan | `agents/marketing/skills/ciso.py` |
| CLO Legal | 0.8 | Regulatory + competitor neutrality | `agents/marketing/skills/clo.py` |
| CRO Risk | 1.2× **veto** | Spend risk + hard-stop | `agents/marketing/skills/cro.py` |

`agents/marketing/skills/registry.py` is the single source of truth for `soldier_id → skill instance`. It is tested directly in `tests/test_marketing_skill_registry.py`.

## Brand code

Every cycle reads from `data/brand_code/`:
- `voice.md` — references `docs/MANIFESTO.md` + `docs/THESIS.md`
- `positioning/pillars.md` — six pillars; the sixth (`code_as_dojo`) is reserved for the human Convener
- `positioning/icp_segments.md` — five concentric audience rings (E reserved for human)
- `forbidden_terms.json` — token-shill ban list (regex compiled with `re.IGNORECASE`)
- `competitor_map.json` — neutral-comparison rules per competitor
- `regulatory_constraints.md` — what marketinga.agent must NOT promise
- `onboarding/{ceo,cpo,cto,coo,cfo,ciso,clo,cro}.marketing.md` — Joseph Fuller HBR job descriptions, one per soldier role

## Boardroom session lifecycle

```
1. CEO composes CampaignBrief + formats boardroom directive
2. Boardroom.convene(directive, members="ceo,cpo,cto,coo,cfo,ciso,clo,cro")
   ↓ each soldier votes (pure inference; no tools)
3. CISO veto check: if ciso_security.vote == "reject" → REFUSE
4. CRO veto check:  if cro_risk.vote == "reject"     → REFUSE
5. Overall outcome check: if session.outcome != "approved" → REFUSE
6. For each soldier with vote == "approve" AND a registered skill, in DISPATCH_ORDER:
     a. ciso_security  — identity + voice scan        (defense in depth)
     b. clo_legal      — regulatory + competitor
     c. cpo_product    — content draft (HBR L1)
     d. cto_technology — variants + holdouts (HBR L2)
     e. coo_operations — distribution (HBR L3)
     f. cfo_finance    — GEO probe + KPI snapshot (HBR L4) + treasury read
     g. cro_risk       — holdout integrity + spend hard-stop
   Each skill emits one `marketing.soldier_skill_executed` catalogue event.
   Each executing soldier gets ONE Tessera credential (per-soldier provenance).
7. CEO assembles CampaignEnvelope (with boardroom_session_id) and signs the
   MarketingAttributionReceipt — emits the `marketing.campaign_executed` event.
```

CISO and CRO carry **hard veto**: a `vote == "reject"` from either short-circuits regardless of weighted score. CLO has no hard veto — its `reject` only blocks the campaign if the weighted score also falls below supermajority.

## Three-receipt model

A campaign produces three on-chain receipt types — see [`MARKETING_RECEIPTS.md`](MARKETING_RECEIPTS.md) for the full explainer. Briefly:

| Receipt | Layer | Per |
|---|---|---|
| `Tessera.sol` | identity | per soldier action |
| `X402Receipt.sol` | payment | per paid call |
| `MarketingAttributionReceipt.sol` | attribution | per campaign envelope (now keyed by `boardroomSessionId`) |

Plus `MarketingTreasury.sol` for the 99% revenue → BANKON SATOSHI buyback/burn rule.

## Backend surface

```
GET /marketing/status                       # 8-row soldier ↔ skill table
GET /marketing/campaigns                    # recent decisions from catalogue
GET /marketing/brand_code                   # current loaded brand-code (read-only)
GET /marketing/geo                          # last GEO probe rollup
GET /marketing/identity                     # on-chain identity binding status
GET /marketing/session/{boardroom_id}       # join BoardroomSession with the receipt + skill outputs
```

Every endpoint accepts `?h=true` for plain-text rendering via `mindx_backend_service.text_render`.

## Configuration

`data/config/marketinga.toml` — inotify-watched. Notable thresholds:
- `governance.spend_threshold_usd` — Boardroom routing flag ($500)
- `risks.hard_stop_spend_usd` — kill switch ($5,000)
- `reporting.geo_weekly_budget_usd` — GEO probe spend cap ($20)
- `experimentation.holdout_rate` — measurement holdout (10%)

## On-chain identity binding

Phase 1 ships in dry-run mode: 8 ENS subnames (`ceo.bankon.eth`, `cpo.bankon.eth`, …, `cro.bankon.eth`) are unregistered until the operator runs:

```bash
python -m agents.marketing.onchain.bind_identity --execute
```

This binds:
1. Tessera credentials for each agent (CEO + 7 soldiers).
2. ENS subnames under `bankon.eth`.
3. AgentRegistry (ERC-8004) registrations with capability bitmaps.
4. iNFT_7857 mints — one per soldier seat.

The `MarketingAttributionReceipt` and `MarketingTreasury` contracts deploy via `daio/contracts/marketing/script/DeployMarketing.s.sol` — see `daio/contracts/marketing/README.md` for the operator command.

## Phase 1 vs Phase 2

**In Phase 1 (this drop):**
- 8 soldier skills wired; orchestrator drives boardroom + dispatches skills end-to-end in dry-run.
- Outbox-only distribution; no live publishes.
- Mocked GEO probes possible (test path); production probes use the boardroom's existing inference cascade — never pinning a model.
- Catalogue events emitted at every boundary (6 marketing.* event kinds).
- Foundry tests at 50,000 fuzz runs green (incl. the new `boardroomSessionId` invariant).
- Plain-text mode on every backend endpoint.

**Operator-gated Phase 2:**
- Mainnet deploy of `MarketingAttributionReceipt` (Base, schema v2) + `MarketingTreasury` (Ethereum L1).
- ENS subname registration ceremony for 8 soldier seats.
- Per-soldier Tessera DID issuance.
- iNFT_7857 mints.
- Live `MINDX_MARKETING_FARCASTER_LIVE`, `MINDX_MARKETING_X_LIVE` flags.

**Out of scope (separate plans):**
- Modifying `Boardroom.convene` itself — soldiers stay pure voters.
- Senatus / Curia / Genius / Tabularium / Fides / SponsioPactum — separate constitutional-layer plan.
- Kuzu / Qdrant / Meilisearch / NATS substrate — catalogue Phase 1+ plan.
- 90-day campaign execution — see `MARKETING_PLAYBOOK.md`.

## Verification

```bash
# Python tests (59 passing as of this drop)
.mindx_env/bin/pytest -q --override-ini="addopts=" \
  tests/test_marketing_catalogue_events.py \
  tests/test_brand_code_loader.py \
  tests/test_geo_probe.py \
  tests/test_marketing_onchain_clients.py \
  tests/test_marketinga_agent.py \
  tests/test_marketing_soldier_skills.py \
  tests/test_marketing_skill_registry.py

# Foundry CI gate (23 tests at 50k fuzz runs)
cd daio/contracts && FOUNDRY_PROFILE=marketing forge test --fuzz-runs 50000 -vvv

# Live backend smoke
curl http://localhost:8000/marketing/status?h=true     # 8-row soldier mapping
curl http://localhost:8000/marketing/session/<id>?h=true
```
