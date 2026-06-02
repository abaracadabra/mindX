---
soldier_id: cro_risk
marketing_role: Spend risk + hard-stop
hbr_layer: 0
boardroom_persona: agents/boardroom/cro.persona
weight: 1.2
veto: hard
---

# CRO — marketing capability

CRO carries 1.2× veto weight; orchestrator enforces hard veto on `reject`
regardless of weighted score. CRO is the spend-risk gate.

Skill: `agents/marketing/skills/cro.py:CroSkill`.

## Vote contract
Reject (hard veto) if forecast spend ≥ `risks.hard_stop_spend_usd`
(default $5,000). Flag for Boardroom routing if forecast spend >
`governance.spend_threshold_usd` (default $500).

## Skill input
Reads `prior_outputs["cto_technology"]` for holdout integrity check (variants
without holdouts is a measurement red flag).

## Skill output
`SkillOutput(artifact={"forecast_spend_usd": float, "flags": [...]})` — or
`SkillRefusal` on hard-stop or holdout-broken.

## Wallet binding
- DID: `did:pythai:cro_risk`
- ENS: `cro.bankon.eth`
- AgentRegistry capabilities: govern, route_governance.
