# Marketing playbook — 90-day ops runbook

**This file is a runbook, not a script.** None of it is automated by the marketinga.agent. The Convener (Codephreak) reads this, schedules the work, and uses the agent to execute the campaign-shaped pieces (drafting, GEO probing, attribution-receipt emission). The strategy choices stay human.

The plan reflects the spec from the May 8 2026 HBR-mapped document, with conservative defaults and explicit Phase-2 markers where on-chain action is required.

---

## T0 — week 1 (May 9–15, 2026)

- [ ] Freeze the GEO baseline. `marketinga.agent.run_geo_probe()` against ChatGPT, Claude, Perplexity, Gemini, Grok with the seven brand terms (PYTHAI, DELTAVERSE, BANKON, mindX, AgenticPlace, BONAFIDE, marketinga.agent) and the 30-prompt set. Commit the rollup as Tessera credential `geo_baseline:2026-05-15`.
- [ ] Brand-code finalized and committed (already done in this drop).
- [ ] Wikidata Q-item drafted via `agents.marketing.tools.wikidata`. Convener manually submits via WP:AfC.
- [ ] `llms.txt` + `llms-full.txt` deployed to `mindx.pythai.net`, `agenticplace.pythai.net`, `bankon.pythai.net` static-site roots.
- [ ] `schema.org` Organization / SoftwareApplication / Article / FAQPage `@graph` rolled across all three sites.
- [ ] IndexNow ping wired to the CMS (operator step; tool exists at `agents.marketing.tools.indexnow`).
- [ ] Codephreak posts one long-form essay on the ETHGlobal OpenAgents experience tagged to `ethglobal_openagents_lineage` pillar. Founder voice — agent does not draft.

## Week 2 (May 16–22)

- [ ] Foundry CI gate green; `MarketingAttributionReceipt` smoke-deployed to Base Sepolia for end-to-end test.
- [ ] Three Reddit AMAs scheduled (r/ethereum, r/algorand, r/MachineLearning). The CPO soldier skill drafts the prep documents (boardroom approves); Convener approves; Codephreak runs the AMAs manually.
- [ ] First Frame on Farcaster /aiagents lets users mint an "ETHGlobal OpenAgents 2026 attestation" — a Tessera credential as collectible.
- [ ] Apply for inclusion in Electric Capital crypto-ecosystems taxonomy.

## Week 3 (May 23–29)

- [ ] Shoulder-content burst: one post on freeCodeCamp ("How HTTP 402 enables agent payments — a practitioner's view"), one on The New Stack ("BDI agents in 2026: why beliefs/desires/intentions still wins over single-prompt orchestration"), one on InfoQ ("Constitutional layers for AI DAOs: the dual-chain pattern"). Each cites mindX, AgenticPlace, BANKON, BONAFIDE in passing.
- [ ] Reddit presence intensifies: thoughtful long-form replies in 5–10 high-authority threads per week. No link-drops.
- [ ] Discord daily-active-senders metric becomes a tracked weekly KPI.

## Week 4 (May 30 – June 5)

- [ ] First demo video: ≤2 minutes, shows `marketinga.agent` autonomously generating, A/B-forking, distributing, and reporting on a single campaign brief, with the receipt visible on basescan. Pinned X post by Codephreak.
- [ ] Companion long-form on the Convener-Counsellor pattern (this is one of the few areas where founder voice + agent voice overlap; Codephreak writes, agent fact-checks against `data/brand_code/`).
- [ ] **Operator step (Phase 2):** `MarketingAttributionReceipt` mainnet-deploy to Base via `forge script daio/contracts/marketing/script/DeployMarketing.s.sol:DeployMarketing --broadcast`.

## Week 5 (June 6–12)

- [ ] Hackathon co-sponsorship announced: PYTHAI bounty at the next ETHGlobal event. $50k for "best agent built on PYTHAI mindX SDK + AgenticPlace + x402".
- [ ] DevRel push: SDK quickstart published with full working example, no ellipses, copy-pasteable.
- [ ] Per-product `llms-full.txt` files deployed (mindX, AgenticPlace, BANKON, x402 integration, BONAFIDE).

## Week 6 (June 13–19)

- [ ] First commissioned research drop: Decentralised.co or Delphi Digital analysis of "the constitutional-layer thesis: why dual-chain DAIO is the AI×crypto missing piece."
- [ ] Coordinated press: CoinDesk, The Block, Decrypt receive embargo packets.
- [ ] Bankless podcast booking confirmed for week 7.

## Week 7 (June 20–26)

- [ ] Bankless drops, Empire drops, Decentralised.co research drops on the same day.
- [ ] `marketinga.agent` generates the post-launch content burst across X, Farcaster, LinkedIn (Convener review for each).
- [ ] KOL outreach moves to the AI-side: Latent Space pod inquiry, Lenny's pod inquiry. `agents.marketing.tools.kol_outreach` drafts; Convener sends.
- [ ] Wintermute engagement announcement (no terms disclosed).

## Week 8 (June 27 – July 3)

