# Integrating WordPress.agent with mindX

This document is written for **Claude (or any agent) deploying WordPress.agent
into the mindX runtime on the VPS**. It describes the canonical wiring between
mindX, AuthorAgent, and this tool.

## Topology

```
                           ┌─────────────────────────────────┐
                           │  VPS (mindx.pythai.net)         │
                           │                                 │
   ┌───────────┐  invoke   │  ┌────────────┐    HTTP/IPC     │
   │  mindX    │──────────▶│  │AuthorAgent │────────────┐    │
   │  cortex   │           │  └────────────┘            │    │
   └───────────┘           │                            ▼    │
                           │                  ┌─────────────┐│
                           │                  │ WordPress.  ││
                           │                  │   agent     ││
                           │                  │ :8765 (loop)││
                           │                  └──────┬──────┘│
                           └─────────────────────────┼───────┘
                                                     │ HTTPS
                                                     │ wp-json/wp/v2
                                                     ▼
                                       ┌──────────────────────────┐
                                       │  Hostinger PHP/Apache    │
                                       │    rage.pythai.net       │
                                       │      WordPress           │
                                       └──────────────────────────┘
```

WordPress.agent runs only on the loopback interface of the VPS. AuthorAgent
calls it on `127.0.0.1:8765`. Outbound HTTPS to `rage.pythai.net` is the only
external network path the agent uses.

## Deployment Path (for Claude)

When asked to deploy WordPress.agent on the VPS, follow these steps. Each is
idempotent and safe to re-run.

1. **Verify Python 3.12+ is present.**
   ```bash
   python3.12 --version || sudo apt-get install -y python3.12 python3.12-venv
   ```

2. **Confirm the Hostinger preconditions** (one-time, manual on the WordPress
   side, not on the VPS):
   - Generate an Application Password for the `codephreak` WordPress user
     under `Users → Profile → Application Passwords`. Label it
     `wordpress-agent-vps`.
   - Confirm permalinks are set to `Post name` under `Settings → Permalinks`.
   - If LiteSpeed Cache or another caching plugin is active, exclude
     `/wp-json/*` from caching.
   - If a security plugin is restricting REST API access, allowlist the VPS
     egress IP.

3. **Install on the VPS.**
   ```bash
   git clone https://github.com/codephreak/wordpress-agent /opt/wordpress-agent.src
   cd /opt/wordpress-agent.src
   sudo bash scripts/install.sh
   ```

4. **Populate the env file.**
   ```bash
   sudo ${EDITOR:-nano} /etc/wordpress-agent/wordpress-agent.env
   ```
   At minimum set `WP_BASE_URL`, `WP_USER`, and `WP_APP_PASSWORD`.

5. **Start the service and verify health.**
   ```bash
   sudo systemctl restart wordpress-agent.service
   sudo systemctl status wordpress-agent.service
   curl -s http://127.0.0.1:8765/healthz | jq
   ```
   A healthy response returns `"ok": true` and the WordPress user id.

6. **Register with AgenticPlace.**
   Copy `agent.manifest.json` into the AgenticPlace agent registry directory
   on the VPS. The manifest declares `wordpress.publish` as a callable
   capability with HTTP transport on `127.0.0.1:8765`.

## Calling from AuthorAgent

AuthorAgent should treat WordPress.agent as one publishing destination among
many. The minimal call from Python:

```python
import httpx

async def publish_to_rage(article: dict) -> dict:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8765") as c:
        response = await c.post("/publish", json={
            "title": article["title"],
            "content": article["html"],
            "status": "publish",
            "categories": article.get("category_ids", []),
            "tags": article.get("tag_ids", []),
            "featured_media": article.get("featured_media_id"),
            "excerpt": article.get("excerpt"),
            "meta": {
                "_mindx_content_hash": article["mindx_hash"],
                "_x402_receipts": article.get("x402_receipts", []),
            },
        })
        response.raise_for_status()
        return response.json()
```

The featured-image flow is two calls: first `/media` to upload, then `/publish`
with the returned `media_id` as `featured_media`.

## Scheduled and Event-Driven Publishing

This tool deliberately does **not** ship an in-process scheduler. WordPress's
own cron handles `status="future"` posts.

- **Scheduled:** AuthorAgent calls `/publish` with `status="future"` and a
  future ISO 8601 `date`. WordPress publishes at that time. If AuthorAgent
  goes down, the scheduled post still publishes.
- **Event-driven:** AuthorAgent's event listeners (NATS, on-chain logs,
  webhooks) decide when to call `/publish`. WordPress.agent never listens for
  events directly.
- **Milestone publishing:** AuthorAgent watches the relevant milestone source
  and triggers `/publish` when conditions are met.

This separation keeps WordPress.agent stateless and easy to reason about.

## Failure Modes and Recovery

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `/healthz` returns `"ok": false`, status 401 | Bad app password | Regenerate in WordPress admin, update env, restart service |
| `/healthz` returns 5xx | Hostinger throttling or maintenance | Wait, retry; the tool retries with exponential backoff automatically |
| `/publish` returns 502 | Repeated upstream failures | Inspect `journalctl -u wordpress-agent` for response body |
| Post created but no featured image | Media upload not done first | AuthorAgent must call `/media` before `/publish` |
| Scheduled post never publishes | WordPress cron not firing | Confirm `wp-cron.php` is being hit (Hostinger sometimes disables wp-cron and requires a system cron entry) |

## Updating

```bash
cd /opt/wordpress-agent.src
git pull
sudo bash scripts/install.sh
sudo systemctl restart wordpress-agent.service
```

## Removal

```bash
sudo bash /opt/wordpress-agent.src/scripts/uninstall.sh         # leave env
sudo bash /opt/wordpress-agent.src/scripts/uninstall.sh --purge # remove all
```
