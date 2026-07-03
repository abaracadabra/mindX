# BANKON Vault — Complete Project Review

`(c) 2026 BANKON — all rights reserved`
SPDX-License-Identifier: Apache-2.0

> **Scope.** Consolidates everything currently known about BANKON Vault as a
> single review document. Sits alongside the existing canonical set:
> [`BANKON_VAULT.md`](BANKON_VAULT.md) (crypto stack, on-disk layout, custody
> modes, lifecycle, HTTP surface, tests),
> [`BANKON_VAULT_HANDOFF.md`](BANKON_VAULT_HANDOFF.md) (operator ceremony),
> [`LEGACY_VAULT_MIGRATION.md`](LEGACY_VAULT_MIGRATION.md) (retirement plan
> for `vault_encrypted/`), and the broader
> [`VAULT_SYSTEM_DOCUMENTATION.md`](VAULT_SYSTEM_DOCUMENTATION.md) (ecosystem
> view: sessions, access logs, user folders, frontend `vault_manager.js`).
>
> **Status.** Production. Live behind `mindx.pythai.net/vault/*`.
> **Implementation.** `mindx_backend_service/bankon_vault/vault.py`.
> **Operator CLI.** `python manage_credentials.py store|list|delete|providers`.

---

## 1. Position in the stack

BANKON Vault is the **custody layer** of the PYTHAI triad. The triad has one
identity and three product surfaces:

```
   agenticplace.pythai.net        mindx.pythai.net           bankon.pythai.net
   ─────────────────────          ───────────────────         ──────────────────
   discovery / marketplace        augmentic intelligence      identity + payment
   agent listings, allchain.html  BDI engine, /vault/*        AlgoIDNFT, x402
                │                          │                          │
                └─────── single user table ┴──────── single identity ──┘
                                       │
                                       ▼
                                BANKON Vault
                          (AES-256-GCM + HKDF-SHA512)
                          custodia | clavis | sigillum
```

mindX users *are* AgenticPlace users *are* BANKON wallet holders *are* DAIO
voters because the user table is one table; the Vault is the encrypted store
that backs the identity column for users who want managed custody. Users who
prefer local custody route through **parsec-wallet** (Ledger HW backed) and
the Vault never holds their material. Both paths resolve to the same BONAFIDE
IDNFT.

The user chooses sovereignty; the system never chooses for them.

---

## 2. Crypto stack

| Concern              | Primitive                                  |
|----------------------|--------------------------------------------|
| Symmetric encryption | AES-256-GCM (authenticated, 96-bit IV)     |
| Key derivation       | HKDF-SHA512 (per-subkey domain separation) |
| Master seed entropy  | 32 bytes from `os.urandom`                 |
| Subkey derivation    | `HKDF(master, info="BANKON\|<scope>\|<id>", L=32)` |
| Per-record IV        | 12 bytes random per `encrypt()`            |
| File integrity       | GCM tag (16 bytes) appended to ciphertext  |
| File permissions     | 0600 (data), 0700 (directories)            |

This **supersedes** the legacy `vault_encrypted/` (Fernet/PBKDF2-SHA256, 100k
iterations). Fernet wraps AES-128-CBC + HMAC-SHA256; the new stack is
AES-256-GCM directly with explicit HKDF separation per scope. The migration
path is in [`LEGACY_VAULT_MIGRATION.md`](LEGACY_VAULT_MIGRATION.md).

### Domain separation strings

HKDF `info` parameters are stable and load-bearing — changing one is a
breaking migration:

```
BANKON|provider|<provider_id>           # 3 provider credentials
BANKON|agent|<agent_id>                 # 12 agent identity keys
BANKON|user|<wallet_addr>|<key_name>    # per-wallet user folders
BANKON|session|<session_id>             # session cookies
BANKON|access_log|<YYYYMMDD>            # daily access-log files
BANKON|<chain>|<agent_id>               # HD-style key derivation (HMAC-SHA512)
```

