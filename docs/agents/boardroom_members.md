# Boardroom Members — prompt + persona loading

The 7-soldier boardroom (today's primary decision tier) plus the CEO are **each backed by a paired `.agent` + `.persona` file** in [`agents/boardroom/`](../../agents/boardroom/). Every LLM call that asks a member for a vote, an acknowledgment, or a deliberation injects a system prompt **composed from those two files** — not the hardcoded `SOLDIER_PERSONAS` dict in `boardroom.py` (that's the fallback if files go missing).

## File pair per member

```
agents/boardroom/
├── ceo.agent      ceo.persona      Chief Executive Officer (orchestrator, weight 1.0)
├── coo.agent      coo.persona      Chief Operating Officer       (weight 1.0)
├── cfo.agent      cfo.persona      Chief Financial Officer       (weight 1.0)
├── cto.agent      cto.persona      Chief Technology Officer      (weight 1.0)
├── ciso.agent     ciso.persona     Chief Information Security    (weight 1.2  VETO)
├── clo.agent      clo.persona      Chief Legal Officer           (weight 0.8)
├── cpo.agent      cpo.persona      Chief Product Officer         (weight 1.0)
└── cro.agent      cro.persona      Chief Risk Officer            (weight 1.2  VETO)
```

### `.agent` file (operating contract, plain text)

ALL_CAPS section headers; body is the human-readable description, inference assignments, boardroom role, conflict triggers, escalation rules. Sample (`ciso.agent`):

```
AGENT: ciso
VERSION: 1.0.0
DOMAIN: executive.security

DESCRIPTION
I am the Chief Information Security Officer. Security posture. Threat modeling.
Access control. ... I carry 1.2x veto weight — my objections weigh more because
security failures are existential. ...

INFERENCE
  local: deepseek-r1:1.5b (14.0 tok/s — thinking/reasoning model)
  cloud: nemotron-3-nano:30b (Ollama Cloud free tier ...)
  weight: 1.2x (VETO WEIGHT)

BOARDROOM ROLE
  Evaluates: security posture impact, attack surface change, credential exposure
  Votes on: whether the directive maintains or improves security stance
  Veto power: 1.2x weight means security objections are harder to override
  Escalates: vulnerability detected → immediate CEO alert ...
  Dissent style: identifies threat vectors, proposes mitigations before approval
```

### `.persona` file (behavioural traits, JSON)

Mirrors the [PersonaAgent](../persona_agent.md) shape. Sample (`ciso.persona`):

```json
{
  "name": "Chief Information Security Officer",
  "agent_id": "ciso_security",
  "role": "security_authority",
  "weight": 1.2,
  "description": "Security failures are existential. I carry 1.2x veto weight.",
  "behavioral_traits": ["threat-first", "defense-in-depth", "least-privilege",
                        "zero-trust", "veto-holder"],
  "beliefs": {
    "least_privilege_always": true,
    "defense_in_depth": true,
    "every_llm_response_is_untrusted": true,
    ...
  },
  "desires": {"system_security": "critical", "credential_integrity": "critical"},
  "inference": { "local_model": "deepseek-r1:1.5b", ... }
}
```

## Loading mechanism

[`Boardroom._load_member_card(member_id)`](../../daio/governance/boardroom.py) at `daio/governance/boardroom.py:445` loads both files and composes a system prompt in this order:

1. **Persona hook line** — `"You are the {persona.name}. {persona.description}"`
2. **Behavioural traits** — first 8 from `persona.behavioral_traits`
3. **Operating beliefs** — every key in `persona.beliefs` whose value is `true`
4. **Priorities** — `persona.desires` keys whose value is `"high"` or `"critical"`
5. **Boardroom role** — `BOARDROOM ROLE` section from `.agent` (first 6 non-empty lines)

Result is cached on first read (`self._member_card_cache`). The same composed prompt is used by:

| Caller | Purpose |
|---|---|
| `_query_soldier()` | full vote inference (boardroom session) |
| `roll_call()` | acknowledgment probe (1-line ack per member) |
| `convene_stream()` | streaming convocation |

If neither file exists for a member, the loader falls back to `SOLDIER_PERSONAS` dict, then to the generic `"You are {member_id}."` string.

## Verification — operator-facing endpoints

### `GET /insight/boardroom/cards`

Returns the exact composed system_prompt for every member, plus the raw `.agent` and parsed `.persona` content, plus a `loaded_from_files` boolean.

```bash
curl https://mindx.pythai.net/insight/boardroom/cards?h=true
```

Plain-text output (truncated):

```
═══ boardroom — loaded prompt + persona per member ═══

  agents dir:        agents/boardroom/
  loaded from files: 8 / 8

─── ceo_agent_main  (Chief Executive Officer, weight 1.0) ───
   source:        ✓ files  ·  system_prompt 663 chars  ·  agent_card 1640 chars
   You are the Chief Executive Officer. I direct. The soldiers deliberate. ...

─── ciso_security  (Chief Information Security Officer, weight 1.2 VETO) ───
   source:        ✓ files  ·  system_prompt 884 chars  ·  agent_card 2074 chars
   You are the Chief Information Security Officer. Security failures are existential. ...
   Behavioral traits: threat-first, defense-in-depth, least-privilege, zero-trust, veto-holder
   Operating beliefs: least privilege always; defense in depth; ...
   ...
```

### `GET /insight/boardroom/rollcall`

Each result row now carries `persona_source: "files" | "fallback"`. If any soldier reports `"fallback"`, the matching `.agent` or `.persona` file is missing and the operator should investigate.

```bash
curl -X POST https://mindx.pythai.net/insight/boardroom/rollcall | \
    jq '.results | to_entries[] | {soldier:.key, source:.value.persona_source}'
```

## Editing a member's prompt

To change how a soldier reasons:

1. Edit `agents/boardroom/<short_id>.agent` (operating description / boardroom role) and/or `agents/boardroom/<short_id>.persona` (traits / beliefs / desires).
2. Restart `mindx.service` (or call `Boardroom.get_instance()._member_card_cache.clear()` from a debug hook) to drop the in-process cache.
3. `curl https://mindx.pythai.net/insight/boardroom/cards` and confirm the change is reflected in the new `system_prompt` for that member.

## Why two files?

- **`.agent`** is the operating contract — version, inference assignment, escalation rules, conflict triggers. Edited rarely; a roster change.
- **`.persona`** is the cognitive style — traits, beliefs, desires. Edited more often; a tuning change.

Splitting them lets a member's role be stable while their cognitive style is iterated. Both are checked into the repo as the source of truth.

## Related

- [BOARDROOM.md](../BOARDROOM.md) — the full 13-seat governance spec (war council + dojo + boardroom hierarchy)
- [`PersonaAgent`](../persona_agent.md) — the same persona schema applied across mindX
- [`agents/boardroom/`](../../agents/boardroom/) — the member files themselves
- [`daio/governance/boardroom.py`](../../daio/governance/boardroom.py) — `_load_member_card`, `_query_soldier`, `roll_call`
