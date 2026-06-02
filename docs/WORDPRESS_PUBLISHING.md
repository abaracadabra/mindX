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

### Public allowlisted publisher (rage.pythai.net)

| Address | Role | Notes |
|---|---|---|
| `0x5277D156E7cD71ebF22c8f81812A65493D1ce534` | `wordpress.agent` / `author_agent` | Canonical EOA. Private key lives in BANKON vault under `wordpress.agent:pk` (context `wordpress.agent.keys`). Allowlisted on the rage.pythai.net mindX-Publish plugin (`wp_user_id=6`). The wallet that both *authors* and *publishes*; recovers from `meta._mindx_signer` on every post. |

Verify the live state any time with:

```bash
sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python \
    -m agents.wordpress_agent.scripts.cross_check_allowlist
# crosscheck: OK — vault wallet 0x5277…ce534 IS allowlisted (maps to wp_user_id=6)
```

External wallets that want to authorize a publish go through
`POST /publish/rage/challenge` → `/authorize` and must additionally appear in
the `WORDPRESS_PUBLISHER_ADDRESSES` allowlist (stored as a vault entry,
exported as an env var at process start). The canonical publisher above is the
only entry required for mindX's internal publishes; external wallets are
add-on.

### Two layers of identity on every post

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

## Identity model + the May 2026 silent-403 incident

**Canonical identity**: a single EOA on the plugin allowlist whose pk lives
in `wordpress.agent:pk` under context `wordpress.agent.keys`. Today's prod
runs as `author_agent` (`0x5277D156E7cD71ebF22c8f81812A65493D1ce534`) — the
same wallet that authors the article also publishes it. One identity, one
allowlist entry, one vault entry.

### What broke (forensic)

Through May 2026, autopublishing was silently broken in three concurrent layers:

1. **Transport never installed**: `/home/mindx/mindX/agents/wordpress_agent/`
   had only 2 of 10 package files; the systemd unit was never copied to
   `/etc/systemd/system/`; the loopback at `127.0.0.1:8765` never ran.
2. **PublicationOrchestrator silently crashed**: `main_service.py` spawn block
   referenced an undefined `author` variable; the `try/except` logged
   `WARNING` without `exc_info=True`, swallowing the traceback. Six restarts
   in the prior week all silently failed; ledger never created.
3. **Identity drift**: the WP plugin's allowlist had exactly 1 EOA but the
   matching pk was nowhere in the prod BANKON vault. Whoever published posts
   666 + 673 used an operator wallet held outside the vault (one-shot CLI
   publish). The wordpress.agent's own vault namespace was never provisioned.

All three are now fixed. The diagnostic at
`agents/wordpress_agent/scripts/cross_check_allowlist.py` prevents layer 3
from recurring — it runs as the systemd `ExecStartPre`, so a future
vault/allowlist drift surfaces as a service-failed-to-start (visible in
`systemctl status`) instead of as a silent 403 on the first publish.

### Recovery runbook (if publishing breaks again)

```bash
# 0. Is the loopback alive?
systemctl status wordpress-agent.service
curl -s http://127.0.0.1:8765/healthz
# (healthz being 401 is a known cosmetic bug — it skips _request_with_retry's
# auth header. The /publish path uses _request_with_retry correctly. Trust
# the cross-check, not healthz, for true auth verification.)

# 1. Run the cross-check (exits 0 if vault wallet is allowlisted)
cd /home/mindx/mindX
sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python -m agents.wordpress_agent.scripts.cross_check_allowlist
# Prints: vault wallet address, allowlist_entries count, verify status.
# Exit 1 → REMEDIATION line tells you to either add the address to the WP
# allowlist OR restore the matching pk into vault.

# 2. If allowlist mismatch — add the cross-check address to the plugin allowlist
#    via rage.pythai.net WP admin → Settings → mindX Publish Auth → Allowlist.
#    Then re-run step 1 until it exits 0.

# 3. If vault is missing wordpress.agent:pk — re-provision:
sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python scripts/vault/provision_wordpress_agent.py \
  --wp-base-url https://rage.pythai.net --wp-user codephreak \
  --wp-app-password JWT_AUTH_ONLY_DO_NOT_USE_BASIC --no-mint
# (--no-mint reuses the existing wordpress.agent wallet; drop the flag to mint a
#  new one, which then needs to be added to the WP allowlist.)

# 4. Restart and confirm
systemctl restart wordpress-agent.service
journalctl -u wordpress-agent.service -n 10 | grep crosscheck
# Expect: "crosscheck: OK — vault wallet 0x... IS allowlisted"

# 5. Publish (canonical example)
cd /home/mindx/mindX && sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python -c "
import asyncio, sys; sys.path.insert(0, '/home/mindx/mindX')
from pathlib import Path
from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md
async def m():
    md = Path('docs/publications/YOUR_ARTICLE.md').read_text()
    body = md.split(chr(10) + '---', 2)[2] if md.startswith('---') else md
    a = await AuthorAgent.get_instance()
    print(await a.publish_to_rage(
        title='Title here', content_html=_render_md(body),
        status='publish', slug='your-slug',
    ))
asyncio.run(m())
"
```

### How to verify it's working

- `journalctl -u wordpress-agent.service -n 5 | grep crosscheck` — last
  startup's pre-flight result (should end with `crosscheck: OK`).
- `curl -A "Mozilla/5.0 ..." https://rage.pythai.net/wp-json/mindx/v1/auth/diagnose`
  — confirms plugin v0.1.0 + `allowlist_entries >= 1` + `jwt_secret_present: true`.
- `GET /insight/publications/health` on mindx.pythai.net — orchestrator state
  + ledger + last publish post id/url + per-source status defaults.
- After a real publish, the post should be live at `https://rage.pythai.net/<slug>/`
  with `status: publish` in `/wp-json/wp/v2/posts/<id>`.

### Privacy invariants of the cross-check

The diagnostic prints only:
- the derived **address** of `wordpress.agent:pk` (public, never the pk)
- the plugin's `allowlist_entries` *count* (never the addresses)
- the `/verify` HTTP status code (200 / 403 / etc.) and the plugin's `code`
  field on failure (e.g. `mindx_auth_address_not_allowlisted`).

No private key value ever appears in stdout, stderr, journal, or systemd
status output.
