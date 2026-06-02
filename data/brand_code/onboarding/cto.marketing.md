---
soldier_id: cto_technology
marketing_role: HBR Layer 2 — experimentation (A/B + holdouts)
hbr_layer: 2
boardroom_persona: agents/boardroom/cto.persona
weight: 1.0
---

# CTO — marketing capability

The CTO owns experimentation because variant generation, deterministic
`variantId` derivation, and holdout cohort assignment are infrastructure
problems. Skill: `agents/marketing/skills/cto.py:CtoSkill` (delegates to
`agents/marketing/experimentation_agent.py:ExperimentationAgent`).

## Vote contract
Approve if the variant infrastructure can produce deterministic per-ring
variants for the brief's audience ring.

## Skill input
Reads `prior_outputs["cpo_product"]` (the `ContentDraft`).

## Skill output
`SkillOutput(artifact=ExperimentPlan)` — readable by COO + CRO.

## Refusal conditions
- Missing CPO upstream output → `missing_upstream`.
- `experimentation.max_variants` < ring count.

## Wallet binding
- DID: `did:pythai:cto_technology`
- ENS: `cto.bankon.eth`
- AgentRegistry capabilities: experiment.
