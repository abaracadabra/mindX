# Dojo Arbiter — the blackbox consensus-arbitration service

The **Dojo** is mindX's arbitration / escalation tier: **Boardroom (t1) → Dojo (t2) →
War Council (t3)**. Where the Boardroom, the War Council, DAIO/JudgeDread, and mindXtrain
each produce *disagreement* in their own vocabulary, the Dojo Arbiter is the one primitive
that ingests those heterogeneous verdicts, normalizes them into **ballots**, resolves the
disagreement under a *chosen, variable* **consensus model**, and records a single verifiable
**decision**.

- Module: [`daio/governance/dojo_arbiter.py`](../daio/governance/dojo_arbiter.py) (`DojoArbiter`, module-level `decide`/`recent`)
- Ledger: `data/governance/dojo_decisions.jsonl` (append-only, rebuildable)
- Booth: every decision is also written to the canonical hash-linked VotingBooth
  (`data/governance/votingbooth.jsonl`) and emitted as a `dojo.decision` catalogue event
- Live: `GET /insight/dojo/decisions` (public diagnostics; `?h=true` for plain text)

## It is a *service* — callable three ways

All three reach the same engine and the same recording sinks:

```bash
# 1. CLI — boardroom/warcouncil/mindXtrain (or an operator) can shell out
python scripts/dojo.py decide --subject "promote gen7" --model supermajority \
  --mindxtrain verdict.json --boardroom session.json --h
python scripts/dojo.py recent --limit 10 --h
python scripts/dojo.py models

# 2. HTTP
curl -X POST localhost:8000/dojo/decide -H 'Content-Type: application/json' -d '{
  "subject":"promote gen7","consensus_model":"supermajority",
  "mindxtrain":{"accepted":true,"delta":0.06},
  "boardroom":{"votes":[{"soldier_id":"cro_risk","vote":"reject","confidence":0.7}]}}'
curl 'localhost:8000/insight/dojo/decisions?h=true'
```

```python
# 3. in-process
from daio.governance import dojo_arbiter as A
rec = await A.decide(subject="promote gen7",
                     ballots=A.from_mindxtrain(verdict) + A.from_boardroom(session),
                     consensus_model="supermajority")
```

## Ballots + source normalizers

A **ballot** is one normalized vote `{origin, voter, vote: approve|reject|abstain, weight,
confidence, reasoning}`. The Dojo is "a service to" each source via a normalizer:

| source | adapter | from |
|--------|---------|------|
| Boardroom | `from_boardroom(session)` | `BoardroomSession.votes` (weight·confidence) |
| War Council | `from_warcouncil(seat_votes)` | `[{seat,vote,role?}]` (seat preserved) |
| mindXtrain | `from_mindxtrain(verdict)` | imprint `{accepted, delta, recall_*}` → one ballot |
| DAIO | `from_daio(group_votes)` | JudgeDread `{group:{voter:bool}}` |

## Variable consensus models

The "variable consensus including DAIO" — a registry (`CONSENSUS_MODELS`); each resolves
ballots into `(decision, score, threshold)` where `decision ∈ {approved, rejected,
exploration, no_quorum}`. **Dissent is a feature**: a split below threshold yields
`exploration` with dissent branches rather than a forced fail.

| model | rule | reuses |
|-------|------|--------|
| `supermajority` | weight·confidence ≥ 0.666; mixed → exploration | Boardroom `_tally_votes` math |
| `weighted_confidence` | weight·confidence ≥ 0.5, decisive | — |
| `prime_ladder` | prime-weighted accelerating majority, never deadlocks | `mindx/war_council.py:tally` |
| `two_of_three` | ≥ 2/3 of groups approve on own majority | DAIO/JudgeDread rule |
| `quorum` | raw headcount majority | — |

## Recording (three sinks, all guarded)

1. `data/governance/dojo_decisions.jsonl` — the Dojo's own append-only ledger;
2. the canonical hash-linked **VotingBooth** (`agents.provenance_chain.council_booth`) —
   tamper-evident, `verify_ledger()` checks content hashes + prev/hash linkage;
3. a `dojo.decision` **catalogue** event (`agents.catalogue.events.emit_catalogue_event`).

## mindXtrain integration (advisory now, authoritative later)

`mindx/godel/mindxtrain/ascend.py` calls `_dojo_advisory(generation, verdict, notes)` right
after each imprint proof-of-recall verdict (both the general `ascend` and the v1.0.0 CPU
`ascend_recipe`). It **records** a Dojo decision from the imprint verdict but does **not**
change promotion — the imprint gate remains the authority. Gated by
`MINDX_DOJO_ARBITER_ENABLED` (default on; `0` makes the advisory call sites no-op). The flag
`MINDX_DOJO_GATES_IMPRINT` is reserved for the future authoritative mode where the Dojo's
blackbox vote gates `serve → ollama` promotion.

## Boardroom escalation

When a Boardroom session ends `outcome == "exploration"` (the board cannot agree),
`daio/governance/boardroom.py` hands the disagreement to the Dojo (`from_boardroom(session)`,
`supermajority`) — the documented Boardroom (t1) → Dojo (t2) escalation. Advisory + best-effort.

## Tests

`tests/test_dojo_arbiter.py` — every consensus model, each normalizer, the dissent path, and
the three-sink recording with isolated tmp paths (`python -m pytest tests/test_dojo_arbiter.py`).
