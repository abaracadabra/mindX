# BANKON Vault — canonical reference

> The encrypted credential store that holds every API key and agent private key the running mindX service depends on. This doc is the durable understanding — what it is, how it works, where to look. For the operator ceremony, see [BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md). For the plan to retire the older `vault_manager` / `encrypted_vault_manager` modules, see [LEGACY_VAULT_MIGRATION.md](LEGACY_VAULT_MIGRATION.md). For the audit that drove the 2026-04-28 remediation pass, see [`/home/hacker/.claude/plans/jolly-baking-wilkinson.md`](../../.claude/plans/jolly-baking-wilkinson.md).

## What it is

`mindx_backend_service/bankon_vault/` is the canonical encrypted credential store. It is **overseer-aware**: the same vault file works under three custody modes — Machine, Human, or DAIO — with the unlock root-of-trust swapping per mode while the encrypted entries stay byte-stable.

```
core code    → mindx_backend_service/bankon_vault/{vault,overseer,credential_provider,routes}.py
on-disk      → mindx_backend_service/vault_bankon/
operator CLI → manage_credentials.py (store/list/delete/providers/load)
ceremony CLI → manage_custody.py (preflight, challenge, dry-run, commit, smoke-test, …)
airgap tool  → scripts/vault/airgap_sign.py (single file, no mindX imports)
test suite   → make test-vault → tests/bankon_vault/ (10 tests, ~1.2 s)
audit log    → data/governance/overseer_history.jsonl (append-only, fsync'd)
```

## Crypto stack

Layered HKDF over a single 32-byte salt that never rotates. The IKM source swaps per overseer; the final HKDF that produces the vault key is identical for all three modes.

```
                                    +--- (Machine) raw 64B from .master.key  --+
unlock IKM source ------------------+--- (Human)   raw 64B = HKDF(             |
(swappable per overseer)            |       ikm=65B EIP-191 sig,               |
                                    |       salt=vault_salt,                   |
                                    |       info=b"bankon-overseer-human-v1:"  |
                                    |            + addr_20)                    |
                                    +--- (DAIO)    raw 64B = HKDF(             |
                                            ikm=on-chain attestation digest,   |
                                            salt=vault_salt,                   |
                                            info=b"bankon-overseer-daio-v1:"   |
                                                 + registry + chain_id)        |
                                                                               |
                              vvv  uniform stage-2 (vault.py:235-242, 245-255) v
                              vault_key (32B) = HKDF-SHA512(
                                  ikm=raw_64B,
                                  salt=vault_salt,
                                  info=b"bankon-vault-master-key",
                                  length=32)

per-entry key (32B) = HKDF-SHA512(
    ikm=vault_key,
    salt=vault_salt,
    info="bankon-entry:<entry_id>:<context>",
    length=32)

ciphertext = AES-256-GCM(
    key=per-entry key,
    iv=12B random per write,
    aad=entry_id,
    pt=value-utf8)
```

- Passphrase mode (`unlock_with_passphrase`) uses PBKDF2-HMAC-SHA512 with 600 000 iterations (OWASP 2024) — used by the test suite, not by production.
- All HKDFs share the same salt (`vault_dir/.salt`, 32 random bytes — created once at first use, never rotated, even across overseer rotations).
- Per-entry domain separation means compromising one entry's per-entry key does **not** disclose another's.
- AES-GCM AAD = entry_id — ciphertext is bound to its entry name; renaming = decrypt failure.

## On-disk layout

`mindx_backend_service/vault_bankon/` (mode `0700`)