The last form is the one parsec-wallet exposes for client-side x402 signing:
`HMAC-SHA512(master_seed, "BANKON|<chain>|<agent_id>")[:32]` → 32-byte
private key, used to sign EIP-3009 USDC-Base authorizations and Algorand
payment txns. Production calls this via parsec-wallet's hardware path; the
in-process implementation in `vault.py` is the test/fallback interface.

---

## 3. Three custody modes

The Vault is intentionally **mode-aware** so the same identity can hold under
different trust assumptions without re-minting an IDNFT.

### Mode A — Managed (default)

The Vault holds the master seed encrypted under a process-derived key wrapped
by the OS keychain (Linux: libsecret; macOS: Keychain; OpenBSD vmm: encrypted
disk image). The mindX backend can sign on behalf of the user during an
authenticated session. **Lowest friction, highest trust assumption.**

- Issuance: `POST /users/register` with wallet signature
- Signing: `POST /vault/sign` with `X-Session-Token`
- Recovery: 24-word BIP-39 mnemonic shown once on registration

### Mode B — Hybrid (recommended)

Vault holds an **agent operating key** (the per-host x402 key under
`m/44'/283'/0xA402'/0/index`) but never holds the user's identity key
(`m/44'/0'/0'/0/0`). The identity key lives in parsec-wallet locally. Vault
can sign micropayments autonomously; promotion to identity-level actions
(IDNFT updates, governance votes) requires a fresh signature from parsec.

- Identity signs: locally via parsec-wallet
- Agent signs: via Vault, scoped capability token (1h TTL)
- Spending cap: configurable per agent in `data/config/vault_caps.json`

### Mode C — Sovereign

Vault holds nothing private. It holds only **public attestations** of which
identity owns which agent, so AgenticPlace and DAIO contracts can resolve
references. All signing happens in parsec-wallet on the user's device. The
Vault behaves as a read-only attestation cache.

- Issuance: parsec-wallet generates seed, mints IDNFT, posts attestation
- Signing: 100% local
- Vault role: cache + replay protection only

Mode is selected per-user at registration and stored in
`users(custody_mode)`. Changing mode requires a fresh wallet signature and a
re-attestation cycle.

---

## 4. On-disk layout

```
mindx_backend_service/
├── bankon_vault/                       # IMPLEMENTATION (Python module)
│   ├── __init__.py
│   ├── vault.py                        # Core encrypt/decrypt/derive
│   ├── credentials.py                  # Provider + agent credential store
│   ├── sessions.py                     # Session token lifecycle
│   ├── user_folders.py                 # Per-wallet key-value store
│   ├── access_log.py                   # URL + IP access tracking
│   ├── hkdf.py                         # HKDF-SHA512 wrapper
│   └── tests/
│       ├── test_vault.py
│       ├── test_credentials.py
│       ├── test_sessions.py
│       └── test_kat.py                 # Known-answer tests vs RFC 5869
│
├── vault_bankon/                       # ON-DISK STATE (production)
│   ├── .master.enc                     # Encrypted master seed
│   ├── .salt                           # 32-byte random salt
│   ├── .mode                           # Custody mode (A|B|C)
│   ├── .version                        # Crypto stack version (e.g. "2.0")
│   ├── providers/
│   │   └── credentials.enc             # 3 provider credentials, GCM
│   ├── agents/
│   │   └── identities.enc              # 12 agent identity keys, GCM
│   ├── sessions/
│   │   └── {session_id}.enc            # Active sessions
│   ├── user_folders/
│   │   └── 0x{40hex}/
│   │       └── {key}.enc               # Per-wallet user data
│   └── access_log/
│       ├── url_access_{YYYYMMDD}.jsonl.enc
│       ├── ip_access_{YYYYMMDD}.jsonl.enc
│       ├── url_index.json              # Cleartext metadata (counts)
│       └── ip_index.json               # Cleartext metadata (counts)
│
├── vault_encrypted/                    # LEGACY (Fernet/PBKDF2, deprecated)
│   └── …                               # Migrated by scripts/migrate_to_encrypted_vault.py
│
└── manage_credentials.py               # Operator CLI
```

