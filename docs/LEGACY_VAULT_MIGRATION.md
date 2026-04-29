# Legacy vault migration plan — vault_manager + encrypted_vault_manager → BANKON

## Context

mindX has three coexisting credential-storage systems today:

| Module | LOC | Crypto | On-disk root | Importers |
|--------|-----|--------|--------------|-----------|
| **`mindx_backend_service/vault_manager.py`** | 894 | none (plaintext + filesystem perms) | `mindx_backend_service/vault/` | 21+ across `main_service.py`, `main_service_production.py`, `id_manager_agent.py`, `startup_agent.py`, `security_middleware.py` |
| **`mindx_backend_service/encrypted_vault_manager.py`** | 481 | Fernet (AES-128) over PBKDF2-HMAC-SHA256 | `mindx_backend_service/vault_encrypted/` | 4 (`aion_agent`, `backup_agent`, `deploy/aion_production_service`, `scripts/migrate_to_encrypted_vault`) |
| **`mindx_backend_service/bankon_vault/`** | ~400 | AES-256-GCM + HKDF-SHA512, overseer-aware unlock | `mindx_backend_service/vault_bankon/` | `routes.py`, `credential_provider.py`, `manage_credentials.py`, `manage_custody.py` |

This is the result of organic growth — `vault_manager` came first (no encryption, just `os.chmod 0o600`), then `encrypted_vault_manager` was added for AION-tier secrets, then BANKON Vault landed as the canonical custody surface for the handoff ceremony. The first two are now **audit blockers**: a security review will flag plaintext credentials and the duplicate Fernet master key, and the human-overseer handoff in `vault_bankon/` is undermined as long as the other two stores hold parallel copies of secrets under their own keys.

This document plans the migration. It is **not** a single-PR effort — the migration is sequenced into four phases that ship independently, each with verification.

## Target end-state

One vault. BANKON Vault is the single encrypted credential store. Concerns that don't fit BANKON's key-value-with-overseer-unlock shape get separate, smaller-scoped stores:

```
                     ┌─────────────────────────────────┐
                     │ BANKON Vault                    │
                     │ vault_bankon/                   │
                     │ - All API provider keys         │
                     │ - All agent private keys        │
                     │ - Treasury/operator privkeys    │
                     │ - Chain RPC URLs (sensitive)    │
                     └────────────┬────────────────────┘
                                  │ unlock once at startup
                                  │ (machine | human | DAIO overseer)
                                  ▼
                            os.environ injection
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────┐
   │  Service runtime — agents read from os.environ only │
   └──────────────────────────────────────────────────────┘

   ┌──────────────────────────┐    ┌──────────────────────────┐
   │ Sessions                 │    │ Access logs              │
   │ (in-memory + signed JWT) │    │ (append-only JSONL)      │
   │ NOT in BANKON            │    │ NOT in BANKON            │
   └──────────────────────────┘    └──────────────────────────┘
```

**What lives in BANKON:** any value that is a secret, has a stable string ID, and is read infrequently (≤1× per process lifetime).

**What does NOT live in BANKON:**
- **Sessions** — `vault_manager` currently writes per-session JSON files under `vault/sessions/`. Reading them on every authenticated request is fine when files are local; reading from BANKON on every request would require unlocking the vault per-request, which is wrong. Sessions should move to in-memory cache + signed JWT (HS256 with a key from BANKON), or to Redis if multi-instance.
- **Access logs** — `vault_manager.log_url_access` / `log_ip_access` are append-only inference-tracking telemetry. They aren't secrets; they're observability data. They should move to a dedicated `data/logs/access_log.jsonl` with the same shape as the existing catalogue events sink.
- **User folders** — `vault_manager`'s `vault/user_folders/{wallet}/` keeps per-wallet user-supplied keys. These already use a session-gated route (`/vault/user/keys/*`) and aren't part of the agent fleet's custody. They can stay file-backed but should be moved out of `vault/` into a clearly-named `data/user_data/` to remove the false "vault" association.

## Concern-by-concern migration

### 1. Agent private keys (`vault_manager.store_agent_key`, `get_agent_key`)

**Current state.** `id_manager_agent.py` writes ETH wallet privkeys to `vault/agents/{agent_id}.json` plaintext. Permissions 0o600.

**Target.** BANKON Vault entry with `id = agent_pk_<agent_id>`, `context = agent_identity`. Already partially implemented — `manage_custody.py transfer-agents` retrieves keys from this exact path.

