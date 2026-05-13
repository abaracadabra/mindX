# WordPress Publishing — AuthorAgent → wordpress-agent → rage.pythai.net

mindX publishes long-form articles to **rage.pythai.net** (a Hostinger
PHP/Apache + WordPress site) through a small, single-responsibility loopback
service. **AuthorAgent** writes and renders the article; the **wordpress-agent**
service puts it on the site over the WordPress REST API. Nothing else in mindX
talks to WordPress.

**Credentials are vault-backed, decrypt-on-demand.** The WP Application Password
and the wordpress.agent wallet private key live in an isolated BANKON-vault
namespace (`context="wordpress.agent.keys"`) and are decrypted only for the
duration of an authorized `/publish` call. **No `WP_APP_PASSWORD` environment
variable exists in production.**

## Topology

```
  external wallet                 mindX backend                  wordpress-agent          WordPress
  (operator/agent)               (FastAPI :8000)                 (loopback :8765)         (rage.pythai.net)
        │  /publish/rage/challenge   │                                   │                       │
        │ ──────────────────────────▶│                                   │                       │
        │   {nonce, message, exp}    │                                   │                       │
        │ ◀──────────────────────────│                                   │                       │
        │  /publish/rage/authorize   │   AuthorAgent.publish_to_rage     │                       │
        │  {wallet, nonce, sig,      │  ────────────────────────────────▶│   open vault          │
        │   title, doc_path|html}    │                                   │   retrieve            │
        │ ──────────────────────────▶│                                   │     wordpress.agent:  │
        │                            │                                   │     {pk, wp_*}        │
        │                            │                                   │   sign sha256(html)   │
        │                            │                                   │   POST wp-json/wp/v2  │
        │                            │                                   │  ────────────────────▶│
        │                            │                                   │   lock vault          │
        │   {wordpress:{post_id,…}}  │ ◀────────────────────────────────│                       │
        │ ◀──────────────────────────│                                   │                       │
```

## Identity & authorization

Every published post carries two layers of identity:

- `meta._mindx_authorized_by` — the **external wallet** that requested the publish.
  Verified by EIP-191 signature recovery on `/publish/rage/authorize`. Must be in
  the `WORDPRESS_PUBLISHER_ADDRESSES` allowlist (a vault-backed env var).
- `meta._mindx_signer` + `meta._mindx_signature` — **wordpress.agent's own
  identity**: in the same vault-unlock window where it reads the WP API key, the
  wordpress-agent retrieves its `wordpress.agent:pk` and signs `sha256(html)`.
  Recovers to `wordpress.agent:address` (the public identity stamped into
  `data/identity/production_registry.json`). The WP API key is *only ever reached
  by wordpress.agent's verified identity*; the published article carries a
  public-checkable chain "external X requested → wordpress.agent Y published →
  content hash Z."
- `meta._mindx_content_hash` — sha256 of the HTML body.

## The vault namespace — `wordpress.agent.keys`

All wordpress.agent secrets share **one HKDF-isolated** context, separate from
every other credential in the vault and **not in `PROVIDER_ENV_MAP`** (so they
are never decrypted into any process env at startup):

| Entry id | Context | Contents |
|---|---|---|
| `wordpress.agent:pk` | `wordpress.agent.keys` | wallet **private key** (hex) |
| `wordpress.agent:address` | `wordpress.agent.keys` | derived checksum address (public identity) |
| `wordpress.agent:wp_app_password` | `wordpress.agent.keys` | WordPress Application Password (the WP API key) |
| `wordpress.agent:wp_base_url` | `wordpress.agent.keys` | `https://rage.pythai.net` (HTTPS-enforced by `config.py`) |
| `wordpress.agent:wp_user` | `wordpress.agent.keys` | WordPress username |

The only wordpress-related entry that's env-mapped:

| Entry id | Env var | Contents |
|---|---|---|
| `wordpress_publisher_addresses` | `WORDPRESS_PUBLISHER_ADDRESSES` | comma-separated 0x EOAs permitted to request a publish |

## One-time provisioning

Run on the VPS as the `mindx` user (vault writer):

```bash
sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python \
    /home/mindx/mindX/scripts/vault/provision_wordpress_agent.py \
    --wp-base-url https://rage.pythai.net \
    --wp-user codephreak \
    --publisher-addresses 0xAaa...,0xBbb...
# (prompts for the WordPress Application Password via getpass — never on argv)
```

This mints the `wordpress.agent` wallet (`Account.create()`), stores
`wordpress.agent:pk` + `:address` under `context="wordpress.agent.keys"`, writes
the address into `data/identity/production_registry.json` under
`agents["wordpress.agent"]`, stores the WP creds in the same namespace, and
seeds the allowlist. Idempotent; safe to re-run (existing wallet is preserved).

## Deploy the loopback service