File permissions are enforced on every write: 0600 for files, 0700 for
directories. The Vault refuses to read state if permissions are too loose.

---

## 5. Lifecycle

### 5.1 Genesis (per-instance, once)

1. Generate 32-byte `master_seed` from `os.urandom`.
2. Generate 32-byte `salt`.
3. Derive `wrap_key = HKDF(master_seed, info="BANKON|wrap|v2", L=32)`.
4. Encrypt `master_seed` under OS keychain → write `.master.enc`.
5. Write `.salt`, `.mode`, `.version`.
6. Emit 24-word BIP-39 mnemonic for operator-held offline backup.
7. **Operator ceremony.** Two operators independently verify the mnemonic
   reproduces the same master seed (see `BANKON_VAULT_HANDOFF.md`).

### 5.2 Steady state

- **Store:** `vault.encrypt(scope, id, plaintext)` →
  ciphertext + 12-byte IV + 16-byte GCM tag written atomically.
- **Retrieve:** `vault.decrypt(scope, id)` returns plaintext; failure logs
  a `SYSTEM_STATE` memory at `HIGH` importance, never returns partial data.
- **List:** metadata-only; never returns values.

### 5.3 Rotation

- **IV rotation:** every `encrypt()` generates a fresh IV. Reuse is fatal in
  GCM, so the Vault asserts uniqueness within a 2^32 envelope before write.
- **Subkey rotation:** triggered by version bump in `.version`. Re-derive
  all subkeys under new HKDF info, re-encrypt all records, fsync, then
  flip `.version`. Resumable.
- **Master rotation:** ceremony only. Requires both operators, generates new
  master, decrypts under old, re-encrypts under new. Mnemonic invariant
  preserved via additive backup.

### 5.4 Deletion

- **Record:** overwrite ciphertext file with zeros, then unlink. Index entries
  removed from in-memory cache.
- **User folder:** entire `user_folders/0x{40hex}/` zeroed and removed; index
  cleaned.
- **Vault destroy:** ceremony only. Zeroes master, salt, all records. Logged
  with operator signatures.

### 5.5 Migration from legacy

`scripts/migrate_to_encrypted_vault.py` reads each Fernet record from
`vault_encrypted/`, decrypts, re-encrypts under AES-256-GCM with the new
HKDF info string, writes to `vault_bankon/`, verifies round-trip, and only
then deletes the legacy file. Resumable; idempotent; manifest written to
`vault_bankon/.migration_manifest.json`.

---

## 6. HTTP surface

Mounted under `mindx.pythai.net` by the FastAPI app. All endpoints except
the public session-validate require `X-Session-Token`.

### 6.1 Provider credentials (operator scope)

```
POST   /vault/credentials/store         # body: { provider, api_key, metadata }
GET    /vault/credentials/get/{id}      # metadata only, never the value
GET    /vault/credentials/list          # list providers
DELETE /vault/credentials/{id}
```

### 6.2 Agent identity keys (operator scope)

```
POST   /vault/agents/register           # body: { agent_id, public_address }
GET    /vault/agents/{agent_id}         # public_address only
GET    /vault/agents/list
DELETE /vault/agents/{agent_id}
```

Private keys are **never** returned over HTTP. Signing happens server-side:

```
POST   /vault/sign/eip3009               # body: { agent_id, pay_to, value, chain }
POST   /vault/sign/algorand              # body: { agent_id, receiver, amount, params }
```

### 6.3 User folders (signature-scoped)

```
GET    /vault/user/keys                  # list key names for authed wallet
GET    /vault/user/keys/{key}            # get value
PUT    /vault/user/keys/{key}            # set value (JSON body)
DELETE /vault/user/keys/{key}
```

Keys: `1–128` chars, `[a-zA-Z0-9_.-]`. Values: JSON. Access is **only** to
the folder corresponding to the public key holding the valid session token.
No whole-vault or cross-wallet access.

