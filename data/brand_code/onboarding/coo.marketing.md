---
soldier_id: coo_operations
marketing_role: HBR Layer 3 — distribution
hbr_layer: 3
boardroom_persona: agents/boardroom/coo.persona
weight: 1.0
---

# COO — marketing capability

The COO owns distribution because channel execution, outbox/live publishing,
and IndexNow ping are operational concerns. Skill:
`agents/marketing/skills/coo.py:CooSkill` (delegates to
`agents/marketing/distribution_agent.py:DistributionAgent`).

## Vote contract
Approve if the outbox path is writable and feature flags are sane.

## Skill input
Reads `prior_outputs["cto_technology"]` (the `ExperimentPlan`).

## Skill output
`SkillOutput(artifact=DistributionLedger)` — readable by CFO.

## Channels
- `farcaster` (gated by `MINDX_MARKETING_FARCASTER_LIVE`)
- `x` (gated by `MINDX_MARKETING_X_LIVE`)
- `llms_txt` (always live local-file write)
- `indexnow` (Bing/Copilot ping)

## Refusal conditions
- Missing CTO upstream output → `missing_upstream`.
- Channel auth missing in BANKON Vault when live flag is on.

## Wallet binding
- DID: `did:pythai:coo_operations`
- ENS: `coo.bankon.eth`
- AgentRegistry capabilities: distribute.
