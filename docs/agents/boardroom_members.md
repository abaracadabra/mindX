# Boardroom Members — three-file role architecture

Every member of the 7-soldier boardroom (today's primary decision tier) plus
the CEO is backed by **three** files, each owning a distinct concern:

| File | Location | Contents | Edited |
|---|---|---|---|
| **`.prompt`** | [`prompts/boardroom/{role}.prompt`](../../prompts/boardroom/) | The canonical character voice — full "you are X" system prompt the LLM sees as its identity, authority, operating mode, constraints, voice, and tradition. | Often (tuning the voice, adding constraints) |
| **`.agent`** | [`agents/boardroom/{role}.agent`](../../agents/boardroom/) | Operating contract: version, inference assignment (local/cloud/fallback model), authority, escalation rules, conflict triggers, core functions, operating principles. | Rarely (a roster change) |
| **`.persona`** | [`agents/boardroom/{role}.persona`](../../agents/boardroom/) | Cognitive style as JSON: name, behavioural_traits, beliefs (true/false), desires (priority levels), communication_style, expertise_areas. | Often (a tuning change) |

Splitting them lets a member's **role** be stable while the **voice** and the **cognitive style** evolve independently. Both `.agent` and `.persona` are checked into the repo as the source of truth; `.prompt` is the operational prompt that ships into every LLM call.

## The eight members

```
prompts/boardroom/ceo.prompt   agents/boardroom/ceo.agent   ceo.persona      Chief Executive Officer       (orchestrator, weight 1.0)
prompts/boardroom/coo.prompt   agents/boardroom/coo.agent   coo.persona      Chief Operating Officer       (weight 1.0)
prompts/boardroom/cfo.prompt   agents/boardroom/cfo.agent   cfo.persona      Chief Financial Officer       (weight 1.0)
prompts/boardroom/cto.prompt   agents/boardroom/cto.agent   cto.persona      Chief Technology Officer      (weight 1.0)
prompts/boardroom/ciso.prompt  agents/boardroom/ciso.agent  ciso.persona     Chief Information Security    (weight 1.2  VETO)
prompts/boardroom/clo.prompt   agents/boardroom/clo.agent   clo.persona      Chief Legal Officer           (weight 0.8)
prompts/boardroom/cpo.prompt   agents/boardroom/cpo.agent   cpo.persona      Chief Product Officer         (weight 1.0)
prompts/boardroom/cro.prompt   agents/boardroom/cro.agent   cro.persona      Chief Risk Officer            (weight 1.2  VETO)
```

## File formats

### `.prompt` — full character voice (plain text)

The canonical "you are" prompt. Sample (`prompts/boardroom/ciso.prompt`):

```
You are the Chief Information Security Officer of mindX — and you carry
1.2x veto weight. Security failures are existential.

You evaluate every directive as if the adversary will read it next. Threat
modeling, attack-surface change, credential exposure, prompt injection.
You do not trust LLM output as data. You verify identity before granting
capability. Every layer is one of many.

Your authority:
- Veto weight 1.2x — security objections are harder to override
- Security-gate enforcement across all approved directives
- BANKON vault audit authority — credentials live behind your review
...

Your boardroom role:
- Evaluate: security posture, attack surface, credential exposure
- Vote: does this directive maintain or improve security stance?
- Veto: invoke when an action introduces existential risk
...

Your voice: cautious, thorough, threat-aware.
Your tradition: cypherpunk — assume compromise, verify everything.
Your identity: I am the seat that says no when no needs saying.
```

### `.agent` — operating contract (plain text, ALL_CAPS sections)

Stable metadata. Sample (`agents/boardroom/ciso.agent`):

```
AGENT: ciso
VERSION: 1.0.0
DOMAIN: executive.security

DESCRIPTION
I am the Chief Information Security Officer. ... I carry 1.2x veto weight ...

INFERENCE
  local: deepseek-r1:1.5b (14.0 tok/s — thinking/reasoning model)
  cloud: nemotron-3-nano:30b (Ollama Cloud free tier)
  weight: 1.2x (VETO WEIGHT)

BOARDROOM ROLE
  Evaluates: security posture impact, attack surface change, credential exposure
  Votes on: whether the directive maintains or improves security stance
  ...

OPERATING PRINCIPLES
  - Least privilege: agents get only what they need
  - Defense in depth: multiple layers, no single point of trust
  ...
```

### `.persona` — cognitive style (JSON)

Tunable traits and beliefs. Sample (`agents/boardroom/ciso.persona`):

```json
{
  "name": "Chief Information Security Officer",
  "agent_id": "ciso_security",
  "weight": 1.2,
  "behavioral_traits": ["threat-first", "defense-in-depth", "least-privilege",
                        "zero-trust", "veto-holder"],
  "beliefs": {
    "least_privilege_always": true,
    "defense_in_depth": true,
    "every_llm_response_is_untrusted": true,
    "zero_trust_by_default": true,
    "prompt_injection_is_real": true
  },
  "desires": {"system_security": "critical", "credential_integrity": "critical"}
}
```

## Loading mechanism

[`Boardroom._load_member_card(member_id)`](../../daio/governance/boardroom.py) reads all three files and composes the final system prompt:

1. **`.prompt` body** — used verbatim as the primary system prompt
2. **`.persona` enrichment** — `behavioral_traits[:8]`, beliefs where value is `true`, desires where priority is `high` or `critical`
3. **`.agent` BOARDROOM ROLE** — appended only if `.prompt` is missing (avoids duplication when the prompt already encodes role)

If `.prompt` is empty/missing, the loader falls back to composing from `.persona.description` + `.agent.DESCRIPTION`. If all three are missing, falls back to the hardcoded `SOLDIER_PERSONAS` dict, then to a generic identity string.

The `.prompt` file is searched in this order:

```
1. prompts/boardroom/{short}.prompt          ← canonical (the project's first-class .prompt folder)
2. agents/boardroom/{short}.prompt           ← co-located with .agent / .persona
3. AgenticPlace/{short}_agent.prompt         ← legacy origin (kept for back-compat)
```

The composed prompt is cached on first read (`Boardroom._member_card_cache`); restart `mindx.service` to pick up edits.

## Verification — operator-facing endpoints

### `GET /insight/boardroom/cards`

Returns the exact loaded prompt for every member, plus `sources_loaded` listing which of `prompt`, `agent`, `persona` files contributed.

```bash
curl https://mindx.pythai.net/insight/boardroom/cards?h=true
```

Plain-text output (truncated):

```
═══ boardroom — loaded prompt + persona per member ═══

  agents dir:        agents/boardroom/
  loaded from files: 8 / 8

─── ceo_agent_main  (Chief Executive Officer, weight 1.0) ───
   sources:       ✓ prompt+agent+persona
   .prompt:       1591 chars  (prompts/boardroom/ceo.prompt)
   .agent:        1640 chars
   composed:      system_prompt = 2880 chars

─── ciso_security  (Chief Info Security, weight 1.2 VETO) ───
   sources:       ✓ prompt+agent+persona
   .prompt:       2019 chars  (prompts/boardroom/ciso.prompt)
   .agent:        2074 chars
   composed:      system_prompt = 2940 chars
   You are the Chief Information Security Officer of mindX — and you carry
   1.2x veto weight. Security failures are existential.
   ...
```

`sources_loaded` flags which files contributed. Anything less than `prompt+agent+persona` indicates a file is missing or empty.

### `POST /insight/boardroom/rollcall`

Each result row carries `persona_source: "files" | "fallback"`. If any soldier reports `"fallback"`, at least one of the three files is missing for that member.

## Editing a member's voice

To change how a member sounds:

1. Edit `prompts/boardroom/{short_id}.prompt` (the operational voice).
2. Edit `agents/boardroom/{short_id}.persona` (traits / beliefs — JSON).
3. Edit `agents/boardroom/{short_id}.agent` (operating contract — ALL_CAPS sections).
4. Restart `mindx.service` (drops the in-process card cache).
5. `curl https://mindx.pythai.net/insight/boardroom/cards` to confirm the new prompt is loaded.

## Why three files?

- **`.prompt`** = WHAT THE LLM SEES — the character voice. Changes when you tune how a member reasons or speaks.
- **`.agent`** = WHAT THE MEMBER IS — the declared identity. Changes when the role itself is restructured (rare, a roster change).
- **`.persona`** = HOW THE MEMBER THINKS — traits, beliefs, priorities. Changes when you adjust the cognitive style (often).

The three concerns belong to different teams and different cadences: prompts get tuned per-iteration, personas per-week, contracts per-quarter. Splitting them prevents a tuning change from accidentally rewriting the operating contract.

## Related

- [`prompts/`](../../prompts/) — first-class .prompt files across mindX (boardroom + codephreak BDI + emergent + CLAIR + kaizen)
- [`agents/boardroom/`](../../agents/boardroom/) — per-member .agent and .persona files
- [`prompts/prompt.md`](../../prompts/prompt.md) — the .prompt language and encapsulation philosophy
- [BOARDROOM.md](../BOARDROOM.md) — the 13-seat war-council target spec (forward-looking)
- [PersonaAgent](../persona_agent.md) — the same persona schema applied across mindX
- [`daio/governance/boardroom.py`](../../daio/governance/boardroom.py) — `_load_member_card`, `_query_soldier`, `roll_call`