### 6.4 Sessions

```
GET    /users/session/validate          # query session_token | header X-Session-Token
POST   /users/logout                    # invalidates current session
```

Sessions are created only after successful wallet signature verification
(ARC-60 challenge for Algorand identities, EIP-191 for EVM).

### 6.5 Access tracking (ML inference feed)

```
POST   /vault/access/url
POST   /vault/access/ip
GET    /vault/access/url/history?url=&days_back=&limit=
GET    /vault/access/ip/history?ip=&days_back=&limit=
GET    /vault/access/summary            # aggregate for ML model ingestion
```

Cleartext indices for counts; encrypted JSONL for full records.

### 6.6 Access gate (optional)

Session **issuance** can be gated on on-chain state. Env vars:

```
MINDX_ACCESS_GATE_ENABLED=true
MINDX_ACCESS_GATE_TYPE=erc20|erc721
MINDX_ACCESS_GATE_CONTRACT=0x…
MINDX_ACCESS_GATE_RPC_URL=…
MINDX_ACCESS_GATE_MIN_BALANCE=1
```

DAIO keyminter contracts (`VaultKeyDynamic` / `VaultKeyIntelligent`) work as
the ERC-721 gate. See `LIT_AND_ACCESS_ISSUANCE.md`.

---

## 7. Tests

`mindx_backend_service/bankon_vault/tests/` runs under pytest. Coverage
targets: 95% line, 90% branch on `vault.py` and `credentials.py`.

| Test file              | Covers                                                     |
|------------------------|------------------------------------------------------------|
| `test_vault.py`        | Encrypt/decrypt round-trip, IV uniqueness, tag verification |
| `test_credentials.py`  | Store, retrieve, list, delete; metadata isolation           |
| `test_sessions.py`     | Signature verification, TTL, revocation                     |
| `test_user_folders.py` | Cross-wallet isolation; permission checks                   |
| `test_access_log.py`   | Append-only, daily rotation, summary aggregation            |
| `test_kat.py`          | Known-answer tests against RFC 5869 (HKDF) vectors          |
| `test_migration.py`    | Fernet → GCM migration, resumability, integrity manifest    |
| `test_perms.py`        | Refuses to read on loose file modes                         |
| `test_concurrency.py`  | Atomic write under concurrent encrypt/decrypt               |

Property-based tests use `hypothesis` for ciphertext-malleability resistance
(any single bit flip in ciphertext must raise `InvalidTag`).

---

## 8. Integration map

### 8.1 AgenticPlace ← Vault

AgenticPlace agents register a public address via `/vault/agents/register`.
The agent listing on `agenticplace.pythai.net` references that address; the
private material never leaves the Vault (Mode A) or never enters it at all
(Mode C). Per-call x402 invoicing uses the Vault-held agent key for
EIP-3009 signing or Algorand payment signing.

### 8.2 mindX ← Vault

mindX's `/agenticplace/agent/call` endpoint hits the Vault for the calling
agent's signing key when an upstream API requires authentication; for x402
challenges, it routes through `/x402/settle` which calls Vault sign endpoints
and submits to parsec-facilitator on Algorand or the EVM x402 facilitator on
Base/Polygon. The BDI Belief layer records vault access events through the
existing memory system (`SYSTEM_STATE` for credentials, `INTERACTION` for
URL/IP access).

### 8.3 BANKON ← Vault

`bankon.pythai.net` wallet UI reads the public address from the Vault for
display and proves ownership by requesting a signed challenge through either
the Vault (Mode A) or parsec-wallet (Mode B/C). The AlgoIDNFT subject address
is the identity public key derived at `m/44'/0'/0'/0/0`; Vault never holds
this in Mode B/C.

### 8.4 DAIO ← Vault

DAIO governance (Boardroom / Senatus / CEO) signs on-chain proposals through
the Vault when running under managed custody. The Censura.sol circuit-breaker
state mirrors the Vault's local circuit-breaker (5 BDI failures → open) so
external observers can verify why execution was paused. Vault-signed proposals
carry the agent's BONAFIDE clearance tier in the signature payload.

