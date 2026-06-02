# Resource Governance — How mindX Shares the Processor

I run in production on a **2-core / 8GB Hostinger VPS** that I share with PostgreSQL,
Apache, pmVPN, and a separate **ollama** inference process. The constraints are
features. I govern my own resource consumption so my autonomous work never starves
the web service that lets the world watch me think — *"I control my own resource
appetite … I coexist."*

This is the operational contract behind that principle.

## The two layers

### 1. `ResourceGovernor` modes (RAM + CPU appetite)

[`agents/resource_governor.py`](../agents/resource_governor.py) is a singleton that
monitors system pressure every 30s and auto-adjusts between four modes based on
neighbor-service load and available RAM:

| Mode | max RAM | max CPU | When |
|------|---------|---------|------|
| greedy | 85% | 90% | VPS idle — maximum inference |
| balanced | 65% | 70% | normal — fair share with neighbors |
| generous | 45% | 50% | neighbors busy — yield |
| minimal | 30% | 30% | survival — unload models, skip non-essential work |

It is enforced at the heartbeat (`should_skip_heartbeat()`) and feeds the
diagnostics dashboard ("power management").

### 2. Dynamic CPU ceiling (the autonomous loop yields)

The autonomous loops and background inference are gated by a **dynamic CPU ceiling**
(default **92%**). This is the same family as the documented `max_cpu_before_sia`
gate — graceful degradation, *not* a hard throttle: full speed when the box is idle,
yields under pressure.

Before the heavy (inference-driven) part of each cycle, both
[`mastermind_agent._run_autonomous_loop`](../agents/orchestration/mastermind_agent.py)
and [`mindXagent._autonomous_improvement_loop`](../agents/core/mindXagent.py) call
`ResourceGovernor.throttle_for_cpu(...)`. If system CPU is over the ceiling, the loop
backs off in a bounded loop (5s → ×1.5 → cap 30s) and, if still saturated, **defers
the campaign/cycle** rather than piling heavy inference onto a busy CPU. Mastermind
treats a deferral as "no campaign this cycle" so it never burns the backlog item's
24h dedup slot.

Background work that the loop doesn't own also yields, because it drives the same
ollama process:

- **Embeddings** ([`memory_pgvector.generate_embedding`](../agents/memory_pgvector.py))
  — when over the ceiling, the local-ollama embed is **deferred** (returns `None`,
  retried at a lower-load moment) instead of piling onto a saturated engine. It is
  also serialized through a background-only semaphore (size 1 on the 2-core box) so a
  burst can't peg both cores. Interactive/web-triggered embeds bypass the gate.
- **Gödel-choice evaluation** ([`memory_agent._score_godel_choice`](../agents/memory_agent.py))
  — the GEval judge falls back to local CPU inference under cloud-tier exhaustion
  (40s+ model loads that thrash a 2-core box). It is **skipped** when over the
  ceiling; the choice is still logged, just without a coherence score.

Sync `rglob` file-walks (`machine_dreaming._dir_size`, the author-journal memory
count) are moved off the event loop via `run_in_executor` so they never stall serving.

**Fail-open everywhere.** Any CPU-sensor error lets work proceed — the gate can never
hang the loop or block all inference. Local inference is always the failsafe.

## Why the in-process gate isn't enough alone — and the cap-free fix

All local inference is async HTTP to a **separate ollama process**. The Python event
loop is therefore not directly CPU-bound by inference — the hog is ollama, driven by
my demand. The gate reduces that demand, but it cannot stop ollama from monopolizing
both cores *during* an inference it is already running, which starves the FastAPI
event loop (even `/health` stalls).

On a 2-core box, closing that gap requires an **OS scheduling hint** — a *priority*,
not a cap. Persistent systemd drop-ins express "share the processor" at the kernel:

```
# /etc/systemd/system/ollama.service.d/cpushare.conf
[Service]
CPUWeight=50
Nice=10

# /etc/systemd/system/mindx.service.d/cpushare.conf
[Service]
CPUWeight=200
```

This gives the web service a 4:1 scheduling preference **only under contention** —
ollama still uses 100% of the CPU when the box is idle. It is not a CPUQuota; nothing
is capped. Apply with `systemctl daemon-reload && systemctl restart ollama`.

## Configuration

| Knob | Default | Env override |
|------|---------|--------------|
| Autonomous CPU ceiling (%) | 92 | `MINDX_MAX_AUTONOMOUS_CPU` |
| Background inference concurrency | 1 | `MINDX_INFERENCE_CONCURRENCY` |
| Governor mode | auto (balanced start) | `POST /resources/status` set-mode |

JSON config keys (under the `resource.` namespace): `max_autonomous_loop_cpu`,
`inference_concurrency`.

## Observability

The live reading is surfaced on [`/diagnostics/live`](https://mindx.pythai.net/diagnostics/live)
under `governor.cpu`:

```json
"governor": {
  "mode": "balanced",
  "cpu": { "current": 85.3, "ceiling": 92.0, "headroom": 6.7,
           "throttling": false, "throttle_label": null }
}
```

`throttling: true` with a `throttle_label` ("mastermind" / "mindx_loop") means a loop
is actively backing off. The public dashboard renders this as the **"CPU (live)"**
row. Mode + limits are also at `GET /resources/status`.

## Related

- [Autonomous Operation](AUTONOMOUS.md) — the loops that consult the gate
- [Inference Budget](INFERENCE_BUDGET.md) — the per-provider rate-limit "metabolism"
  that routes cloud → router → local (orthogonal: rate limits vs CPU)
- [Production Deployment](DEPLOYMENT_MINDX_PYTHAI_NET.md) — the VPS I coexist on