| File | Mode | Contents | Lifecycle |
|------|------|----------|-----------|
| `entries.json` | `0600` | `{version, cipher, kdf, pbkdf2_iterations, entries:[…]}` — every entry's `{id, ciphertext_hex, iv_hex, context, created_at, updated_at, access_count}` | Mutated on every `store/delete/rotate_overseer` |
| `.salt` | `0600` | 32 random bytes | One-shot, never rotated |
| `.master.key` | `0400` | 64 random bytes | Present in **machine custody**; deleted (zeroized first) on Human/DAIO handoff |
| `.human_overseer_active` | `0600` | `{since, overseer_kind, overseer_identity}` | **Sentinel** — present after non-machine handoff. Blocks `unlock_with_key_file` (vault.py:191-197) |
| `.overseer_proof.json` | `0600` | `{kind, address, signature, message, ts}` for human overseer | Lets the service re-unlock without re-signing (overseer.py:250-275) |
| `.rotation.lock` | `0600` | PID + timestamp | Held during `_rotate_overseer_locked`, exclusive `fcntl.flock` (vault.py:298-328) |
| `.rotation.ok` | `0600` | `{candidate_sha, ts, new_overseer_fingerprint, entries_count}` | Two-phase commit marker; required <300 s old at commit (vault.py:480-507) |
| `entries.json.candidate` | `0600` | Re-encrypted entries pending commit | Atomically swapped via `os.replace` |

The audit log lives **outside** the vault dir at `data/governance/overseer_history.jsonl` — append-only, fsync'd, one row per rotation.

## Three custody modes

Implemented as three classes satisfying one Protocol (`overseer.py:30-50`):

| Overseer | `kind` | `identity` | IKM source | Status |
|----------|--------|------------|-----------|--------|
| `MachineOverseer` | `"machine"` | filesystem path | `.master.key` 64 random bytes | Active default |
| `HumanOverseer` | `"human"` | `0x…` EOA | 65-byte EIP-191 signature over a challenge text | Implemented + tested end-to-end |
| `DAIOOverseer` | `"daio"` | `daio:<chain_id>:<governor_addr>` | On-chain Governor proposal attestation digest | **Stub** — `NotImplementedError` for `produce_raw_key` and `verify_evidence` (overseer.py:232-244) |

The Protocol lets `vault.rotate_overseer(new_overseer, …)` be polymorphic — same atomic swap, same scratch verify, same audit log row, for any pair of source/target overseers. Going Human → DAIO later is one call.

The two-stage HKDF (per-overseer `_INFO_PREFIX` for IKM, then unified `b"bankon-vault-master-key"` for the vault key) is what makes this clean. Same salt, same `entries.json`, same per-entry derivation path — every overseer ends up at the same 32-byte vault key from a different root of trust.

## Lifecycle

### Startup — machine mode (today)

1. FastAPI `@app.on_event("startup")` (`main_service.py:4613-4630`).
2. `cred_provider = CredentialProvider()` → `BankonVault()` constructor reads `.salt`, loads encrypted `entries.json` into RAM, stays locked.
3. `cred_provider.load_from_vault()` → `unlock_with_key_file(None)`.
4. `unlock_with_key_file` (`vault.py:182-211`): checks for sentinel; if absent, reads `.master.key`, HKDF→32B vault key, sets `_locked=False`.
5. CredentialProvider iterates `PROVIDER_ENV_MAP` (21 entries, `credential_provider.py:13-55`), retrieves each, injects into `os.environ`.
6. `vault.lock()` zeroizes `_vault_key`. Vault back to locked. Total ~50 ms.

### Startup — sentinel present (after Human handoff)

1. Steps 1–3 unchanged.
2. Step 4 raises `RuntimeError("Vault is under HumanOverseer custody…")`.
3. FastAPI startup catches it, logs warning, **service continues** with no credentials in `os.environ`. Agents fail-open hours later when they hit their first LLM call.
4. Recovery has two paths:
   - **Automatic (post-handoff design):** the service is supposed to call `load_human_from_proof(.overseer_proof.json, salt)` → `unlock_with_overseer(...)` at startup. Today this only happens via the `manage_custody.py` CLI, not in `main_service.py`'s startup hook — gap noted as a follow-up.
   - **Operator-mediated:** SSH and run `python manage_custody.py preflight` then unlock via the proof file, OR `POST /vault/credentials/reunlock` (admin-gated; replays the proof file by default — `routes.py:reunlock`).

### Request-time