### 8.5 x402 + parsec-wallet ← Vault

Per the `BANKON|<chain>|<agent_id>` derivation in §2, Vault and parsec-wallet
share an identical HKDF/HMAC derivation surface. A key derived in Vault Mode
A is bit-for-bit the key parsec would derive locally given the same master
seed. This means a user can move between custody modes without re-minting
agent identities — the public addresses are stable across modes.

### 8.6 chainmapping (allchain.html) ← Vault

The Vault's chain registry is sourced from `agenticplace.pythai.net/allchain.html`
(2500+ EVM chains). Each chain entry resolves to a derivation namespace
(`BANKON|<chain>|...`). The on-chain mirror is `ChainOracle.sol`, which the
CEOAgent reads; only chains with active agent activity are mirrored to L1
(realistically ~50–100). The full registry stays off-chain in `allchain.html`.

---

## 9. DAIO blockchain deployment alignment

The Vault is **off-chain custody** for **on-chain identities**. The DAIO
deployment plan (Polygon EVM + Algorand) consumes the Vault's signing surface:

### 9.1 Polygon (Foundry, Solidity)

Nine contracts under BONAFIDE Latin naming:

| Contract          | Vault interaction                                        |
|-------------------|----------------------------------------------------------|
| `Genius.sol`      | Root authority; multisig owner held outside Vault         |
| `BonaToken.sol`   | ERC20 $BANKON mirror; bridged 1:1 to Algorand ASA         |
| `Senatus.sol`     | On-chain Boardroom; vault signs CEO commits               |
| `Censura.sol`     | Circuit breaker; mirrors vault local state                |
| `Fides.sol`       | Bridge attester; verifies Algorand state proofs           |
| `SponsioPactum.sol` | Agent staking/slashing; vault signs stake transactions  |
| `Tabularium.sol`  | Immutable Gödel-journal SHA-256 commits; vault writes     |
| `Tessera.sol`     | ERC-8004 identity; vault provides agent public addresses  |
| `ChainOracle.sol` | Mirror of `allchain.html`; reporter signs through vault   |

Foundry layout:

```
contracts/
├── foundry.toml                          # solc 0.8.26, optimizer 200, via_ir true
├── remappings.txt                        # forge-std, openzeppelin
├── src/
│   ├── Genius.sol
│   ├── BonaToken.sol
│   ├── Senatus.sol
│   ├── Censura.sol
│   ├── Fides.sol
│   ├── SponsioPactum.sol
│   ├── Tabularium.sol
│   ├── Tessera.sol
│   └── ChainOracle.sol
├── script/
│   ├── DeployPolygon.s.sol               # mainnet deployer
│   ├── DeployAmoy.s.sol                  # testnet
│   └── PostDeployWiring.s.sol            # role grants, ownership transfer
├── test/
│   ├── unit/                             # per-contract unit tests
│   ├── invariant/                        # stateful fuzzing
│   ├── fork/                             # mainnet-fork integration
│   └── Integration.t.sol                 # full cross-contract happy path
└── broadcast/                            # deploy artifacts (gitignored except mainnet)
```

Headers on every `.sol`:

```solidity
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity ^0.8.26;
```

### 9.2 Algorand (algopy)

| Asset / Contract      | Vault interaction                                  |
|-----------------------|----------------------------------------------------|
| `$BANKON` ASA         | Reserve = Genius-owned address; vault holds no privs|
| `BONAFIDE` ASA        | Clawback = Fides app address (deterministic)        |
| `Dojo.algo`           | Reputation rank reads/writes; vault-signed deltas   |
| `AlgoIDNFT.algo`      | Soulbound IDNFT; identity key from m/44'/0'/0'/0/0  |
| `x402Facilitator.algo`| Settles parsec x402 invoices                        |

