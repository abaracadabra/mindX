---
soldier_id: ciso_security
marketing_role: Identity gate + voice violation scan
hbr_layer: 0
boardroom_persona: agents/boardroom/ciso.persona
weight: 1.2
veto: hard
---

# CISO — marketing capability

CISO carries 1.2× veto weight in the boardroom AND the marketing orchestrator
enforces hard veto on `vote == "reject"` regardless of weighted score. CISO is
the voice + identity gate. Skill: `agents/marketing/skills/ciso.py:CisoSkill`.

## Vote contract
Reject (hard veto) on:
- Censura reports the agent identity as faded/ghosted/blocked.
- Tessera credential not bound for the agent address.
- Forbidden-term `deny_pattern` matches the proposed copy or brief.

## Skill input
Reads brief + `prior_outputs["cpo_product"]` if present (defense-in-depth scan).

## Skill output
`SkillOutput(artifact={"voice_clear": bool, "soft_warns": [...]})`.

## Wallet binding
- DID: `did:pythai:ciso_security`
- ENS: `ciso.bankon.eth`
- AgentRegistry capabilities: govern.

## Why CISO and not CLO
CISO owns identity + cryptographic provenance. Voice violations are a
cryptographic-tamper-equivalent problem in the brand-code substrate (the
brand voice IS the identity). CLO covers regulatory + competitor copy;
voice-pattern scanning sits squarely in CISO's lane.
