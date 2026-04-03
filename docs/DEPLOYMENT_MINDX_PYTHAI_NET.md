# mindX Production Deployment — mindx.pythai.net

**Live at:** https://mindx.pythai.net  
**API Docs:** https://mindx.pythai.net/docs  
**VPS:** Hostinger KVM, `168.231.126.58`  

## Architecture

```
  Client (wallet/Bearer token)
      │
      ▼  HTTPS :443
  Apache2 (SSL termination, Let's Encrypt)
      │
      ▼  http://127.0.0.1:8000
  uvicorn → FastAPI (mindx_backend_service)
      │
      ├── BANKON Vault (AES-256-GCM credentials)
      ├── LLM Providers (Gemini, Groq, OpenAI, Anthropic, ...)
      ├── Agent Orchestration (BDI, Mastermind, Coordinator)
      └── mindterm (WebSocket terminal)
```

| Layer | Detail |
|-------|--------|
| **Domain** | `mindx.pythai.net` → `168.231.126.58` (A record) |
| **SSL** | Let's Encrypt, auto-renew via certbot |
| **Proxy** | Apache2 reverse proxy, WebSocket for `/mindterm` |
| **Service** | systemd `mindx.service`, User=mindx |
| **Code** | `/home/mindx/mindX/` |
| **Venv** | `/home/mindx/mindX/.mindx_env/` |
| **Credentials** | BANKON Vault at `mindx_backend_service/vault_bankon/` |
| **Logs** | `data/logs/mindx_runtime.log` + journalctl -u mindx |

## Authentication

### Wallet-Based (Primary)
```bash
# 1. Get challenge
curl -X POST https://mindx.pythai.net/users/challenge \
  -H "Content-Type: application/json" \
  -d '{"wallet_address":"0x...", "action":"login"}'

# 2. Sign challenge with wallet, then register
curl -X POST https://mindx.pythai.net/users/register-with-signature \
  -H "Content-Type: application/json" \
  -d '{"wallet_address":"0x...", "message":"...", "signature":"0x..."}'

# 3. Use session token
curl https://mindx.pythai.net/agents/list \
  -H "X-Session-Token: <uuid>"
```

### Bearer API Key (Service-to-Service)
```bash
curl https://mindx.pythai.net/health \
  -H "Authorization: Bearer <API_KEY>"
```

API keys are stored encrypted in BANKON Vault as `mindx_api_keys`.

## Credential Management (BANKON Vault)

All API keys are encrypted with AES-256-GCM + HKDF-SHA512. No plaintext secrets on disk.

### CLI Tool

SSH to VPS, then:

```bash
cd /home/mindx/mindX

# List supported providers
sudo -u mindx .mindx_env/bin/python manage_credentials.py providers

# Store a key
sudo -u mindx .mindx_env/bin/python manage_credentials.py store gemini_api_key "AIza..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store groq_api_key "gsk_..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store openai_api_key "sk-..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store anthropic_api_key "sk-ant-..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store mistral_api_key "..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store together_api_key "..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store deepseek_api_key "..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store cohere_api_key "..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store perplexity_api_key "..."
sudo -u mindx .mindx_env/bin/python manage_credentials.py store fireworks_api_key "..."

# List stored credentials (IDs only, no secrets)
sudo -u mindx .mindx_env/bin/python manage_credentials.py list

# Delete a credential
sudo -u mindx .mindx_env/bin/python manage_credentials.py delete old_key

# Restart service to pick up changes
sudo systemctl restart mindx
```

### API Endpoints

```bash
# Vault status
curl https://mindx.pythai.net/vault/credentials/status

# List stored credential IDs
curl https://mindx.pythai.net/vault/credentials/list

# List supported providers
curl https://mindx.pythai.net/vault/credentials/providers
```

### Provider Config Templates

Per-provider templates at `config/providers/*.env`:

```
config/providers/
├── anthropic.env
├── cohere.env
├── deepseek.env
├── fireworks.env
├── gemini.env
├── groq.env
├── mistral.env
├── ollama.env
├── openai.env
├── perplexity.env
├── replicate.env
├── stability.env
└── together.env
```

Each file documents the provider URL and vault storage command. Non-secret model overrides can be added directly to these files.

## Service Management

```bash
# Status
sudo systemctl status mindx

# Logs (live)
sudo journalctl -u mindx -f

# Restart
sudo systemctl restart mindx

# Stop
sudo systemctl stop mindx

# Start
sudo systemctl start mindx
```

## DNS Configuration (Hostinger)

### Current Record
| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | mindx | 168.231.126.58 | 3600 |

### How to Update DNS on Hostinger

1. Log in to [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. Select the domain **pythai.net**
3. Go to **DNS / Nameservers** → **DNS Records**
4. Find or create the **A record**:
   - **Type:** A
   - **Name:** `mindx` (this creates `mindx.pythai.net`)
   - **Points to:** `168.231.126.58`
   - **TTL:** 3600 (or 14400)
5. Click **Save** / **Update**
6. DNS propagation takes 5–30 minutes (up to 48h for new records)

### Verify DNS
```bash
dig mindx.pythai.net +short
# Should return: 168.231.126.58
```

## SSL Certificate

Managed by certbot (Let's Encrypt). Auto-renews via systemd timer.

```bash
# Check certificate
sudo certbot certificates

# Force renewal (if needed)
sudo certbot renew --cert-name mindx.pythai.net

# Verify renewal timer
sudo systemctl list-timers | grep certbot
```

Current cert expires **2026-06-19** (auto-renews 30 days before).

## Updating the Deployment

```bash
# On local machine: package update
cd ~/mindX
tar czf /tmp/mindx-update.tar.gz \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.mindx_env' --exclude='node_modules' --exclude='.env' \
  --exclude='data/logs/*' --exclude='data/memory/stm/*' \
  .

# Transfer
scp /tmp/mindx-update.tar.gz root@168.231.126.58:/tmp/

# On VPS: apply update (preserves vault and .env)
ssh root@168.231.126.58
cd /home/mindx/mindX
# Backup vault
cp -r mindx_backend_service/vault_bankon /tmp/vault_bankon_backup
# Extract (overwrites code, not vault or .env)
tar xzf /tmp/mindx-update.tar.gz
# Restore vault
cp -r /tmp/vault_bankon_backup mindx_backend_service/vault_bankon
chown -R mindx:mindx .
systemctl restart mindx
```

## Security Notes

- API listens on `127.0.0.1:8000` only (not exposed directly)
- Apache handles SSL termination and sets security headers (HSTS, X-Frame-Options, CSP)
- systemd runs as `mindx` user with `NoNewPrivileges=true`, `ProtectSystem=strict`
- BANKON Vault master key at `vault_bankon/.master.key` is `0400` (owner-read only)
- Vault entries are AES-256-GCM encrypted with per-entry HKDF key derivation
- HTTP → HTTPS 301 redirect enforced