The clawback pattern is what makes Algorand the right home for Dojo:
*containment without kill switch* (per `DAIO.md`). Reputation can be revoked
without burning the underlying identity.

### 9.3 Deploy sequence (Algorand-first)

1. **Algorand mainnet first** (cheaper, faster, clawback anchors everything):
   - Mint `$BANKON` ASA → reserve = Genius multisig
   - Mint `BONAFIDE` ASA, `clawback = Fides app address` (pre-computed)
   - Deploy `Dojo.algo`, `AlgoIDNFT.algo`, `x402Facilitator.algo`
   - Seed initial reputation for 7 soldiers + CEOAgent from `/dojo/standings`

2. **Polygon mainnet:**
   - `forge script DeployPolygon --broadcast --verify --rpc-url $POLYGON_RPC`
   - Order: `Genius` → `BonaToken` → `Tessera` → `Tabularium` →
     `SponsioPactum` → `Senatus` → `Censura` → `Fides` → `ChainOracle`
   - `PostDeployWiring.s.sol` transfers ownership to Timelock + 4-of-7 Safe
   - `Fides.setAlgorandBridge(<indexer>, <state-proof verifier>)`

3. **mindX config:**
   - Write deployed addresses → `data/config/daio_contracts.json`
   - Restart CEOAgent
   - Flip `DAIO_ONCHAIN=true`

4. **Smoke test on mainnet:**
   - No-op boardroom session → `/daio/boardroom/commit` → Senatus event
   - One reputation delta → BONAFIDE clawback txn on Algorand
   - One x402-gated agent call end-to-end via parsec-wallet

---

## 10. Operator ceremony

From [`BANKON_VAULT_HANDOFF.md`](BANKON_VAULT_HANDOFF.md). Required for:
genesis, master rotation, vault destroy, custody-mode-A → mode-B/C downgrade.

**Participants.** Two operators, independent hardware (ideally OpenBSD vmm
+ Ledger Nano, separate physical locations). One off-site witness signs
the ceremony log.

**Protocol.**

1. Both operators load the genesis script on air-gapped machines.
2. Each independently generates 32 bytes from `os.urandom`.
3. Both seeds XOR'd to produce the master.
4. BIP-39 mnemonic for the XOR'd master is computed.
5. Both operators verify the mnemonic reproduces the same master.
6. Mnemonic split via Shamir 3-of-5 across operator + witness + safe + safe
   + safe (geographically separated).
7. Ceremony log signed by both operators + witness, posted to Tabularium.

**Recovery.** Requires three of the five Shamir shares to reconstruct.

---

## 11. Legacy migration

From [`LEGACY_VAULT_MIGRATION.md`](LEGACY_VAULT_MIGRATION.md). One-shot,
resumable, idempotent.

```bash
cd mindx_backend_service
python scripts/migrate_to_encrypted_vault.py \
    --source vault_encrypted/ \
    --target vault_bankon/ \
    --verify-round-trip \
    --manifest vault_bankon/.migration_manifest.json
```

Process:

1. Decrypt each Fernet record under old PBKDF2-derived key.
2. Re-derive subkey under new HKDF-SHA512 info string.
3. Encrypt under AES-256-GCM with fresh IV.
4. Write to `vault_bankon/`; fsync.
5. Round-trip verify decrypt produces identical plaintext.
6. Append `{source_path, target_path, sha256, status}` to manifest.
7. Only after manifest write: zero and unlink legacy file.

Manifest is the audit trail; never delete it. After migration completes and
operator signs off, `vault_encrypted/` should be removed entirely from the
filesystem (not just emptied).

---

## 12. Threat model & known limits

