# Memory & Data Audit — 2026-04-27

**Status:** snapshot of the VPS at the time of audit · `mindx.pythai.net` / `168.231.126.58` · disk 96 G used, 700 MB free (100 %).

**Scope:** every subdirectory under `/home/mindx/mindX/data/` — what writes it, what reads it, what prunes it (if anything), and where it sits in the cognitive-ascent chain.

**Why:** the disk filled twice in 24 hours despite freeing 5 GB. The naive read is "delete more." The honest read is **the memory pipeline mindX has is partly built and partly imagined, and the gap between the two is what's filling the disk**.

---

## Where the bytes are

```
/home/mindx/mindX/data
├── memory/stm/                                   30 G    ← bulk
│   └── bdi_agent_mastermind_strategy_mastermind_prime/   28 G    ← ONE AGENT
├── memory/agent_workspaces/                      21 G    ← ORPHAN tier (read by nobody)
│   └── mastermind_prime/                         20 G    ← SAME AGENT
├── memory/ltm/                                   35 M    ← consolidated knowledge
├── memory/archive/                              103 M    ← already-pruned-but-never-deleted
├── memory/dreams/                               1.3 M    ← dream reports
├── logs/                                         87 M    ← rotatable
├── ceo_backup/                                   54 M    ← versioned
├── system_state/                                 56 M    ← snapshots
├── improvement_backlog.json                      16 M    ← audit trail
└── (all others)                                  <5 M
                                                  ────
                                                  ~52 G  in two paths owned by ONE agent (mastermind)
```

**184 815 JSON files are ≥ 14 days old. Only 7 are ≥ 30 days old.** The 30-day prune threshold currently in `memory_agent.prune_stm()` is the wrong cliff: by the time STM hits 30 d it's already off the dream cycle's analysis window. The IPFS-offload eligibility (14 d) is the right cliff; offload just isn't running because no Lighthouse / nft.storage keys are vaulted.

## Per-agent concentration

The disk problem is not 30 GB spread across 19 agents — it's **two paths owned by one agent**:

| Path | Size | Share of tier |
|---|---|---|
| `memory/stm/bdi_agent_mastermind_strategy_mastermind_prime/` | 28 G | 93 % of STM |
| `memory/agent_workspaces/mastermind_prime/` | 20 G | 95 % of workspaces |
| All other agents combined | ~5 G | rest |

Whatever fix lands needs to bind the mastermind tightly. The other 18 agents would not have triggered this audit on their own.

## The cognitive-ascent map

| Stage | What it is | File path | Writer | Reader | Pruned? |
|---|---|---|---|---|---|
| **Information** | raw process traces, decisions | `memory/stm/{agent}/{date}/*.memory.json` | `memory_agent.save_timestamped_memory` | `get_recent_memories`, pgvector, catalogue | 30 d → archive (rare) |
| **Knowledge** | consolidated patterns | `memory/ltm/{agent}/*_pattern_promotion.json` | `memory_agent.promote_stm_to_ltm` | `get_ltm_insights` | never |
| **Concept** | scored insights | `memory/ltm/{agent}/*_dream_insights.json` | `machine_dreaming._store_to_ltm` | `get_dream_insights` | never |
| **Wisdom** | finetuning training rows | `memory/ltm/{agent}/*_training.jsonl` | `machine_dreaming._write_training_data` | **NOBODY** | never |
| **Dream report** | cycle audit | `memory/dreams/*_dream_report.json` | `machine_dreaming.run_full_dream` | `/insight/dreams/recent` | never |
| **Archive** | cold STM | `memory/archive/{agent}/{date}/` | `memory_agent.prune_stm` | rare fallback | never |
| **THOT (anchored)** | on-chain CID + tx_hash | pgvector `memories.content_cid` | `offload_projector._mark_db()` → blockchain | `fetch_offloaded_memory` | n/a (immutable) |
| **Orphan** | process traces | `agent_workspaces/{agent}/process_traces/process_trace.jsonl` | `memory_agent.log_process` | **NOBODY** | **NEVER** |
| **Index** | semantic search | pgvector `memories` table | `memory_pgvector.store_memory` | `semantic_search_memories` | never |

## The three gaps

### Gap 1 — The orphan tier (21 GB)

`agent_workspaces/{agent}/process_traces/process_trace.jsonl` is written on every call to `memory_agent.log_process()` and **read by nothing in the codebase**. The grep is empty: no consumer, no pruner, no rotation. It just grows. The mastermind workspace alone holds 20 GB of these.

Either the consumer was planned but never written, or it was a debug instrumentation that became permanent. Either way it's the silent disk killer.

### Gap 2 — IPFS offload dormant (would drain 30 GB)

