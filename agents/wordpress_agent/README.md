# WordPress.agent

> Agnostic publishing tool that takes finished content and posts it to
> WordPress. Single responsibility. Does one thing and does it well.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](#)

WordPress.agent is a small, focused publishing tool for the
[PYTHAI/DELTAVERSE](https://pythai.net) ecosystem. It enhances `AuthorAgent`
with the ability to publish to any self-hosted WordPress site over the
standard REST API. It does not generate content, manage editorial style,
schedule via in-process timers, or anchor anything on-chain — those concerns
belong upstream in `AuthorAgent` or in dedicated tools elsewhere in the stack.

The canonical deployment publishes from `mindx.pythai.net` (a VPS) to
`rage.pythai.net` (Hostinger PHP/Apache + WordPress).

---

## Table of Contents

1. [Why this exists](#why-this-exists)
2. [Architecture](#architecture)
3. [Quick start](#quick-start)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Deployment](#deployment)
7. [API](#api)
8. [Testing](#testing)
9. [Integration with mindX / AuthorAgent](#integration-with-mindx--authoragent)
10. [Hostinger-specific setup](#hostinger-specific-setup)
11. [Project layout](#project-layout)
12. [License](#license)

---

## Why this exists

`AuthorAgent` already handles content generation, editorial voice, citation
checking, image commissioning, payment settlement, and provenance hashing.
What it lacks is a clean, well-tested adapter to the WordPress REST API on
the destination site. WordPress.agent is that adapter, and nothing more.

This project deliberately rejects the temptation to do too much. Earlier
designs accreted in-process schedulers, style engines, on-chain anchoring,
chain mappers, x402 settlers, and editorial DAIO contracts. All of those
exist or will exist as separate components. WordPress.agent stays focused
on a single boundary: turning a fully formed article into a WordPress post.

The result is roughly 200 lines of core Python wrapping `httpx`, plus a
thin FastAPI surface for local IPC, plus the deployment scaffolding to run
it as a hardened systemd service or Podman container on a VPS.

## Architecture

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

WordPress.agent binds to loopback only. AuthorAgent reaches it on
`127.0.0.1:8765`. Outbound HTTPS to the WordPress host is the only external
network path.

## Quick start

```bash
# Clone
git clone https://github.com/codephreak/wordpress-agent.git
cd wordpress-agent

# Install (development)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# edit .env with your WordPress site, user, and Application Password

# Verify connectivity
wordpress-agent health

# Publish a test post
echo '<p>Hello from WordPress.agent.</p>' > test.html
wordpress-agent publish --title "Hello" --content-file test.html --status draft
```

A successful health check returns:

```json
{
  "ok": true,
  "status_code": 200,
  "base_url": "https://rage.pythai.net",
  "user": "codephreak",
  "wp_user_id": 1
}
```

## Configuration

All configuration is environment-driven via `pydantic-settings`. The full
list of variables, with defaults:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WP_BASE_URL` | yes | — | WordPress site base URL (e.g. `https://rage.pythai.net`) |
| `WP_USER` | yes | — | WordPress username |
| `WP_APP_PASSWORD` | yes | — | Application Password (24 chars, spaced or hyphenated) |
| `WP_TIMEOUT` | no | `30` | HTTP request timeout in seconds |
| `WP_RETRY_COUNT` | no | `3` | Retry attempts on transient failures |
| `WP_RETRY_BACKOFF` | no | `0.5` | Exponential backoff base in seconds |
| `WP_USER_AGENT` | no | `mindX-WordpressAgent/0.1 ...` | Sent with every request |
| `WP_SERVER_HOST` | no | `127.0.0.1` | IPC server bind host |
| `WP_SERVER_PORT` | no | `8765` | IPC server bind port |

Generate an Application Password under
`Users → Profile → Application Passwords` in WordPress admin. **Never** use
the user's login password — the REST API will accept it but it is a
security anti-pattern that bypasses every revocation mechanism.

## Usage

### CLI

```bash
# Verify connectivity
wordpress-agent health

# Publish immediately
wordpress-agent publish \
    --title "Aglm Flagship Checkpoint Released" \
    --content-file post.html \
    --status publish \
    --category 5 --tag 12 --tag 18

# Schedule for later
wordpress-agent publish \
    --title "Scheduled Article" \
    --content-file post.html \
    --status future \
    --date 2026-06-01T09:00:00+00:00

# Upload a featured image first, then publish referencing it
wordpress-agent media upload --file hero.png --alt "Featured image"
# returns {"media_id": 123, "url": "...", ...}

wordpress-agent publish \
    --title "With Featured Image" \
    --content-file post.html \
    --featured-media 123
```

### Python library

```python
import asyncio
from wordpress_agent import WordpressAgent, Settings

async def main() -> None:
    async with WordpressAgent(Settings()) as agent:
        media = await agent.upload_media("hero.png", alt_text="Featured")
        result = await agent.publish(
            title="Aglm Flagship Checkpoint Released",
            content="<p>Body of the article…</p>",
            featured_media=media.media_id,
            categories=[5],
            tags=[12, 18],
        )
        print(result.url)

asyncio.run(main())
```

### HTTP server (local IPC for AuthorAgent)

```bash
wordpress-agent-server   # binds 127.0.0.1:8765 by default
```

```bash
curl -X POST http://127.0.0.1:8765/publish \
    -H 'Content-Type: application/json' \
    -d '{"title": "Hello", "content": "<p>World</p>", "status": "draft"}'
```

## Deployment

### Direct (systemd + venv)

```bash
sudo bash scripts/install.sh
sudo ${EDITOR:-nano} /etc/wordpress-agent/wordpress-agent.env
sudo systemctl restart wordpress-agent.service
sudo systemctl status wordpress-agent.service
curl -s http://127.0.0.1:8765/healthz | jq
```

The install script creates a dedicated `wpagent` system user, installs the
package into `/opt/wordpress-agent/.venv`, stages the env file at
`/etc/wordpress-agent/wordpress-agent.env`, and enables the systemd unit.

The unit is hardened: `ProtectSystem=strict`, `NoNewPrivileges=true`,
`PrivateTmp=true`, `MemoryDenyWriteExecute=true`, `MemoryMax=256M`,
`CPUQuota=50%`. Adjust resource limits in
`deploy/systemd/wordpress-agent.service` if needed.

### Container (Podman)

```bash
podman build -f deploy/Containerfile -t localhost/wordpress-agent:0.1.0 .
podman-compose -f deploy/compose.yml up -d
podman logs -f wordpress-agent
```

The container runs as a non-root user, with a read-only root filesystem and
all capabilities dropped. Only the loopback port is exposed.

For a Podman-managed systemd unit, see
`deploy/systemd/wordpress-agent-podman.service`.

### Uninstall

```bash
sudo bash scripts/uninstall.sh           # leaves env file and user
sudo bash scripts/uninstall.sh --purge   # removes everything
```

## API

### `GET /healthz`

Verifies WordPress reachability and authentication.

```json
{
  "ok": true,
  "status_code": 200,
  "base_url": "https://rage.pythai.net",
  "user": "codephreak",
  "wp_user_id": 1
}
```

### `POST /publish`

Publishes a finished article. Pass `status: "future"` with a future `date`
for scheduled publishing — WordPress's own cron handles the timer.

Request:

```json
{
  "title": "string (required)",
  "content": "string (required, HTML or block markup)",
  "status": "publish | future | draft | pending | private",
  "date": "2026-06-01T09:00:00+00:00",
  "categories": [5, 12],
  "tags": [3, 7],
  "featured_media": 123,
  "excerpt": "optional excerpt",
  "slug": "optional-url-slug",
  "author": 1,
  "meta": { "_mindx_content_hash": "0xabc..." }
}
```

Response:

```json
{
  "post_id": 42,
  "url": "https://rage.pythai.net/?p=42",
  "status": "publish",
  "slug": "hello-world",
  "date_gmt": "2026-05-09T22:00:00"
}
```

### `POST /media`

Uploads a media file. Multipart form-data.

| Field | Type | Required |
|-------|------|----------|
| `file` | file | yes |
| `alt_text` | string | no |
| `caption` | string | no |
| `title` | string | no |

Response:

```json
{
  "media_id": 123,
  "url": "https://rage.pythai.net/wp-content/uploads/2026/05/hero.png",
  "mime_type": "image/png"
}
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite uses `pytest-httpx` to mock the WordPress REST API and verifies:

- Successful publish path returns a `PublishResult` with the expected fields.
- Authentication failures raise `AuthenticationError`.
- Transient 5xx responses retry with exponential backoff.
- Persistent failures raise `PublishError` after `WP_RETRY_COUNT` attempts.
- Empty title or content is rejected client-side.
- Scheduled publishes require a timezone-aware `date`.
- The `meta` field is forwarded verbatim to WordPress.
- The FastAPI server validates request schemas and surfaces upstream errors
  as appropriate HTTP status codes.

```bash
pytest --cov=wordpress_agent --cov-report=term-missing
```

## Integration with mindX / AuthorAgent

The detailed wiring is in [`docs/MINDX_INTEGRATION.md`](docs/MINDX_INTEGRATION.md).
A short version:

WordPress.agent is registered with AgenticPlace via `agent.manifest.json`,
which declares its `wordpress.publish` capability over loopback HTTP.
AuthorAgent calls `/publish` as the final step of its content pipeline.
For featured images, AuthorAgent calls `/media` first, then includes the
returned `media_id` in the `featured_media` field of the `/publish` call.

Provenance metadata (mindX content hash, x402 receipts from
`parsec-wallet`, on-chain anchor transaction hashes) is passed through the
`meta` field. WordPress stores these as post meta and renders them in the
post footer if the active theme supports the `_mindx_*` meta keys.
See [`docs/HOSTINGER_SETUP.md`](docs/HOSTINGER_SETUP.md) §6 for the
`register_post_meta` snippet that whitelists these fields.

Scheduled and event-driven publishing are handled by AuthorAgent and
WordPress's own cron, not by this tool. WordPress.agent is intentionally
stateless.

## Hostinger-specific setup

The `rage.pythai.net` site runs on Hostinger's managed PHP/Apache stack.
The one-time setup checklist is in
[`docs/HOSTINGER_SETUP.md`](docs/HOSTINGER_SETUP.md). Highlights:

- Generate an Application Password under `Users → Profile`.
- Set permalinks to `Post name`.
- Verify the REST API at `https://rage.pythai.net/wp-json/wp/v2/`.
- Allowlist the VPS egress IP if any security plugin is filtering REST.
- Exclude `/wp-json/*` from full-page caching.
- Add a Hostinger cron job hitting `wp-cron.php` every 5 minutes if
  scheduled publishing is used.

## Project layout

```
wordpress-agent/
├── wordpress_agent/
│   ├── __init__.py            # public API (WordpressAgent, Settings)
│   ├── agent.py               # core async client wrapping httpx
│   ├── server.py              # FastAPI loopback server
│   ├── cli.py                 # Click CLI
│   └── config.py              # pydantic-settings
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_config.py
│   └── test_server.py
├── deploy/
│   ├── Containerfile          # Podman/Docker image
│   ├── compose.yml            # Podman-compose definition
│   └── systemd/
│       ├── wordpress-agent.service           # venv-based unit
│       └── wordpress-agent-podman.service    # container-based unit
├── scripts/
│   ├── install.sh             # idempotent VPS installer
│   ├── uninstall.sh           # uninstaller
│   └── smoke.sh               # health probe
├── docs/
│   ├── MINDX_INTEGRATION.md   # for Claude / mindX deployers
│   └── HOSTINGER_SETUP.md     # WordPress-side prerequisites
├── agent.manifest.json        # AgenticPlace registry entry
├── pyproject.toml
├── .env.example
├── LICENSE                    # Apache-2.0
├── CHANGELOG.md
└── README.md
```

## License

Apache License 2.0. © 2026 BANKON — all rights reserved.
See [LICENSE](LICENSE).
