# Phase 1 → 1.1 → 1.2 ops runbook

VPS: `168.231.126.58` (Hostinger) · user `mindx` (uid 1002) · mindX path `/home/mindx/mindX/`
Plan: `/home/hacker/.claude/plans/breezy-strolling-anchor.md`

> **Phase 1.2 is current.** netdata is the always-on monitoring UI; Prom stack is on-demand.
> Substitutions to Phase 1+1.1 below are called out at the end of this file.

## Prerequisites (operator does once, before any of this)

1. **Gmail app-password** at https://myaccount.google.com/apppasswords (16-char string, no spaces).
2. **Hostinger DNS** A records:
   ```
   prom.pythai.net.       A   168.231.126.58
   grafana.pythai.net.    A   168.231.126.58
   alerts.pythai.net.     A   168.231.126.58
   ```
3. Wait for DNS propagation: `dig +short prom.pythai.net @1.1.1.1` until non-empty.

## Deploy (operator runs as root on VPS)

```bash
# 1. Get this directory onto the VPS
rsync -av --delete /home/hacker/mindX/mindx_observability/ \
    root@168.231.126.58:/root/mindx_observability/

# 2. Bootstrap (apt install podman, 4 GB swap, enable-linger, mkdir tree)
ssh root@168.231.126.58 'bash /root/mindx_observability/scripts/bootstrap_vps.sh'

# 3. Place the SMTP app-password (single line, no trailing newline, chmod 600)
ssh root@168.231.126.58
  cat > /home/mindx/obs/alertmanager/smtp_app_password <<'EOF'
  PASTE-16-CHAR-GMAIL-APP-PASSWORD-HERE
  EOF
  chmod 600 /home/mindx/obs/alertmanager/smtp_app_password
  chown mindx:mindx /home/mindx/obs/alertmanager/smtp_app_password

# 4. Deploy Quadlets + start units
ssh root@168.231.126.58 'bash /root/mindx_observability/scripts/deploy_quadlets.sh'

# 5. Install Apache vhosts (http stubs only first, then certbot creates -le-ssl)
ssh root@168.231.126.58
  cp /root/mindx_observability/apache/prom.pythai.net.conf      /etc/apache2/sites-available/
  cp /root/mindx_observability/apache/grafana.pythai.net.conf   /etc/apache2/sites-available/
  cp /root/mindx_observability/apache/alerts.pythai.net.conf    /etc/apache2/sites-available/

  # htpasswd files
  htpasswd -cB /etc/apache2/htpasswd/prom.htpasswd   ops    # set 24+ char password
  htpasswd -cB /etc/apache2/htpasswd/alerts.htpasswd ops    # set different password

  # required mods
  a2enmod proxy proxy_http proxy_wstunnel rewrite headers ssl auth_basic
  a2ensite prom.pythai.net grafana.pythai.net alerts.pythai.net
  apachectl configtest && systemctl reload apache2

# 6. TLS via certbot
ssh root@168.231.126.58
  certbot --apache -d prom.pythai.net -d grafana.pythai.net -d alerts.pythai.net --redirect

# 7. CRITICAL: certbot may rewrite vhosts. Verify the -le-ssl.conf files match
#    /root/mindx_observability/apache/*-le-ssl.conf (especially ProxyPass blocks)
ssh root@168.231.126.58
  diff /etc/apache2/sites-available/prom.pythai.net-le-ssl.conf \
       /root/mindx_observability/apache/prom.pythai.net-le-ssl.conf || true
  # If diff shows missing ProxyPass blocks, re-copy our version:
  # cp /root/mindx_observability/apache/*-le-ssl.conf /etc/apache2/sites-available/
  # systemctl reload apache2

# 8. Verify the pipeline (the six checks)
PROM_PASS='<the-password-from-htpasswd>' bash /home/hacker/mindX/mindx_observability/scripts/verify_pipeline.sh
```

## First Grafana login

- URL: https://grafana.pythai.net
- Default admin user: `admin`
- Default admin password: `admin` → forced change on first login → store in your password manager
- Three provisioned dashboards under folder **mindX**: Node Exporter Full · Prometheus Overview · Blackbox Exporter

## Synthetic alert test (one-time)