| Threat                                          | Mitigation                                                   |
|-------------------------------------------------|--------------------------------------------------------------|
| Filesystem read by unauthorized process         | 0600 / 0700 perms; refuses to read on looser modes           |
| Master seed leak from running process memory    | Subkeys zeroed after use; `mlock` on master pages            |
| OS keychain compromise                          | Falls back to operator passphrase; ceremony to rotate master  |
| GCM IV reuse                                    | Asserted unique within 2^32; ceremony to rotate master       |
| Side-channel on AES (cache, timing)             | Uses `cryptography` library (constant-time AES-NI on x86_64) |
| Quantum (Shor on RSA/ECDSA)                     | Out of scope for Vault itself; mitigated at Algorand layer    |
|                                                 | via state-proof finality (per `parsec` quantum integration)   |
| Operator collusion                              | 3-of-5 Shamir; cross-operator ceremony log on Tabularium     |
| `manage_credentials.py` typo destroys data      | `--confirm` required on `delete`; soft-delete with 7d TTL     |
| Network gate misconfigured                      | Vault defaults to closed; explicit `MINDX_ACCESS_GATE_ENABLED`|

**Known limits.**

- The cross-chain identity bridge (Algorand → EVM Tessera) is **one-way**.
  Revocations on Algorand stay valid on EVM until the EVM attestation expires
  or is overridden. The relayer should proactively push revocations as
  zero-credential attestations with `expiresAt = block.timestamp + 1`.
- The Vault does not currently support hardware-signing for the master seed.
  Mode A requires the OS keychain. Mode C avoids this entirely by holding
  nothing private.
- Per-agent spending caps are local-only; they are not enforced on-chain.
  An attacker with the agent key can exceed caps until the next vault-issued
  signature is required.

---

## 13. Open items

| # | Item                                                                | Owner       | Priority |
|---|---------------------------------------------------------------------|-------------|----------|
| 1 | Wire `manage_credentials.py` into systemd timer for daily rotation  | operator    | M        |
| 2 | Replace OS-keychain fallback with hardware token (YubiKey HMAC)     | infra       | M        |
| 3 | Add `POST /vault/sign/state-proof` for Algorand state-proof signing | dev         | L        |
| 4 | Publish Foundry test suite for `Fides.sol` Algorand verifier        | dev         | H        |
| 5 | Audit pass on `bankon_vault/` module by external firm               | ops         | H        |
| 6 | Document ceremony recovery drill cadence (suggest quarterly)        | ops         | M        |
| 7 | Migrate `vault_encrypted/` → `vault_bankon/` on production          | ops         | H        |
| 8 | Switch x402 facilitator from parsec-test to parsec-mainnet          | dev         | H        |

---

## 14. References

- `BANKON_VAULT.md` — canonical crypto/layout reference
- `BANKON_VAULT_HANDOFF.md` — operator ceremony
- `LEGACY_VAULT_MIGRATION.md` — Fernet → GCM migration
- `VAULT_SYSTEM_DOCUMENTATION.md` — broader vault ecosystem (sessions, access
  logs, frontend `vault_manager.js`)
- `LIT_AND_ACCESS_ISSUANCE.md` — token-gating for session issuance
- `DAIO.md` — DAIO framework; Polygon + Algorand split rationale
- `DAIO_DEPLOYMENT_INTEGRATION.md` — deploy sequence; chain registry; x402
- `mindx_backend_service/bankon_vault/vault.py` — implementation
- `mindx_backend_service/manage_credentials.py` — operator CLI
- `agenticplace.pythai.net/allchain.html` — chain registry
- BONAFIDE contracts — `github.com/bankon/bonafide`
- parsec-wallet — local custody; ARC-52 HD derivation

---

## 15. Cypherpunk2048 conformance

- [x] Apache-2.0 + `(c) 2026 BANKON — all rights reserved` headers on all source
- [x] Flat snake_case module layout
- [x] No badges, no marketing copy, no emoji in source
- [x] Latin operational vocabulary preserved (custodia, clavis, sigillum,
      vectigal, ianitor, porta in `marketspace/src/bankon_vault/`)
- [x] Python ≥ 3.12
- [x] Foundry for Solidity; no Hardhat
- [x] No Docker; Podman + OpenBSD vmm
- [x] Open-source dependencies only; no proprietary crypto

---

*End of review.*
