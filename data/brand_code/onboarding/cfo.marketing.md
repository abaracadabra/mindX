---
soldier_id: cfo_finance
marketing_role: HBR Layer 4 — reporting + treasury
hbr_layer: 4
boardroom_persona: agents/boardroom/cfo.persona
weight: 1.0
---

# CFO — marketing capability

The CFO owns reporting because measurement + ROI are finance concerns. The
CFO also reads `MarketingTreasury` state for the buyback ledger that feeds
quarterly RetroPGF. Skill: `agents/marketing/skills/cfo.py:CfoSkill`
(delegates to `agents/marketing/reporting_agent.py:ReportingAgent` plus a
treasury-client read).

## Vote contract
Approve if the spend is justified by the expected GEO + KPI lift; reject if
forecast spend is unbounded or no measurement is wired.

## Skill input
Reads `prior_outputs["coo_operations"]` (the `DistributionLedger`).

## Skill output
`SkillOutput(artifact={"kpi": KpiSnapshot, "treasury": TreasurySnapshot|None})`.

## GEO probe
- Engines: ChatGPT, Claude, Perplexity, Gemini, Grok.
- Brand terms: PYTHAI, DELTAVERSE, BANKON, mindX, AgenticPlace, BONAFIDE, marketinga.agent.
- Cap: `geo.weekly_budget_usd` (default $20). Cache 24h.
- Selector + Ollama cascade (no model pinning).

## Wallet binding
- DID: `did:pythai:cfo_finance`
- ENS: `cfo.bankon.eth`
- AgentRegistry capabilities: report.