```bash
ssh root@168.231.126.58
  sed -i 's|https://mindx.pythai.net/feedback.txt|https://mindx.pythai.net/intentional-404|' \
      /home/mindx/obs/prometheus/prometheus.yml
  curl -X POST -u "ops:PROM_PASS" https://prom.pythai.net/-/reload
  # wait 2m30s
  curl -s -u "ops:PROM_PASS" 'https://prom.pythai.net/api/v1/alerts' | jq '.data.alerts[]'
  # email should arrive at tokindex@gmail.com
  # revert
  sed -i 's|https://mindx.pythai.net/intentional-404|https://mindx.pythai.net/feedback.txt|' \
      /home/mindx/obs/prometheus/prometheus.yml
  curl -X POST -u "ops:PROM_PASS" https://prom.pythai.net/-/reload
```

## Rollback

See `rollback.md`. Quick reference:
- Tier 1 (stop Prom + Grafana, keep history): `TIER=1 bash scripts/teardown.sh`
- Tier 2 (stop all obs units): `TIER=2 bash scripts/teardown.sh`
- Tier 3 (wipe TSDB, last resort): `TIER=3 bash scripts/teardown.sh`

## Disk + RAM watchpoints

- `du -sh /home/mindx/obs/prometheus_data` should stay <4 GB (Phase 1.1 hard-cap)
- `free -h` available should stay ≥1.5 GB in Phase 1.2 default-on state
- `swapon --show` should show <2 GB used (>2 GB = thrashing warning)

---

# Phase 1.2 — substitutions to the above

## DNS (one more A record)

```
netdata.pythai.net. A 168.231.126.58 TTL 3600
```

(In addition to prom/grafana/alerts.pythai.net from Phase 1.)

## Bootstrap step deltas

- **Step 3** (apt) → use `bash scripts/install_deps.sh` (adds `git` for the netdata submodule + the Phase 1.1 text-tool deps).
- **Step 8** (rsync) → before rsync: `git submodule update --init --recursive` to populate `mindx_observability/vendor/netdata/`.
- **Step 12** (systemctl start) → `bash scripts/obs_on.sh` (starts netdata only). The Prom stack stays off.
- **NEW step 13**: install netdata Apache vhost.
  ```bash
  cp /root/mindx_observability/apache/netdata.pythai.net*.conf /etc/apache2/sites-available/
  htpasswd -cB /etc/apache2/htpasswd/netdata.htpasswd ops    # set 24+ char pw
  a2ensite netdata.pythai.net
  apachectl configtest && systemctl reload apache2
  certbot --apache -d netdata.pythai.net --redirect
  # Verify post-certbot vhost retained ProxyPass + WebSocket rewrite blocks
  ```
- **NEW step 14**: verify daily UI. Visit `https://netdata.pythai.net` → Basic Auth → real-time CPU/MEM/DISK/NET charts.

## When to summon Prom

Run `bash scripts/prom_on.sh` (4 containers come up: prometheus, alertmanager, node-exporter, blackbox-exporter):

- An incident — you want 3 days of historical PromQL queries.
- A synthetic alert test — `prom_on.sh`, simulate failure, verify email lands, `prom_off.sh`.
- Grafana dashboards — `bash scripts/grafana_on.sh` (auto-implies `prom_on`).
- Pushing eval scores (Phase 2 work) — Pushgateway lives next to Prom.

Run `bash scripts/prom_off.sh` when done — frees ~416 MB. netdata keeps running.

## Phase 1.2 verification

After deploy:
```bash
# Default state
sudo -u mindx XDG_RUNTIME_DIR=/run/user/1002 systemctl --user list-units --type=service --state=active \
  | grep -E "(netdata|prom|grafana|alert|node-exp|blackbox)"
# Expect: only netdata.service active

# netdata reachable
curl -fsSL -u ops:PASS https://netdata.pythai.net/api/v1/info | jq .version

# /insight/host/* endpoints reachable from public mindX backend
curl -s "https://mindx.pythai.net/insight/host/cpu?h=true"      # netdata-backed
curl -s "https://mindx.pythai.net/insight/host/memory?h=true"   # netdata-backed
curl -s "https://mindx.pythai.net/insight/host/disk?h=true"     # local psutil + walk
curl -s "https://mindx.pythai.net/insight/host/probes?h=true"   # "prom: off" if Prom stack down

# Prom on/off cycle
bash scripts/prom_on.sh
sleep 10
curl -fsSL -u ops:PASS https://prom.pythai.net/api/v1/targets | jq '.data.activeTargets | length'
bash scripts/prom_off.sh
```
