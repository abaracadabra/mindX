# Rollback

Three tiers, escalating severity. All run from root on `168.231.126.58`.

## Tier 1 — fast relief (heaviest units only)

Use when memory pressure is rising but the box is still responsive.

```bash
TIER=1 bash /root/mindx_observability/scripts/teardown.sh
# stops: prometheus.service, grafana.service
# keeps: alertmanager, node-exporter, blackbox-exporter (small RAM footprint)
# data:  TSDB + Grafana DB intact, restart resumes with history
```

## Tier 2 — full stack down

Use when something is misbehaving and you want the whole obs surface gone.

```bash
TIER=2 bash /root/mindx_observability/scripts/teardown.sh
# stops: all 5 obs containers
# data:  intact — restart with `systemctl --user start <unit>.service` as mindx
```

## Tier 3 — wipe TSDB

Use only if `du -sh /home/mindx/obs/prometheus_data` shows the TSDB exceeded the 8 GB cap and disk is the active failure mode.

```bash
TIER=3 bash /root/mindx_observability/scripts/teardown.sh
# stops: prometheus.service
# wipes: /home/mindx/obs/prometheus_data/*
# restart: sudo -u mindx XDG_RUNTIME_DIR=/run/user/1002 systemctl --user start prometheus.service
```

## Full removal (uninstall Phase 1)

If Phase 1 needs to come out entirely (e.g. to free RAM during an incident, or to replace with Phase 2):

```bash
# 1. stop and disable all obs units
sudo -u mindx XDG_RUNTIME_DIR=/run/user/1002 \
    systemctl --user stop prometheus grafana alertmanager node-exporter blackbox-exporter

# 2. remove Quadlet files (containers stay stopped after daemon-reload)
rm /home/mindx/.config/containers/systemd/{obs.network,prometheus.container,grafana.container,alertmanager.container,node_exporter.container,blackbox_exporter.container}
sudo -u mindx XDG_RUNTIME_DIR=/run/user/1002 systemctl --user daemon-reload

# 3. (optional) prune images and data
sudo -u mindx podman image prune -af
rm -rf /home/mindx/obs/

# 4. remove Apache vhosts
a2dissite prom.pythai.net grafana.pythai.net alerts.pythai.net
rm /etc/apache2/sites-available/{prom,grafana,alerts}.pythai.net*.conf
systemctl reload apache2

# 5. (optional) revoke TLS certs
certbot delete --cert-name prom.pythai.net
certbot delete --cert-name grafana.pythai.net
certbot delete --cert-name alerts.pythai.net

# 6. (optional) remove swap
swapoff /swapfile && rm /swapfile && sed -i '/\/swapfile/d' /etc/fstab

# 7. (optional) remove DNS records at Hostinger panel
```

## Apache vhost state during obs outage

If Prom/Grafana/Alertmanager are stopped but Apache vhosts remain enabled, the public URLs return **502 Bad Gateway** (proxy can't reach loopback). This is harmless — no need to `a2dissite` unless you want the public surface gone.

## Pre-incident heartbeat

`PrometheusSelfDown` only fires while Prometheus is up enough to evaluate it. A true dead-man's-switch (Phase 1.5) needs an external pinger:

```bash
# laptop cron, every 5 min
*/5 * * * * curl -fsS https://prom.pythai.net/-/healthy -u "ops:$PROM_PASS" > /dev/null || \
    curl -X POST https://hc-ping.com/<uuid>/fail
```
