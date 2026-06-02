# Why netdata in Phase 1.2 — the smartphone-class reframe

## The constraint

mindX runs on a Hostinger VPS: **8 GB RAM, 2 CPU cores, ~96 GB disk** (18 GB free at last check). The `autotune/` package is being perfected against a ~1.5 GB local model, with bursty inference workloads that want most of one core during probes. mindX's BDI + AGInt + boardroom + memory + dream cycles + Ollama + Postgres + Apache + Express frontend collectively want ~5-6 GB resident in steady state.

That leaves ~2 GB headroom for everything else: incoming traffic spikes, Linux kernel buffers, swap reserve, and the monitoring stack.

## The wrong question

Phase 1 of the blueprint asked: "what's the right enterprise observability stack?" Answer: Prometheus + Thanos + Grafana + OTel Collector + Langfuse + Jaeger + DeepEval + ... — a stack designed for fleet-scale workloads where 1 GB of telemetry RAM is rounding error.

Phase 1.1 trimmed that to ~416 MB resident with Grafana off-by-default. Better, but still: the box is constantly running 4 daemons whose only job is to be ready in case an operator wants a PromQL query.

## The right question

**This VPS is a flagship-class phone, not an enterprise host.** A Pixel 8 has 8 GB RAM and runs Android, Chrome, Spotify, Signal, and an LLM all at once. It does not run a 24/7 TSDB.

The phone monitoring story:
- **`dumpsys`** — point-in-time state snapshot. Run when you want it; nothing persistent.
- **`logcat`** — in-memory ring buffer of recent events. Old entries discarded.
- **`perfetto`** — on-demand kernel + userspace trace, recorded when an investigation starts and stopped when it ends.
- **The vitals widget** — always-on tiny indicator: battery %, signal bars, CPU/RAM swirl (in dev menu). Updates per-second, costs ~nothing.

Translation to mindX VPS:
- **`mindx-stat`** = `dumpsys` (already shipped in Phase 1.1)
- **`journalctl`** = `logcat` (always there)
- **`prom_on.sh` → PromQL → `prom_off.sh`** = `perfetto` on-demand trace
- **netdata** = the vitals widget — always on, ~200 MB, real-time charts, smartphone-class footprint

## Why netdata specifically

Three properties mattered:

1. **Single-process, single-port, single-binary** — runs in one container, exposes one HTTP port, no companion processes (no Postgres, no ClickHouse, no Redis). Unlike Langfuse which needs 5+ services and ~2 GB collectively just to start.

2. **Real-time per-second charts with 0 config** — out of the box, netdata produces the kind of "tap the screen, see what's happening right now" UX a phone vitals widget gives you. No PromQL learning curve.

3. **1-day in-memory dbengine retention** — phones don't keep a week of history. netdata's dbengine can be tuned down to 1 day (set in `netdata_config/netdata.conf`), which keeps RAM at ~200 MB instead of 500+.

## Why Prom + Grafana stay (off by default)

For the same reason a developer keeps perfetto/strace/wireshark installed but unused: when you need them, you need them now, and reinstalling under incident pressure is the wrong move.

- **Prom history** — when an incident hits, `prom_on.sh` brings 3 days of TSDB online for retrospective PromQL queries. netdata only has 1 day of in-memory data; Prom is the longer-term complement.
- **Email alerts** — Alertmanager + Gmail SMTP is the paging surface. armed only when Prom is up. Phase 1.5 will add a true dead-man's-switch separately.
- **Grafana dashboards** — `node_exporter_full` and the eval/agent-loop dashboards (Phase 2) are too rich for ad-hoc netdata views. Brought up via `grafana_on.sh` for incident retrospectives.

## RAM budget delta

| State | Phase 1 | Phase 1.1 | Phase 1.2 |
|---|---|---|---|
| Default-on resident | ~1100 MB (all 6 units) | ~416 MB (Grafana off) | **~256 MB (netdata only)** |
| Active deep-dive | ~1100 MB | ~608 MB | ~672 MB (Prom stack + netdata) |
| Full deep-dive | ~1100 MB | ~608 MB | ~864 MB (Prom + Grafana + netdata) |

Phase 1.2 default-on is **3-4× lighter** than Phase 1 default. mindX gets back ~750 MB of resident RAM that previously sat being "ready in case operator wants Grafana."

## CPU budget delta

netdata default: `CPUQuota=15%` of 2 cores = 0.3 core (per `podman_quadlets/netdata.container`).
Full deep-dive (Prom + AM + node + blackbox + netdata + Grafana): 50% = 0.5 core.

mindX retains ≥1.5 cores in every state, leaving headroom for autotune probes.

## Why "Android compatible" matters but is deferred

The operator flagged "mindX may run handheld yet." Phase 1.2 stays VPS-only but is designed to port:

- All five container images publish arm64 builds (verified: `docker.io/netdata/netdata`, `quay.io/prometheus/*`).
- All shell scripts are POSIX-clean — no `apt`-specific assumptions in `obs_on.sh` / `obs_off.sh` / `mindx-stat`.
- The Python TUI in `cli/mindx_stat_tui.py` uses stdlib + psutil only, both present on Termux.
- netdata's binary runs on Android via Termux per upstream support matrix.

Phase 1.3 or later: if mindX runs on a handheld, Phase 1.2's monitoring stack is one apt-install away from working. No restructuring needed.

## Summary one-liner

mindX's VPS is a phone, not a server. Phase 1.2 monitors it like a phone — vitals always-on, deep tools on-demand.
