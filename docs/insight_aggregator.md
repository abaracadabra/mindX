# InsightAggregator — the diagnostic data pipeline

**File:** [`mindx_backend_service/insight_aggregator.py`](../mindx_backend_service/insight_aggregator.py)
**Surface:** every `/insight/*` endpoint (and through them, `/feedback.html`, `/feedback.txt`, and the landing dashboard's Self-Improvement Ledger row).

The aggregator is the single async loop that turns mindX's append-only logs and per-agent files into the cached numerical surface the operator sees. **Nothing else owns these numbers.** If something on the page reads wrong, it's wrong here.

## Cadence

- Singleton, started from `main_service.startup_event`.
- Recomputes every **60 seconds** (`interval_s = 60`).
- Each recompute reads files from disk; never blocks the request path. The `/insight/*` endpoints return cached snapshots, never recompute inline.
- A **daily snapshot** is persisted to `data/fitness/daily_snapshots.jsonl` for trajectory queries.

## Inputs (read each cycle)

| Source | Path | Purpose |
|---|---|---|
| Mastermind campaign history | `data/memory/agent_workspaces/mastermind_prime/mastermind_campaigns_history.json` | source for ledger / improvement summary buckets |
| Per-agent process traces | `data/memory/agent_workspaces/{agent_id}/process_trace.jsonl` | trace-reliability, latency-score |
| Boardroom sessions | `data/governance/boardroom_sessions.jsonl` | consensus-alignment fitness axis |
| Dojo events | `data/governance/dojo_events.jsonl` | reputation-momentum |
| Gödel choices | `data/logs/godel_choices.jsonl` | godel-selection-rate axis + ledger join |
| Beliefs | `data/memory/beliefs.json` | learning-velocity, identity map |
| Model performance metrics | `data/model_performance_metrics.json` | latency-score |
| Improvement backlog | `data/improvement_backlog.json` | directive-coverage |
| Agent registry | `daio/agents/agent_map.json` | agent list for fitness leaderboard |

The aggregator handles missing files gracefully — every reader returns a sensible empty default, never raises into the request path.

## Outputs (cached, served to API)

### `improvement_summary()` → 4 + 1 buckets

Returned by `GET /insight/improvement/summary`. Three time-window buckets plus directive coverage.

```python
{
  "campaigns_1h":  {total, succeeded, running, errored, failed, blocked},
  "campaigns_24h": {total, succeeded, running, errored, failed, blocked},
  "campaigns_7d":  {total, succeeded, running, errored, failed, blocked},
  "belief_churn_per_hour": float,
  "model_quality_trend": {model_id: {success_rate, avg_latency_ms, avg_quality, last_used}},
  "directive_coverage": {
    "backlog_total":               int,  # how many improvement suggestions on disk
    "distinct_directives_attempted": int, # unique directive strings ever attempted
    "total_campaigns":             int,  # campaigns ever recorded
    "matched_in_backlog":          int,  # legacy substring match (kept for back-compat)
    "attempted":                   int,  # alias for distinct_directives_attempted
    "coverage_ratio":              float # distinct / backlog_total
  }
}
```

**Bucket size approximation.** Production campaign records do not carry timestamps. The aggregator approximates time windows by **list-tail slices**:

| Window | Slice |
|---|---|
| `campaigns_1h` | last 5 records |
| `campaigns_24h` | last 25 records |
| `campaigns_7d` | last 100 records |

This is honest given the data shape but **not exact** — if the system ran a thousand campaigns in 1 hour the 24h bucket only sees the last 25. A future version should add `created_at` timestamps to the campaign records and switch to time-range queries.

### Classification (the 5-state machine)

Every campaign passes through `bucket()` in `_compute_improvement_summary`. The mastermind sets `overall_campaign_status="FAILURE_OR_INCOMPLETE"` for *any* non-success outcome, collapsing 4 materially different states into one. The actual outcome lives in `final_bdi_message` — the aggregator reads that first.

```text
                final_bdi_message               | bucket
─────────────────────────────────────────────────|──────────
contains "COMPLETED_GOAL_ACHIEVED"               | succeeded
status == "SUCCESS"                              | succeeded
contains "CYCLE EXCEPTION"                       | errored
contains "FAILED" (FAILED_PLANNING, FAILED, …)   | failed
contains "RUNNING"  (BDI run RUNNING. Reason: …) | running
status == "RUNNING" or "IN_PROGRESS"             | running
status contains "BLOCK"                          | blocked
otherwise                                        | failed (truly unknown)
```

**Why these 5 states are not 1.**
- **succeeded** = goal achieved; agent applied wisdom or the LLM produced a working plan.
- **running (max-cycle)** = BDI loop hit `max_cycles` without crashing, typically because the skeleton fallback ran NO_OP repeatedly. Distinct from a real failure — the loop didn't error, it just ran out of time.
- **errored** = unhandled `Cycle Exception` — usually a bug in a tool or in the BDI itself.
- **failed** = explicit `FAILED_PLANNING`, `FAILED_EXECUTION`, or `FAILED_RECOVERY` — the BDI gave up cleanly.
- **blocked** = the campaign was refused before BDI ran (e.g., refused-because-failed-3×).

The math invariant: `succeeded + running + errored + failed + blocked == total`. The feedback page renders a `!math:N` warning if this ever fails.

### `snapshot()` → fitness leaderboard

Returned by `GET /insight/fitness`. Per-agent rollup of 7 fitness axes, weighted into a single 0–100 score. Code: `_compute_fitness_for_agent`.

| Axis | Weight | Source | Floor |
|---|---|---|---|
| `campaign_success`     | 0.25 | mastermind_campaigns_history | 50 (neutral) |
| `trace_reliability`    | 0.20 | process_trace success rate   | 50 |
| `latency_score`        | 0.10 | EMA of process latency       | 50 |
| `consensus_alignment`  | 0.15 | boardroom vote-with-majority | 50 |
| `reputation_momentum`  | 0.10 | 7-day dojo events delta      | 50 |
| `learning_velocity`    | 0.10 | new/updated beliefs in 24h   | 50 |
| `godel_selection_rate` | 0.10 | chosen / options_considered  | 50 |

`fitness = sum(axis_value × weight)`. Scores cluster around 50 when there's no data. This is intentional — neutral when uncertain, not zero.

### `trajectory(agent_id, days)` → fitness over time

Reads daily snapshots back N days. Used by `/insight/fitness/{agent_id}/trajectory` and the dashboard heatmap.

## How to read failures

If the page shows wrong numbers, check in this order:

1. **Source file format.** Did the writer schema change? A `final_bdi_message` field renamed to `bdi_message` would silently classify everything as failed.
2. **Bucket-tail slicing.** If the aggregator says `campaigns_24h: 25 total` but the timeline shows 200, that's the slice approximation — not a bug, but worth surfacing.
3. **Math invariant.** Open the browser console while on `/feedback.html` improvement ledger. If `!math:N` appears, one of the classifier branches isn't firing.
4. **Cache freshness.** `computed_at` is in every response. If it's >120s old, the aggregator loop crashed — check `data/logs/mindx_runtime.log` for `[insight] loop iteration failed`.
5. **Stale daily snapshot.** Trajectory queries pull from `data/fitness/daily_snapshots.jsonl`. If that's older than 24h the loop wasn't able to write it (disk full, perms, etc.).

## How to extend

To add a new aggregated metric:

1. Add a field to `ImprovementSummary` (or a sibling dataclass).
2. Compute it inside `_compute_improvement_summary` (or a new `_compute_*` method).
3. Surface it via `agg.improvement_summary()` to `/insight/improvement/summary`.
4. Render it in `feedback.html` and (optionally) `text_render.py` for `?h=true`.
5. Document it here.

The aggregator is the single chokepoint — nothing on the surface should compute its own statistics. That guarantee is the page's truth contract.

## Related

- [`/feedback.html`](https://mindx.pythai.net/feedback.html) — the operator surface
- [`/feedback.txt`](https://mindx.pythai.net/feedback.txt) — terminal-friendly snapshot
- [`?h=true` on every `/insight/*`](NAV.md#mind-of-mindx-insight-endpoints) — plain-text rendering
- [Cognitive ascent chain](../mindx_backend_service/main_service.py) — `/insight/cognition` shows where mindX is genuinely producing vs aspirational
- [Dashboard ledger row](../mindx_backend_service/dashboard.html) — uses the same `improvement_summary()` data
- [Plan: feedback redesign](../../.claude/plans/) — the design intent behind the 5-state classification