- `routes.py:37` creates a module-level singleton `_vault = BankonVault()`. **Locked at import** — every store/list/delete on `/vault/credentials/*` goes through `CredentialProvider` which unlocks → operates → re-locks.
- `vault.store/retrieve/delete/list_entries` (`vault.py:647-708`) all gate on `_locked` and raise if locked.

### Lock + zeroize

- `vault.lock()` (`vault.py:635-642`) overwrites `_vault_key` bytes with `\x00`s before reassigning to `None`. AES-GCM context (`AESGCM(key)` instances) is created per-call and discarded.

## HTTP surface

Mounted via `app.include_router(bankon_vault_router)` at `main_service.py:4607`.

| Path | Method | Auth | Returns |
|------|--------|------|---------|
| `/vault/credentials/status` | GET | public | Vault info (vault_dir stripped) |
| `/vault/credentials/providers` | GET | public | Provider IDs + env-var mappings |
| `/vault/credentials/list` | GET | admin (`require_admin_access`) | Metadata only — no plaintexts |
| `/vault/credentials/store` | POST | admin | `{status, cipher}` |
| `/vault/credentials/delete` | DELETE | admin | `{status}` or 404 |
| `/vault/credentials/reunlock` | POST | admin | `{status, fingerprint, providers_loaded, env_vars, source}` — Flow A: replay `.overseer_proof.json`; Flow B: `{address, signature, message}` body |

The two `/admin/vault/{keys,migrate}` endpoints are admin-gated since `be45f113` (the global auth middleware was already enforcing 401 for anonymous callers; the per-route gate adds `wallet ∈ admin_addresses`).

Rate limit: 30 req/min/client, all `/vault/*` share one bucket (`security_middleware.py:49`). No HTTP path can call `unlock_with_key_file` or return plaintext entry values.

## Tests

`make test-vault` (Makefile target) — 10 tests in `tests/bankon_vault/`, ~1.2 s:

- `test_rotate_overseer.py` — 1 happy-path Machine→Human rotation: 5 entries preserved, `.master.key` deleted, sentinel + proof written, sentinel guard fires on subsequent `unlock_with_key_file`, proof-file re-unlock works, audit log gets one row.
- `test_rotate_overseer_negative.py` — 5 rejection paths: malformed signature (wrong length), signature replay against different challenge, evidence kind mismatch (`"daio"` vs `HumanOverseer`), signature signed by different EOA, missing `MINDX_VAULT_ALLOW_OVERSEER_ROTATION` env flag.
- `test_reunlock_endpoint.py` — 4 endpoint tests: Flow A (proof-file replay), Flow B (body evidence overrides), refuse-without-sentinel (409), refuse-without-proof-or-body (404).

The defense-in-depth checks for stale `.rotation.ok` (>300 s) and candidate SHA drift between dry-run and commit (`vault.py:506-512`) are intentionally **not** tested — the locked single-call `_rotate_overseer_locked` always re-runs the dry-run path before checking those guards, so they're unreachable from outside without white-box mocking that ossifies internal call structure.

## Reading order for a new contributor

1. **This doc** — what + how.
2. [`mindx_backend_service/bankon_vault/vault.py`](../mindx_backend_service/bankon_vault/vault.py) — implementation. Most of the cryptographic decisions live here. Read top to bottom.
3. [`mindx_backend_service/bankon_vault/overseer.py`](../mindx_backend_service/bankon_vault/overseer.py) — the Protocol + three implementations.
4. [`tests/bankon_vault/test_rotate_overseer.py`](../tests/bankon_vault/test_rotate_overseer.py) — the rotation contract test. Best single file to understand what the vault guarantees.
5. [`manage_custody.py`](../manage_custody.py) — the connected-side CLI. Each subcommand is a self-contained ceremony step.
6. [BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md) — operator runbook for the airgapped Machine → Human ceremony with threat model and recovery flows.
7. [LEGACY_VAULT_MIGRATION.md](LEGACY_VAULT_MIGRATION.md) — sequenced plan to retire `vault_manager` and `encrypted_vault_manager`. The Phase 1 retirement of `encrypted_vault_manager` is the real audit blocker before any Human handoff is meaningful — its parallel Fernet vault still has its own machine-mode `.master.key` that the BANKON handoff doesn't touch.

