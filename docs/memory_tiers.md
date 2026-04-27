# Memory Tiers — retention policy

The policy doc the [memory audit](MEMORY_AUDIT_2026_04_27.md) recommended. **One row per /data path, one source of truth for "how long does this live."** Retention is enforced by `agents/memory_agent.py:prune_stm` (tier-aware) and `agents/storage/agent_workspace_pruner.py` (orphan tier). Live byte counts are surfaced at `/insight/memory/tiers` and `/insight/memory/audit`.

## The eight tiers

| Tier | Path | Cognitive role | Lifecycle | Default policy |
|---|---|---|---|---|
| **information_stm** | `memory/stm/{agent}/{date}/*.memory.json` | raw experience | hot for 7 d → eligible-for-offload at 14 d → IPFS push → local delete after CID confirmed | `information_max_age_days=14` |
| **archive** | `memory/archive/{agent}/{date}/` | cold information | 90 d local → IPFS push → local delete after CID confirmed | `archive_max_age_days=90` |
| **knowledge_ltm** | `memory/ltm/{agent}/*_pattern_promotion.json` | consolidated patterns | **forever** (35 MB total today; growth is bounded by pattern-promotion rate, not raw volume) | never pruned |
| **concept_dreams** | `memory/ltm/{agent}/*_dream_insights.json` | scored insights | **forever** | never pruned |
| **wisdom_training** | `memory/ltm/{agent}/*_training.jsonl` | finetuning corpus | **forever** (substrate for THOT mints; growth ~3 KB / agent / dream cycle) | never pruned |
| **dream_reports** | `memory/dreams/*_dream_report.json` | cycle audit | 90 d local → archive | `dream_reports_max_age_days=90` |
| **thot_anchored** | pgvector `memories.content_cid` + on-chain | immutable wisdom | **forever** (on chain) | n/a — operator can't prune the chain |
| **orphan_workspaces** | `agent_workspaces/{agent}/process_traces/process_trace.jsonl` | unread process trace | rotate at 100 MB → archive at 30 d → **delete at 90 d** | `rotate_at_bytes=100MB`, `archive_after_days=30`, `delete_after_days=90` |

## Why each value

### `information_max_age_days = 14`

Was 30. The audit found 184 815 JSON files ≥ 14 d old but only 7 ≥ 30 d. The previous 30-day cliff was after the data had already aged out of the dream cycle's 7-day analysis window — pruning happened too late to help. **14 d aligns with `agents/storage/eligibility.py:min_age_days=14.0`** so STM transitions to *archive* exactly when it becomes eligible for IPFS offload. Same threshold, two systems agree.

### `archive_max_age_days = 90`

Cold tier. Three months gives operators time to investigate any incident referencing the pruned data before it gets pushed to IPFS. After 90 d AND the IPFS push is confirmed (CID present in pgvector + tx_hash), local copies can be deleted because retrieval still works through `memory_agent.fetch_offloaded_memory()`.

### `dream_reports_max_age_days = 90`

Same logic as archive. Reports are small (1.3 MB total for 88 reports today) so this could honestly be `forever` — but archiving keeps the `/insight/dreams/recent` page fast as the count grows over years.

### `orphan_workspaces` — rotate / archive / delete

The `process_trace.jsonl` files are read by nothing in the codebase. We can't prove they're useless — maybe an external consumer (debugger, log shipper) reads them out of band — so we **rotate-not-delete** at 100 MB to preserve recent traces, **archive at 30 d** for offline inspection, and only **delete at 90 d** once both the IPFS push has happened (if archived) and 90 d have passed (long enough that any forensic value is gone).

`MINDX_WORKSPACE_PRUNE_DISABLE=1` env disables this if anything turns out to need the live file.

### Why ltm/* is forever

`pattern_promotion.json`, `dream_insights.json`, `training.jsonl` are durable signals. They're small (35 MB total across all agents). They're the substrate for the cognitive ascent — concepts → wisdom → THOT. Pruning them would be like a brain forgetting verified facts to make room for sensory input.

Growth: bounded by pattern-extraction rate (~10–100 KB per agent per dream cycle, ~3 cycles/day), so on the order of 3 GB/year aggregate. Cheap.

## Hard guarantees

The pruner has three invariants enforced in code:

1. **Nothing under `memory/ltm/` is touched.** Knowledge, concept, wisdom — never pruned, never archived, never moved.
2. **No file is deleted until its IPFS CID is confirmed in pgvector** (offload-then-delete, never delete-then-push).
3. **Default `dry_run=True` everywhere.** Operator must explicitly set `dry_run=false` for any destructive action; admin auth gate enforces this for `/insight/memory/prune`.

## Endpoints

```
GET  /insight/memory/audit?h=true      # live byte counts per tier (Phase 1)
GET  /insight/memory/tiers?h=true      # this policy + live state (Phase 2)
POST /insight/memory/prune?dry_run=true  # operator-triggered prune (Phase 5)
```

The audit endpoint replaces ad-hoc SSH `du` commands. The tier endpoint surfaces this policy + the live state side by side. The prune endpoint, with `dry_run=false`, applies the policy.

## Related

- [MEMORY_AUDIT_2026_04_27.md](MEMORY_AUDIT_2026_04_27.md) — the audit that prompted this policy
- [`agents/memory_agent.py`](../agents/memory_agent.py) — implements the policy
- [`agents/storage/eligibility.py`](../agents/storage/eligibility.py) — IPFS offload eligibility (the 14-d cliff this aligns with)
- [`agents/storage/offload_projector.py`](../agents/storage/offload_projector.py) — the cold-tier push
- [storage_offload_phases_a_to_e.md](storage_offload_phases_a_to_e.md) — how to vault Lighthouse / nft.storage keys

*Last reviewed: 2026-04-27. Future updates should bump the date and append rationale for any change in the table.*
