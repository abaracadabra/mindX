# mindx_observability

VPS monitoring for mindx.pythai.net via rootless Podman Quadlets, sized for a smartphone-class host (8 GB / 2 CPU).

**Phase 1.2 architecture** (current): **netdata** is the always-on daily UI (~256 MB). Prometheus + Grafana + Alertmanager + node_exporter + blackbox_exporter are all OFF by default — brought up on-demand via `scripts/prom_on.sh` for PromQL sessions or paging.

| Component | Always-on? | Image (pinned) | RAM cap | URL |
|---|---|---|---|---|
| **netdata** 2.5.0 | ✅ yes | `docker.io/netdata/netdata:v2.5.0` | 256 MB | https://netdata.pythai.net |
| Prometheus 3.11.1 | ❌ on-demand | `quay.io/prometheus/prometheus:v3.11.1` | 256 MB | https://prom.pythai.net |
| Grafana 13.0.1 | ❌ on-demand | `docker.io/grafana/grafana:13.0.1` | 192 MB | https://grafana.pythai.net |
| Alertmanager 0.32.0 | ❌ on-demand | `quay.io/prometheus/alertmanager:v0.32.0` | 48 MB | https://alerts.pythai.net |
| node_exporter 1.11.1 | ❌ on-demand | `quay.io/prometheus/node-exporter:v1.11.1` | 64 MB | loopback only |
| blackbox_exporter 0.27.0 | ❌ on-demand | `quay.io/prometheus/blackbox-exporter:v0.27.0` | 48 MB | loopback only |

**Default-on resident**: ~256 MB. **Prom-stack-on**: +416 MB. **Full deep-dive**: +192 MB. mindX retains ≥1.5 cores in every state.

**Why netdata is primary**: see `docs/why_netdata_phase_1_2.md` (smartphone-class reframe).
**License flag**: see `docs/netdata_license.md` (GPL-3 Agent + proprietary UI — mitigation paths documented).

## Layout

```
prometheus/        scrape config + alert/recording rules
alertmanager/      routing config (Gmail SMTP to tokindex@gmail.com)
blackbox/          http_2xx prober module
grafana/           grafana.ini + provisioning (datasource + dashboards)
podman_quadlets/   rootless Quadlet units (.network + 5 .container)
apache/            6 vhost files (http→https + le-ssl per subdomain)
scripts/           bootstrap_vps.sh · deploy_quadlets.sh · verify_pipeline.sh · teardown.sh
docs/              runbook_phase1.md · rollback.md · adding_new_blackbox_target.md
```

## Lint (local, before any deploy)

```bash
bash scripts/lint.sh
```

Runs `promtool check config`, `promtool check rules`, `amtool check-config`,
blackbox `--config.check`, plus YAML/JSON/bash syntax over the whole tree using the same
image versions pinned in `podman_quadlets/`. Requires Docker on the local machine.

## Daily operations (Phase 1.2)

```bash
# Web UI (always-on)
open https://netdata.pythai.net          # daily monitoring

# Text dashboard (no UI needed)
mindx-stat all                            # top / disk / probes / alerts / netdata
mindx-stat netdata                        # netdata API status

# Bring full Prom stack up for incident or PromQL session
bash scripts/prom_on.sh
# ... investigate ...
bash scripts/prom_off.sh                  # frees ~416 MB

# Optional Grafana dashboards
bash scripts/grafana_on.sh                # implies prom_on too
bash scripts/grafana_off.sh

# Per-service on/off
bash scripts/netdata_on.sh / netdata_off.sh

# Full kill switch (stops EVERYTHING)
bash scripts/obs_off.sh
```

## Deploy

Full plan: `/home/hacker/.claude/plans/breezy-strolling-anchor.md`
Ops runbook: `docs/runbook_phase1.md`

In short:
1. Add A records `prom.pythai.net`, `grafana.pythai.net`, `alerts.pythai.net` → `168.231.126.58` at Hostinger DNS.
2. `ssh root@168.231.126.58` → `bash scripts/bootstrap_vps.sh` (one-time).
3. rsync this directory to `/root/mindx_observability/` on VPS → `bash scripts/deploy_quadlets.sh`.
4. `cp apache/*.conf /etc/apache2/sites-available/` → `a2ensite` → `certbot --apache -d prom.pythai.net -d grafana.pythai.net -d alerts.pythai.net`.
5. `PROM_PASS=... bash scripts/verify_pipeline.sh`.

## Why this exists

mindX live diagnostics today are app-internal: `/insight/*` JSON endpoints, `/feedback.html`, `/feedback.txt`, `data/logs/catalogue_events.jsonl`. No Prometheus exposition format, no industry-standard scrape surface. Until this Phase 1 lands, "is mindx.pythai.net up?" is answered by manual `curl` or user complaint. After Phase 1, it's a 2-minute paging SLO with a Grafana panel.

## Deviations from the full blueprint (intentional)

- Retention 7d / 8 GB cap (blueprint specifies 15d) — disk constraint.
- No Thanos / SeaweedFS / OTel Collector / Jaeger / Langfuse / Pushgateway — Phase 2+.
- Apache2 reverse proxy (existing) instead of Caddy v2.
- Apache Basic Auth + Grafana built-in auth instead of Keycloak OIDC — single operator.

License: Apache 2.0.
