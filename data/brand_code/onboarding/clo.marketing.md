---
soldier_id: clo_legal
marketing_role: Regulatory + competitor neutrality
hbr_layer: 0
boardroom_persona: agents/boardroom/clo.persona
weight: 0.8
veto: none
---

# CLO — marketing capability

CLO holds 0.8 weight — the lightest soldier. Their domain is compliance.
CLO does NOT carry hard veto; a CLO `reject` still requires the weighted
score to fall below supermajority for the campaign to fail. But CLO findings
always land in the soft-warns bag where the Convener can review.

Skill: `agents/marketing/skills/clo.py:CloSkill`.

## Vote contract
Reject if:
- Brief or draft contains regulatory red flags (financial advice, ROI promises,
  jurisdictional claims, "not a security" / "SEC-compliant" assertions).
- Comparison to a competitor (Bittensor, Olas, Virtuals, ai16z, Story
  Protocol, ElizaOS, Manus) violates `competitor_map.json` neutrality rules.

## Skill output
`SkillOutput(artifact={"clean": True})` — or `SkillRefusal` with the matched
phrases.

## Wallet binding
- DID: `did:pythai:clo_legal`
- ENS: `clo.bankon.eth`
- AgentRegistry capabilities: govern.