## When to use what

| You want to … | Path |
|---------------|------|
| Store a new API key | `python manage_credentials.py store <provider_id> <value>` |
| List stored entries (no plaintexts) | `python manage_credentials.py list` |
| Provision the deployer key for the iNFT campaign | `python manage_credentials.py store zerog_deployer_pk 0x...` |
| Provision the x402-AVM (Algorand) buyer wallet — see [X402.md](X402.md) | `python manage_credentials.py store algorand_mnemonic "<25-word>"` ; also `algorand_recipient_address`, `algorand_usdc_asa_id`, `x402_avm_facilitator_url` |
| Run the airgapped handoff ceremony | Follow [BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md) |
| Recover after a service restart that came up with empty `os.environ` | `POST /vault/credentials/reunlock` (admin) or `python manage_custody.py` (SSH) |
| Verify the rotation contract still holds before a deploy | `make test-vault` |
| Read who currently owns the vault | `cat data/governance/overseer_history.jsonl` (append-only) |
| Plan moving Stage 1 (Human) → Stage 2 (DAIO) | The DAIO migration section of this doc + `overseer.py:200-244` (DAIOOverseer stub) |

## What is *not* in BANKON Vault (and why)

- **User sessions.** Per-session JSON in `vault/sessions/` (legacy `vault_manager`). Reading sessions on every authenticated request would mean unlocking the vault per-request; instead they should move to in-memory + signed JWT (HS256 with a key from BANKON). Plan: [LEGACY_VAULT_MIGRATION.md §4](LEGACY_VAULT_MIGRATION.md).
- **Access logs.** URL/IP access events — not secrets, just observability. Plan: [LEGACY_VAULT_MIGRATION.md §5](LEGACY_VAULT_MIGRATION.md).
- **Per-wallet user folders.** `vault/user_folders/{wallet}/` for user-supplied per-app keys; session-gated, working correctly. Should move out of `vault/` into `data/user_data/` to remove the false "vault" association. Plan: [LEGACY_VAULT_MIGRATION.md §6](LEGACY_VAULT_MIGRATION.md).
- **AION-tier secrets.** Currently in `vault_encrypted/` under Fernet. Audit-blocker: that vault has its own machine-mode `.master.key` that a BANKON handoff does not touch. Plan: [LEGACY_VAULT_MIGRATION.md §3 / Phase 1](LEGACY_VAULT_MIGRATION.md).

## Reference (one-liners)

| What | Where |
|------|-------|
| Core implementation | `mindx_backend_service/bankon_vault/vault.py` (~720 LOC) |
| Overseer protocol + three classes | `mindx_backend_service/bankon_vault/overseer.py` (~275 LOC) |
| Bridge to `os.environ` at startup | `mindx_backend_service/bankon_vault/credential_provider.py` |
| FastAPI router | `mindx_backend_service/bankon_vault/routes.py` |
| Connected-side CLI | `manage_credentials.py`, `manage_custody.py` |
| Airgap signer | `scripts/vault/airgap_sign.py` |
| Operator runbook | [docs/BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md) |
| Migration plan | [docs/LEGACY_VAULT_MIGRATION.md](LEGACY_VAULT_MIGRATION.md) |
| Audit (2026-04-28) | `/home/hacker/.claude/plans/jolly-baking-wilkinson.md` |
| Original overseer-design plan | `/home/hacker/.claude/plans/glimmering-growing-scroll.md` |
| Tests | `tests/bankon_vault/` — 10 via `make test-vault` |
| Append-only audit log | `data/governance/overseer_history.jsonl` |
| Live vault dir | `mindx_backend_service/vault_bankon/` |
| Production endpoint | https://mindx.pythai.net/vault/credentials/status |
