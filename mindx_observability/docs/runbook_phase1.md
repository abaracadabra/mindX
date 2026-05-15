# Phase 1 ops runbook

VPS: `168.231.126.58` (Hostinger) · user `mindx` (uid 1002) · mindX path `/home/mindx/mindX/`
Plan: `/home/hacker/.claude/plans/breezy-strolling-anchor.md`

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

- `du -sh /home/mindx/obs/prometheus_data` should stay <8 GB (Prometheus hard-cap)
- `free -h` available should stay ≥500 MB after swap is in play
- `swapon --show` should show <2 GB used (>2 GB = thrashing warning)
