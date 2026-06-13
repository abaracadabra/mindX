# Adding a new blackbox HTTPS probe target

Three-line change. Example: probe `https://newsvc.pythai.net/health`.

## 1. Edit `prometheus/prometheus.yml`

In the `blackbox_http` scrape job, add the URL to the `targets:` list:

```yaml
  - job_name: blackbox_http
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://mindx.pythai.net/health
          - https://mindx.pythai.net/feedback.txt
          - https://agenticplace.pythai.net
          - https://bankon.pythai.net
          - https://rage.pythai.net
          - https://newsvc.pythai.net/health   # <-- new
```

## 2. Sync to VPS

```bash
rsync -av /home/hacker/mindX/mindx_observability/prometheus/prometheus.yml \
    root@168.231.126.58:/home/mindx/obs/prometheus/prometheus.yml
ssh root@168.231.126.58 'chown mindx:mindx /home/mindx/obs/prometheus/prometheus.yml'
```

## 3. Hot-reload Prometheus (no restart needed)

```bash
curl -X POST -u "ops:$PROM_PASS" https://prom.pythai.net/-/reload
```

## 4. Verify the new probe shows up

```bash
curl -s -u "ops:$PROM_PASS" 'https://prom.pythai.net/api/v1/query?query=probe_success' \
    | jq '.data.result[] | select(.metric.instance | contains("newsvc"))'
```

Should return `value: ["...", "1"]` within 15 s of the reload.

## 5. Commit back to the repo

```bash
cd /home/hacker/mindX
git add mindx_observability/prometheus/prometheus.yml
git commit -m "obs: probe newsvc.pythai.net"
```

## Notes

- `module: http_2xx` accepts any 2xx HTTP status. To match only 200, edit `blackbox/blackbox.yml` and add `valid_status_codes: [200]`.
- For `mTLS` or `Authorization:` headers, see https://github.com/prometheus/blackbox_exporter/blob/master/CONFIGURATION.md — add a new module rather than overloading `http_2xx`.
- The `ProbeDown` alert in `prometheus/rules/alert_rules.yml` automatically covers new targets — no rule edit needed.