- [ ] Re-measure GEO baseline. Track delta. If share-of-voice in any engine is below 5% across the seven brand terms × 30-prompt set, the CISO soldier skill flags for Convener intervention.
- [ ] Second demo video: agent-to-agent transaction on x402, two PYTHAI agents trading services, one Tessera credential per call.

## Week 9 (July 4–10)

- [ ] Hackathon week. Codephreak attends in person; PYTHAI sponsors a side-event happy hour; bounty winners announced live.
- [ ] Second commissioned research piece: Messari analysis of "Proof-of-Active-Cognition emission design" comparing PYTHAI to Olas PoAA and Bittensor dTAO.

## Week 10 (July 11–17)

- [ ] Listing pipeline starts. Tier-2 CEX outreach (Bybit, Gate, MEXC, KuCoin) begins with the listing-application packet that includes the Foundry test reports, the audit report, the DAA/sticky-TVL projection, and the marketing-treasury buyback rule.
- [ ] Wintermute begins active making.
- [ ] First Frame-native PYTHAI agent deployed on Farcaster /aiagents.
- [ ] **Operator step (Phase 2):** `MarketingTreasury` mainnet-deploy to Ethereum L1.

## Week 11 (July 18–24)

- [ ] Coinbase Asset Hub application submitted (~30-day timeline).
- [ ] Public technical AMA on X Spaces with Codephreak + the Counsellor agents (agents respond via TTS through ElevenLabs voice cloning, but only Convener-approved scripts).
- [ ] Third commissioned research piece announced.

## Week 12 (July 25–31)

- [ ] Quarterly RetroPGF round one. Foundation treasury (sourced from `MarketingTreasury.foundation` 1% share + initial endowment) distributes 100k USDC across ten teams that built on PYTHAI in the prior 90 days.
- [ ] Public dashboard.
- [ ] Codephreak writes the quarterly philosophical pillar essay (`code_as_dojo`) — the manual founder-only piece — anchoring the 90-day arc.

---

## Day-90 KPI review

These are the metrics. The vanity numbers (Twitter followers, raw TVL, total Discord members, total hackathon submissions) are explicitly **not** measured and not reported.

- **D30 cohort retention** of transacting addresses ≥ 25% (Polymarket-class threshold; below this means the agent marketplace lacks habit).
- **Weekly active agents** with tokens billed > 0 ≥ 50 (the agent-marketplace NSM; fewer means demand is thin).
- **Adjusted x402 revenue** ≥ $25k/month (the monetization NSM at this stage).
- **GEO share-of-voice** ≥ 10% across at least three of five engines for the seven brand terms.
- **Senior-developer commits** to PYTHAI ecosystem repos ≥ 50 unique authors (Electric Capital methodology).
- At least one **Tier-2 CEX listing** live with Wintermute making.
- Coinbase application advanced past Legal review.

## What to do if behind plan

- **GEO behind by week 8:** trigger an unbudgeted commissioned research drop at week 9 instead of waiting for week 12. The Princeton GEO paper benchmark of 30–40% citation lift is the modeling reference; one well-cited paper moves share-of-voice ~10pp in 30 days.
- **D30 retention behind:** debug the agent-marketplace UX before any new content. Retention is downstream of habit-forming surface, not narrative.
- **Senior-dev commits behind:** double the hackathon bounty pool. Solana's 8-hackathon → 3,000-projects pipeline is the playbook.

## What to do if ahead of plan

- **GEO ahead:** save research budget for the constitutional-layer narrative drop in month 4. That post is the harder one to write and will need more internal iteration.
- **Retention ahead:** that's the agentic flywheel landing. Don't perturb it.

---

## Operator playbook for `marketinga.agent` itself

```bash
# Before week 1
python -m agents.marketing.onchain.bind_identity --dry-run     # preview
python -m agents.marketing.onchain.bind_identity --execute     # bind (operator-gated)

# Run a campaign (dry-run; outbox only)
python -c "import asyncio; from agents.marketing.marketinga_agent import MarketingaAgent, CampaignBrief; \
  inst = asyncio.run(MarketingaAgent.get_instance(brand_code_root='data/brand_code', \
    toml_config_path='data/config/marketinga.toml', llm_caller=lambda s,u: __import__('asyncio').sleep(0))); \
  ..."     # see docs/MARKETING_AGENT.md for the canonical caller wiring

# Inspect
curl http://localhost:8000/marketing/status?h=true
curl http://localhost:8000/marketing/campaigns?h=true
curl http://localhost:8000/marketing/identity?h=true

# Flip live publishing (Phase 2)
export MINDX_MARKETING_FARCASTER_LIVE=1
export MINDX_MARKETING_X_LIVE=1
```

The CI gate runs:

```bash
pytest -q --override-ini="addopts=" tests/test_marketing*.py tests/test_brand_code*.py tests/test_geo_probe.py
cd daio/contracts && FOUNDRY_PROFILE=marketing forge test --fuzz-runs 50000
```

Both must be green before any merge that touches the marketing layer.
