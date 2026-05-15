# mindx_observability

Phase 1 of the observability blueprint — VPS-level monitoring for mindx.pythai.net via rootless Podman Quadlets.

**Stack:** Prometheus 3.11.1 · Grafana 13.0.1 · Alertmanager 0.32.0 · node_exporter 1.11.1 · blackbox_exporter 0.27.0
**Scope:** infra only — host metrics + HTTPS probes for the four pythai.net services. App-level `/metrics` instrumentation deferred to Phase 2.
**Surfaces:** `https://prom.pythai.net` (Basic Auth) · `https://grafana.pythai.net` (Grafana auth) · `https://alerts.pythai.net` (Basic Auth)

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
