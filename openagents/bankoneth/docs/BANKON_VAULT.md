# BANKON Vault + shadow-overlord (standalone)

`vault_module/` is a **full, self-contained import** of mindX's BANKON Vault and
shadow-overlord signature-auth system, so the bankon.eth dApp is also the UI to
bankon-vault without depending on the mindX backend. Imported from
`mindx_backend_service/bankon_vault/` with only relative-import rewrites and two
already-guarded coupling points (see below). 3/3 ported tests pass standalone
(`pytest vault_module/tests`).

## What it is

A "safe with a remote-controlled robot arm": private keys live encrypted in a
vault; an **offline** operator key (the shadow-overlord) authorizes each
privileged operation by signing a server-issued challenge; the server unlocks,
performs the op, and re-locks — the key never leaves.

### Crypto core — `vault.py` (`BankonVault`)
- AES-256-GCM per-entry encryption; keys derived via **HKDF-SHA512** with
  per-entry domain separation (`bankon-entry:{id}:{context}`).
- Master key from a passphrase (PBKDF2-HMAC-SHA512, 600k iters) or a 64-byte
  key file, or a **HumanOverseer** (EIP-191 signature → HKDF IKM).
- On-disk: `.salt`, `.master.key` (0400), `entries.json` (0600),
  `.human_overseer_active` sentinel, `.overseer_proof.json`, atomic rotation
  (`entries.json.candidate` + fsync + `os.replace`). Default dir:
  `openagents/bankoneth/vault_bankon/` (override `vault_dir=` / `BANKON_VAULT_DIR`).

### Overseers — `overseer.py`
`MachineOverseer` (key file), `HumanOverseer` (EIP-191 sig), `DAIOOverseer` (stub).

### Shadow-overlord auth — `shadow_overlord.py`
- `issue_challenge(scope, params)` → `{nonce, message, expires_at}` (120s, single-use).
- `consume_signed_challenge(nonce, sig, scope, params)` — verifies the signer is
  `SHADOW_OVERLORD_ADDRESS` over the server-canonical message.
- `issue_jwt(addr, scope)` / `verify_jwt(token, scope)` / `require_shadow_jwt(scope)`
  — 5-min, scope-bound HS256 JWTs. Scopes: `auth`, `cabinet.provision`,
  `cabinet.clear`, `vault.sign`, `release.key`.

### Routers (mount in any FastAPI app)
- `bankon_vault_router` → `/vault/credentials/{status,list,providers,store,delete,reunlock}`
- `shadow_admin_router` → `/admin/shadow/{challenge,verify}`, `/admin/cabinet/*`
- `public_cabinet_router` → `/cabinet/{company}`
- `vault_sign_router` → `/vault/sign/{agent_id}` (signing oracle; message sha256 re-bound server-side)
- `cabinet.py` — 8-role executive-suite provisioner (`company:{c}:cabinet:{role}:pk`).
- `credential_provider.py` — `PROVIDER_ENV_MAP` loader (decrypts secrets into `os.environ`).

## Env vars

| Var | Purpose | Default |
|---|---|---|
| `SHADOW_OVERLORD_ADDRESS` | the offline admin key (for bankon, the bankon.eth owner) | — (required) |
| `SHADOW_JWT_SECRET` | HS256 secret, ≥32 chars | — (required) |
| `BANKON_VAULT_DIR` / `vault_dir=` | vault storage dir | `bankoneth/vault_bankon/` |
| `SHADOW_NONCES_PATH` | nonce store | `data/governance/shadow_nonces.json` |
| `MINDX_PRODUCTION_REGISTRY`, `MINDX_AGENT_MAP` | cabinet registries | `data/identity/…`, `daio/…` |

## Coupling points cut (standalone-safe)

1. `routes.py` — `from mindx_backend_service.security_middleware import require_admin_access`
   is `try/except ImportError → None`, and `_admin_dep()` returns a **503 pass-through**
   when absent (never silently allows). The Phase-2 gate injects its own admin dep.
2. `shadow_overlord.py` — `emit_catalogue_event` audit is best-effort inside try/except;
   absence does not block ops.

## Use

```bash
pip install -r vault_module/requirements-vault.txt
# mounted by the gate backend (Phase 2); or directly:
python -c "from vault_module import BankonVault, bankon_vault_router"
```

The tiered-login gate (`backend/`, see `docs/TIERED_LOGIN.md`) mounts these routers
and exposes the credential/cabinet/sign surface to the **admin** tier only.
