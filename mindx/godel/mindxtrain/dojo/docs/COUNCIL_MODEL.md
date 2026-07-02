# The Council model — Boardroom, CEO-as-a-Service, War Council

Two governance bodies sit behind the Dojo's **Council** tab. They are *not* the
same thing, and they pull in opposite directions:

## The Dojo — the deliberation arena
The Dojo is where disagreement is worked. Agents spar, score, and revise; that is
the mechanism by which a divided room converges.

## The Boardroom — consensus from disagreement (internal)
The Boardroom (7 soldiers + CEO, CISO/CRO carrying veto weight) **uses the Dojo to
achieve consensus from disagreement through deliberation.** The soldiers do not
start agreed — they argue their domains (security, risk, finance, product, legal,
ops, tech), and deliberation drives them to a weighted consensus. It is an
**internal, cooperative** process: the room talking itself into one decision.

## CEO-as-a-Service — the CEO carries the boardroom's decision
The **CEO embodies the boardroom's outcome.** When the CEO acts, the CEO's decision
*includes the boardroom's decision* — the consensus is folded into the CEO's
verdict. Exposed as an interface, this is **CEO-as-a-Service**: a single
addressable decision-maker that already contains the deliberated consensus of the
room behind it.

## The War Council — an outside hostile force (external)
The **War Council is an example of an outside, hostile force directing the
CEO-as-a-Service.** It is *not* internal deliberation; it is external pressure. Its
13 prime-weighted seats and accelerating prime majority exist to **guarantee a
decisive directive** that is pointed *at* the CEO-as-a-Service from outside. Where
the Boardroom converges cooperatively, the War Council imposes adversarially.

## The flow

```
disagreement ──Dojo deliberation──▶ Boardroom consensus ──folded into──▶ CEO decision
                                                                          (CEO-as-a-Service)
                                                                                ▲
                                          external · hostile · decisive        │ directs
                                          ─────────────────────────────────────┘
                                                        War Council
```

- **Boardroom** → consensus *from* disagreement, internal, cooperative (the Dojo).
- **CEO-as-a-Service** → the served decision-maker that *includes* that consensus.
- **War Council** → an outside hostile force that *directs* the CEO-as-a-Service.

# warcouncil is found at https://mastermind.pythai.net

## Implication for the wiring

The Boardroom and the War Council are **distinct bodies**, not the same voters: the
War Council is external and adversarial, so it should not be composed of the
internal boardroom soldiers. The Dojo's Council tab keeps them as two separate,
endpoint-agnostic modules — Boardroom (consensus) and War Council (external
directive) — so a client can watch internal consensus and external pressure
side by side.

## The Dojo blackbox — modes (= themes)

The blackbox **measures actor quality**: objective imprint eval + subjective
test / response. A *fresh* actor's session is an **audition**. It runs in four
modes — and a mode is also a theme (one unified `THEMES` registry, so every
functional theme is accessible alongside the visual head layers primitive · gltf):

- **interactive** — subjective test: spar with the actor and score its responses (a fresh actor → audition).
- **mindXtrain** — imprint quality from eval: train into an actor (dream → weights → imprint → serve), with live `/insight/godel/ascend`.
- **boardroom** — the soldiers deliberate to consensus (feeds CEO-as-a-Service); live `/insight/boardroom/recent`.
- **dojo** — the base/default state of the arena itself.

## Actor-quality assessment (every mode)

A fresh actor's session is named by the mode:

- **audition** — dojo · interactive · mindXtrain
- **recruit** — war council
- **interview** — boardroom

Every assessment yields **pass / fail · a percentage · and reasons**, drawn from three sources:

- **review** — subjective scores captured in the blackbox (avg/5, ▲ up / ▼ down),
- **eval** — objective imprint result from the ascent log (`/insight/godel/ascend` — accepted ascents),
- **panel review** — the governing body's verdict (boardroom consensus / war-council verdict).

The blackbox renders a `{term} assessment` card: **PASS/FAIL · %**, with a ✓/✗ reason per source.

### Persisting assessments

Each assessment can be **recorded** (`💾 record {term}`) — persisted to local
storage (`dojo-assessments`) keyed by **actor id** (defaults to the dataset name).
A **permanent record to actor** toggle (**default OFF**) marks the record as a
durable record on the actor (`★ permanent`); off keeps it as an ordinary
persisted entry. The card shows the recent records for the current actor.

### Exporting an actor

The Personas tab can **export an actor** (`⤓ export actor record`): a single
`{id}.actor.json` bundling the **.persona** (with the chosen theme + your prompt)
and its **★ permanent assessment records** (matched by actor id / name). The button
shows the permanent-record count, so an actor's `.persona` travels with its
audition/interview/recruit history.

### Importing an actor + BONA FIDE issuance

The Personas tab can **import an `.actor.json`** (`⤒ import .actor.json`): it
restores the persona (into a local imported-actors store, merged into the list),
re-applies the saved **theme** and **prompt** overrides, and merges the
**permanent records** back into `dojo-assessments` (deduped by actor + timestamp).

**BONA FIDE** (the DAIO credential — Algorand ASA with clawback) can be issued as
a **service option**: `◈ issue 1 BONA FIDE` per actor, or an **issue-on-import**
toggle — which **only credentials an actor whose import carries a PASS assessment**
(no PASS → BONA FIDE skipped). It POSTs to the agnostic `/bona_fide/issue` service
(default mindX) with the actor id + wallet. The endpoint is **401-gated**, so a
credentialed operator supplies a token in the **operator token (OVERLORD/OVERSEER)**
field — held **in memory only, never persisted** — sent as both `X-Session-Token`
and `Authorization: Bearer`. On success the badge re-verifies on-chain; without a
token it reports *needs operator token*. Each persona shows a **BONA FIDE ◈ ✓ / ✗**
badge (yes/no).

The badge is verified **on-chain via the public Dojo standings** (`/dojo/standings`
— per-agent `rank` · `tier` · `bona_fide`; `/daio/agent_map` is 401-gated): on load
(and `↻ verify on-chain`) the standings are fetched and each actor matched by
`agent_id` / wallet; `bona_fide > 0` ⇒ ✓ and `rank` is surfaced as the tier chip.
The badge shows its source `(on-chain)` when reachable, falling back to the
**local** flag (persisted + round-tripped through `.actor.json`) when it is not.

## Live endpoints (verified end-to-end, mindx.pythai.net)

All client surfaces were tested against the live protocol:

| surface | endpoint | host | notes |
|---------|----------|------|-------|
| Boardroom | `/insight/boardroom/recent` | mindX | `{sessions:[{directive,outcome,weighted_score,votes}]}` (200) |
| War Council | `/insight/war_council` | **mindX** | co-served by mindX (mastermind host → 404); `{config,recent,vote_source}` (200) |
| mindXtrain ascent | `/insight/godel/ascend` | mindX | `{capability,settings,training,events[],count}` — log is **`events`**, imprint delta is **`recall.delta`** (200) |
| Verification | `/dojo/standings` | mindX | **public** (`/daio/agent_map` is 401-gated); `{standings:[{agent_id,rank,tier,bona_fide,group}]}` — `rank` is the tier name, `bona_fide>0` ⇒ ◈ ✓ |
| BONA FIDE issue | `/bona_fide/issue` | mindX | exists, **401-gated** (needs OVERLORD/OVERSEER auth) |
