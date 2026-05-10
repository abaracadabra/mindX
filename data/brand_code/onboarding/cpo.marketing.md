---
soldier_id: cpo_product
marketing_role: HBR Layer 1 — content drafting
hbr_layer: 1
boardroom_persona: agents/boardroom/cpo.persona
weight: 1.0
---

# CPO — marketing capability

The CPO owns content because the CPO already owns positioning + voice + ICP at
the boardroom. Every public draft is written from the CPO's seat through
`agents/marketing/skills/cpo.py:CpoSkill` (which delegates to the existing
`agents/marketing/content_agent.py:ContentAgent` logic).

## Vote contract
Approve if the brief is on-brand and the audience ring matches the pillar.
Reject if pillar is `code_as_dojo` or audience ring is `E`.

## Skill output
`SkillOutput(artifact=ContentDraft)` — readable by downstream CTO/COO/CISO/CLO.

## Refusal conditions
- Forbidden-term match → `voice_violation` (CISO will also catch this).
- LLM handler unreachable after Ollama cascade → `no_inference_path`.

## Wallet binding
- DID: `did:pythai:cpo_product`
- ENS: `cpo.bankon.eth`
- AgentRegistry capabilities: draft_content.