```bash
sudo bash /home/mindx/mindX/agents/wordpress_agent/scripts/install.sh
sudo systemctl restart wordpress-agent.service
curl -s http://127.0.0.1:8765/healthz | jq
```

The unit runs as `User=mindx` (so it shares mindX's vault), with hardening:
`NoNewPrivileges`, `ProtectSystem=strict`, `MemoryDenyWriteExecute`,
`MemoryMax=256M`, `ReadWritePaths` scoped to the vault dir + `data/`. Blast
radius: this service can read the vault — that's the accepted tradeoff for
decrypt-on-demand. The optional `/etc/wordpress-agent/wordpress-agent.env` holds
only non-secret operational overrides (binding host/port, timeouts).

## Publishing — three paths

**1. Public, wallet-authorized (recommended):**

```bash
# 1. compute the content hash you'll sign (server recomputes from rendered HTML)
HTML=$(curl -s …or render the doc however you like…)
CONTENT_SHA256=0x$(printf %s "$HTML" | sha256sum | awk '{print $1}')

# 2. request a challenge
curl -s -X POST https://mindx.pythai.net/publish/rage/challenge \
  -H 'Content-Type: application/json' \
  -d "{\"wallet_address\":\"0xAaa...\",\"title\":\"My post\",\"content_sha256\":\"$CONTENT_SHA256\"}"
# → {"nonce":"0x…","message":"MINDX-SHADOW-OVERLORD scope=wordpress.publish\nnonce: 0x…\ncontent_sha256: 0x…\ntitle: My post\nwallet: 0xaaa…","expires_at":…}

# 3. sign `message` with that wallet (EIP-191), then authorize:
curl -s -X POST https://mindx.pythai.net/publish/rage/authorize \
  -H 'Content-Type: application/json' \
  -d '{"wallet_address":"0xAaa...","nonce":"0x...","signature":"0x...130-hex...","title":"My post","status":"draft","doc_path":"publications/machine_dreaming_explained.md"}'
# → {"status":"ok","authorized_by":"0xaaa…","wordpress":{"post_id":…,"url":"…","status":"draft",…}}
```

Body of `/publish/rage/authorize` accepts exactly one of `doc_path` (markdown
file under `docs/`), `markdown` (inline), or `html` (pre-rendered). The server
renders markdown→HTML via `_render_md`, computes the content hash, and verifies
it matches what the wallet signed (the nonce is bound to that hash).

**2. Operator path (admin-gated):** `POST /admin/publish-to-rage` — unchanged
from before; for one-off publishes by the mindX admin.

**3. CLI (direct to the loopback service, bypassing wallet auth):**

```bash
python -m agents.wordpress_agent.cli publish \
    --title "My post" --status draft --content-file post.html
```

The CLI is for local dev / emergencies. The service still reads its creds from
the vault.

## Diagnostics

`GET /diagnostics/live` exposes (under `author.*`):

| Field | Meaning |
|---|---|
| `rage_publishes` | total successful publishes since service start |
| `last_rage_url` | URL of the most recent publish |
| `last_rage_authorized_by` | wallet that authorized the most recent publish |

The vault never appears in diagnostics output. Catalogue audit events are written
to `data/logs/catalogue_events.jsonl` (kind: `wordpress.publish.authorize`).

## Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `publish_to_rage` returns `None`, logs "is the wordpress-agent service running?" | service down or wrong port | `systemctl status wordpress-agent`; check `MINDX_WORDPRESS_AGENT_URL` |
| `/healthz` returns 503 "no credentials available" | vault not provisioned, or locked under HumanOverseer without a proof | run `provision_wordpress_agent.py`; check `.overseer_proof.json` |
| `/publish/rage/authorize` → 403 "not in allowlist" | wallet not in `WORDPRESS_PUBLISHER_ADDRESSES` | add it via `manage_credentials.py store wordpress_publisher_addresses "0xA,0xB"` and restart |
| `/publish/rage/authorize` → 400 "content hash differs from what was signed" | client signed a different rendering of the markdown | re-fetch the rendered HTML, recompute the hash, re-sign |
| `/publish/rage/authorize` → 401 invalid signature | sig was made over a different message, or by a different key | re-issue challenge and sign exactly the returned `message` text |
| `/publish` → 401 from WordPress | bad/expired Application Password | run `provision_wordpress_agent.py` with the fresh app password |
| `/publish` → 502 from WordPress | Hostinger throttling/maintenance | wait; the wordpress-agent retries 5xx with backoff |

## Why decrypt-on-demand

- The WordPress Application Password is plaintext only inside the wordpress-agent
  process, only for the request that uses it.
- A process memory dump catches credentials only if the dump happens during an
  active publish window.
- An `os.environ` scan from anywhere else on the box returns no WP secret.
- Rotating the WP password = store the new value + restart isn't required (the
  next request will fetch the new one).
- Promoting the vault from MachineOverseer to HumanOverseer rotates every
  `wordpress.agent.keys` entry with the rest of the vault, atomically.