**Migration steps.**
1. One-time: read every `vault/agents/*.json`, write to BANKON under `agent_pk_<agent_id>`. Idempotent (skip if entry exists). New `scripts/vault/migrate_agent_keys.py`.
2. Update `id_manager_agent.py:create_new_wallet` to write only to BANKON, never to `vault/agents/`.
3. After verification (every agent's key roundtrips correctly via BANKON), delete `vault/agents/`.

**Risk.** Loss of any agent key disconnects that agent from its on-chain identity. Mitigation: migration script runs in `--dry-run` first, writes a manifest of `(agent_id, address, vault_id, source_file)`, then `--commit` only if the operator approves the manifest.

**Verification.** `manage_custody.py preflight` already counts `agent_pk_*` entries. Add a check: after migration, that count equals the original `vault/agents/*.json` count.

### 2. API provider keys (`vault_manager.store_access_credential`)

**Current state.** Two parallel paths — `vault/credentials/*.json` (plaintext) and BANKON Vault entries via `manage_credentials.py store`. The audit deleted the dead routes pointing at the legacy path; `manage_credentials.py` is the only correct way today.

**Target.** BANKON Vault entries with the IDs already in `PROVIDER_ENV_MAP` (credential_provider.py:13-55).

**Migration steps.**
1. Inventory `vault/credentials/*.json`. For each, identify whether it maps to a BANKON `PROVIDER_ENV_MAP` ID. If yes, copy. If not, decide: add to map, or discard.
2. Delete `vault/credentials/`.

**Risk.** Low. BANKON is already the canonical path; the legacy folder may be empty or near-empty.

### 3. AION-tier secrets (`encrypted_vault_manager`)

**Current state.** Fernet-encrypted vault at `vault_encrypted/` with its own machine-mode `.master.key`. Used by `aion_agent`, `backup_agent`, `aion_production_service`. Holds whatever the AION layer calls "production secrets" — needs a code-walk to enumerate.

**Target.** Migrate all `EncryptedVaultManager.get(key)` callers to `BankonVault.retrieve(key)` (via `CredentialProvider`). Delete `encrypted_vault_manager.py` and `vault_encrypted/`.

**Migration steps.**
1. Walk `aion_agent.py:107`, `backup_agent.py:113`, `deploy/aion_production_service.py:34` — list every key the legacy module is asked for.
2. For each, decide a `PROVIDER_ENV_MAP`-compatible ID + env var name. Add to `credential_provider.py:PROVIDER_ENV_MAP`.
3. One-time migration script: unlock `EncryptedVaultManager`, read each known key, write to BANKON.
4. Switch importers to `os.environ.get(env_var)` — same pattern every other consumer uses.
5. Delete `encrypted_vault_manager.py` after a release with both paths active.

**Risk.** Medium. Fernet-encrypted store has its own machine-mode `.master.key` that the BANKON handoff doesn't touch — until this migration, an attacker with VPS root can still decrypt this vault even after the BANKON ceremony. **This is the audit blocker.**

**Sequencing concern.** The migration of (3) should happen BEFORE the user runs the BANKON handoff ceremony, OR the handoff ceremony should be re-run for `encrypted_vault_manager` separately. Cleanest path: migrate (3) first, retire `encrypted_vault_manager`, then run a single BANKON handoff that covers everything.

### 4. Sessions (`vault_manager.create_user_session`, `get_user_session`)

**Current state.** Per-session JSON in `vault/sessions/{token}.json`. Read on every authenticated request via `security_middleware.py`.

**Target.** Stateless JWT with HS256. Signing key lives in BANKON under `session_jwt_key`. Sessions become opaque to the filesystem.

**Migration steps.**
1. Add `session_jwt_key` to BANKON — generated as 64 random bytes on first startup post-migration.
2. Replace `vault_manager.create_user_session` with a JWT issuer that signs `{wallet, exp, scopes}` claims.
3. Replace `vault_manager.get_user_session` with JWT verification.
4. After deploy: invalidate all existing file-based sessions (delete `vault/sessions/`).

**Risk.** All in-flight sessions get logged out at deploy time. Acceptable for a self-hosted service with low session count; coordinate the deploy with the user.

**Out-of-scope for this plan.** A multi-instance deployment would want Redis or DB-backed sessions instead of JWTs (so that revocation works). mindX is single-instance today.

### 5. Access logs (`vault_manager.log_url_access`, `log_ip_access`)

**Current state.** JSONL append into `vault/access_log/{url,ip}.jsonl`. The HTTP routes `/vault/access/url` and `/vault/access/ip` are public per the audit (medium-severity finding).

**Target.** Move out of the vault module entirely. New file `agents/observability/access_log.py` mirroring the catalogue-event-sink pattern (`agents/catalogue/log.py`). Routes get session-gated.

**Migration steps.**
1. Copy the four log functions to a new module that doesn't import vault_manager.
2. Update the routes in `main_service.py:8019-8147` to call the new module + add session gate.
3. Delete `vault_manager`'s log_url_access / log_ip_access methods.
4. Move `vault/access_log/` → `data/logs/access/`.

**Risk.** Low. Telemetry data only.

### 6. User folders (`vault_manager.set_user_key`, `get_user_key`)

**Current state.** Per-wallet folder `vault/user_folders/{wallet}/` for user-supplied per-app keys (`/vault/user/keys/*`). Session-gated, working correctly.

**Target.** Same shape, different location. Move to `data/user_data/{wallet}/` to disassociate from "vault" naming.

**Migration steps.**
1. Rename root path constant in `vault_manager.py` from `vault/user_folders/` to `data/user_data/`.
2. Migrate existing folders.
3. After this and (1)-(5) ship, `vault_manager.py` becomes a thin shim with only user-folder methods. Either keep as-is (smallest surface), or rewrite as `mindx_backend_service/user_data/` and delete `vault_manager.py` entirely.

**Risk.** Low.

## Sequencing

Phases must ship in this order. Each is a separate PR / deploy.

**Phase 1 — Audit-blocker triage (1 week).**
- Migrate (3) AION-tier secrets to BANKON.
- Delete `encrypted_vault_manager.py` and `vault_encrypted/`.
- Run BANKON handoff ceremony if not already done. After this phase, no plaintext or Fernet-keyed credentials exist outside BANKON's overseer-aware custody.

**Phase 2 — Agent key consolidation (1 week).**
- Migrate (1) agent private keys.
- Update `id_manager_agent.py` to write to BANKON only.
- Delete `vault/agents/`.

**Phase 3 — Session + telemetry hygiene (1-2 weeks).**
- Migrate (4) sessions to JWT.
- Migrate (5) access logs out of vault_manager.
- Session-gate `/vault/access/*` routes.

**Phase 4 — Cleanup (3 days).**
- Migrate (2) leftover legacy provider keys.
- Migrate (6) user folders to `data/user_data/`.
- Decide whether `vault_manager.py` shrinks to a shim or gets replaced. Either way, the `vault/` directory is empty by the end.

## Verification (per phase)

- **Phase 1:** `grep -r "encrypted_vault_manager" /home/hacker/mindX` returns zero matches. `ls vault_encrypted/` errors. AION + backup agents start cleanly + decrypt their secrets.
- **Phase 2:** `manage_custody.py preflight` shows `agent_pk_*` count matches `data/identity/registry.jsonl` count. Every agent's wallet address roundtrips: vault → IDManagerAgent → on-chain `IdentityRegistry.lookup`.
- **Phase 3:** Service start with no `vault/sessions/`. Login flow issues a JWT, JWT verifies via BANKON `session_jwt_key`. `/vault/access/*` returns 401 unauthenticated.
- **Phase 4:** `grep -r "from mindx_backend_service.vault_manager" /home/hacker/mindX` returns zero (or only the user-folder shim if kept). `vault/` is empty.

## Out of scope (deferred)

- **HSM-backed BANKON keys** — Stage 3 in the overseer model. Hardware-backed key derivation for the master key. Only relevant once the user runs from a host with a YubiKey / TPM.
- **Multi-region replication of `entries.json`** — orthogonal. Solved by infrastructure (e.g., btrfs snapshots replicated via syncthing), not by vault code.
- **Full audit trail beyond `overseer_history.jsonl`** — currently the audit log records overseer rotations only, not per-entry reads/writes. Adding write/read auditing belongs in BANKON itself, not this migration.

## Reference

- `mindx_backend_service/bankon_vault/` — the target.
- `mindx_backend_service/vault_manager.py:889` — `get_vault_manager` constructor entry point.
- `mindx_backend_service/encrypted_vault_manager.py:477` — `get_encrypted_vault_manager` entry point.
- `mindx_backend_service/bankon_vault/credential_provider.py:13-55` — `PROVIDER_ENV_MAP` to extend per phase.
- `manage_credentials.py` — CLI for adding entries to BANKON.
- `manage_custody.py preflight` — sanity check after each phase.
- `docs/BANKON_VAULT_HANDOFF.md` — operator runbook (re-runnable per phase if custody changes).
- `/home/hacker/.claude/plans/jolly-baking-wilkinson.md` — vault audit plan that triggered this migration.