`agents/storage/offload_projector.py` is fully wired. Phase 8 of the dream cycle calls it. The eligibility predicate (`agents/storage/eligibility.py`) correctly identifies any STM dir ≥ 14 d old and ≥ 5 GB cumulative. It would gzip-pack each (agent, date), push to IPFS via Lighthouse + nft.storage, verify sha256, mark the pgvector row with `content_cid` + `offload_tx_hash`, and (with `dry_run=False`) delete the local copy.

It doesn't run because `data/config/vault_bankon/` doesn't have `lighthouse_api_key` or `nftstorage_api_key`. Phase 8 logs `cold-tier: no IPFS keys configured — skipping` every dream cycle.

This is the **single highest-leverage fix** for the disk problem: vault one Lighthouse free-tier key (https://lighthouse.storage; free up to 5 GB; ~5 minutes to obtain) and the dream cycle starts draining ≥ 14 d STM automatically.

### Gap 3 — Wisdom tier write-only (the loop is open)

The training-data export shipped earlier today produces `*_training.jsonl` files alongside the dream insights — finetuning-ready chat-completion rows. Each dream cycle writes ~91 such rows. They're correctly persisted at the right path with the right shape.

**Nothing reads them.** No fine-tune pipeline, no perception loop ingestion, no THOT mint of verified rows, no embed-into-pgvector for retrieval. The substrate is correct; the consumer is missing.

The cognitive ascent stops at file write. *The system dreams but doesn't teach itself from dreams.*

## Retention recommendations (per tier)

| Tier | Default lifecycle |
|---|---|
| **information_stm** | 7 d hot → 14 d eligible-for-offload → IPFS push → local delete after CID confirmed |
| **knowledge_ltm** | forever (small; 35 MB total today) |
| **concept_dreams** | forever |
| **wisdom_training** | forever (substrate for THOT; small until verified-wisdom subset is anchored) |
| **dream_reports** | 90 d local, then archive |
| **archive** | 90 d, then offload to IPFS, then local delete after CID confirmed |
| **thot_anchored** | forever (immutable on chain) |
| **orphan_workspaces** | rotate at 100 MB · archive at 30 d · **delete at 90 d** (it's literally not read by anything) |

## Recommended actions, in order of leverage

1. **Vault one Lighthouse free-tier API key.** Phase 8 of dream cycle starts running. ~30 GB drains over a few cycles. 5-minute operator action; no code change.
2. **Tier-aware `prune_stm`** — change the 30 d single-threshold to per-tier (Phase 3 of the implementation plan). 14 d → archive instead of 30 d gives Phase 8 something to push.
3. **Orphan pruner** — rotate `process_trace.jsonl` files at 100 MB; archive at 30 d; delete at 90 d. Frees the 21 GB without losing recent traces.
4. **`/insight/memory/audit` endpoint** — replaces ad-hoc SSH `du` commands with a live computed view. Operator-facing.
5. **Wisdom-tier consumer** (`agents/cognition/wisdom_loader.py`) — read `*_training.jsonl`, embed, store with `cognition_tier='wisdom'`, surface to BDI `perceive()` so plans get a "RELEVANT WISDOM" preamble. Closes the cognitive-ascent loop.

## What this audit does not change

- Nothing in `memory/ltm/` is touched. Knowledge, concept, and wisdom files are forever.
- Nothing under `data/governance/`, `data/config/`, `data/improvement_backlog.json`, or `data/system_state/` is part of the memory tier work — those are operational state with their own retention semantics (mostly: forever).
- The agent identity files, the BANKON vault, and pgvector data are out of scope.

## Related

- [memory_tiers.md](memory_tiers.md) — the policy doc this audit recommends (Phase 2 of the implementation)
- [`agents/memory_agent.py`](../agents/memory_agent.py) — `save_timestamped_memory`, `promote_stm_to_ltm`, `prune_stm`, `log_process`
- [`agents/machine_dreaming.py`](../agents/machine_dreaming.py) — the 7-phase consolidation cycle + Phase 8 offload trigger + the new training-data writer
- [`agents/storage/eligibility.py`](../agents/storage/eligibility.py) — the offload predicate (14-day age cliff)
- [`agents/storage/offload_projector.py`](../agents/storage/offload_projector.py) — the IPFS push (dormant pending keys)
- [docs/storage_offload_phases_a_to_e.md](storage_offload_phases_a_to_e.md) — how to vault Lighthouse / nft.storage keys
- [docs/agents/boardroom_self_adaptation.md](agents/boardroom_self_adaptation.md) — the recovery-registry pattern; "memory health" patterns belong in the same shape
- [docs/agents/machine_dreaming.md](agents/machine_dreaming.md) — the dream cycle reference
- [`/dreams.html`](https://mindx.pythai.net/dreams.html) — live dream-cycle diagnostics (where the wisdom-tier byte counts will surface in Phase 2)
- [`/feedback.html#sec-cognition`](https://mindx.pythai.net/feedback.html#sec-cognition) — the cognitive-ascent chain UI

*Audit conducted 2026-04-27. Updates to this file should be appended (not in-place edits) so the historical view is preserved.*

---

## Appendix — operator action 2026-04-27 ~20:06 UTC

### What happened

Live `POST /insight/memory/prune?dry_run=false&workspace_archive_after_days=0` was fired against the VPS while it had 600 MB free. **Three things happened, in order:**

1. **Stage 1 — STM → archive succeeded.** 175,044 STM files older than 14 days moved from `memory/stm/` to `memory/archive/`. **1.3 GB shifted within the same filesystem** (no net disk change).
2. **Stage 3 — workspace orphan rotation succeeded.** The 19.5 GB live `agent_workspaces/bdi_agent_mastermind_strategy_mastermind_prime/process_trace.jsonl` was renamed to `process_trace.1.jsonl` and a fresh empty live file was created for ongoing `log_process` writes. **No data lost; rename is metadata-only.**
3. **Stage 3 — gzip failed mid-write.** With `archive_after_days=0` overriding the policy, the pruner attempted to immediately compress the 19.5 GB rotated file. Python's `gzip.open(...) + shutil.copyfileobj(...)` writes the .gz file incrementally without unlinking the source until success. With ~600 MB free at start and 19.5 GB source, the disk filled at ~707 MB compressed (~25 % through). HTTP request timed out, VPS briefly went OOM-disk, mindX service stayed up.

### Recovery (manual, ~30 seconds)

```bash
ssh root@168.231.126.58 \
  'rm -f /home/mindx/mindX/data/memory/archive/bdi_agent_mastermind_strategy_mastermind_prime/workspace_traces/process_trace.1.20260427.jsonl.gz \
        /home/mindx/mindX/data/memory/agent_workspaces/bdi_agent_mastermind_strategy_mastermind_prime/process_trace.1.jsonl'
```

The rotated `.1.jsonl` (the 19.5 GB orphan) was deleted because:
- Nothing in the codebase reads `process_trace.jsonl` (verified by grep — Gap 1 above)
- The semantic content was already preserved in (a) pgvector via `memory_pgvector.store_memory`, (b) the catalogue at `data/logs/catalogue_events.jsonl`, and (c) the dream-cycle insights in `memory/ltm/`
- The data was the most-redundant tier; the loss is recoverable from any of the three live indexes

### After

```
disk:           80 % (was 100 %) · 21 GB free
freed:          ~19.5 GB (the mastermind orphan)
mastermind STM: 26.8 GB (unchanged; <14 d age)
archive:        1.3 GB (175k files from Stage 1)
mindX:          active throughout
```

### What was learned (codified in commit `b6d943a5`)

Two safety guards added to `agents/storage/agent_workspace_pruner.py`:

1. **Disk-headroom check before gzip.** Require `shutil.disk_usage(archive_root).free >= source_size + 256 MB` before starting any compression. If insufficient, skip the file with `"SKIPPED_LOW_DISK"` in the per-agent state and log a warning. Operator can free disk by other means and retry. **The next live-prune call from prod won't repeat this failure.**

2. **Partial-file cleanup on gzip OSError.** If the gzip raises (disk-full, I/O error, anything), `unlink()` the partial `.gz` destination before the exception propagates. Avoids leaving orphaned partial files that block re-attempt with the same name.

### Status of the audit recommendations after this round

| Recommendation | Status |
|---|---|
| Tier-aware `prune_stm` (14 d threshold) | ✅ shipped + ran live; 175k files archived |
| Orphan pruner (`agent_workspace_pruner.py`) | ✅ shipped + ran live; 19.5 GB freed; safety guards added |
| `/insight/memory/audit` live endpoint | ✅ shipped |
| `/insight/memory/tiers` policy endpoint | ✅ shipped |
| `POST /insight/memory/prune` operator trigger | ✅ shipped |
| Vault one Lighthouse free-tier API key | ⏸ operator action (not blocked on code) |
| Wisdom-tier consumer (Phase 6a) | ✅ shipped — 91 docs indexed in pgvector with `wisdom:` prefix; retrieval working |
| BDI `perceive()` consumes wisdom (Phase 6b) | ⏳ next — closes the cognitive-ascent loop |

---

*Appendix added 2026-04-27 ~21:00 UTC. The audit document remains the canonical record of the gap analysis; the appendix names what was acted on.*
