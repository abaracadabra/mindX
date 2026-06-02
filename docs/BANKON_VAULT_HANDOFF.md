# BANKON Vault — operator handoff

The shortest path from *"my mindX has a vault somewhere and I don't really know
how to use it"* to *"I am the shadow-overlord, my keys are vault-encrypted, and
each participant is in its own isolated namespace."*

> **Audit status (snapshot at the time of writing):** machine custody
> (`.master.key` present, no `.human_overseer_active` sentinel, no
> `.overseer_proof.json`). Entries currently in vault: 3 — all in the
> `provider` context: `uniswap_trade_api_key`, `openrouter_api_key`,
> `gemini_api_key`. No `wordpress.agent.keys` entries provisioned yet. No
> overseer-history rows. Permissions are correct (`vault_dir` 0700,
> `entries.json` 0600, `.master.key` 0400, `.salt` 0600).
>
> See [§Audit findings](#audit-findings) for the full read of what *is* and
> *isn't* isolated today and the recommended next steps.

---

## 30-second mental model

```
                    ┌─────────────────────────────────────────────┐
                    │ BANKON Vault — mindx_backend_service/vault_bankon/ │
                    │                                             │
                    │   .salt      (32 bytes, never rotated)      │
                    │   .master.key  ──┐  (machine custody today) │
                    │                  │                          │
                    │   entries.json ──┴── AES-256-GCM ciphertext │
                    │                       per-entry HKDF key    │
                    │                       info = bankon-entry:  │
                    │                              <id>:<context> │
                    └─────────────────────────────────────────────┘
                                       │
                            unlock                lock()
                                       │            │
                                       ▼            ▲
                              ┌───────────────────────┐
                              │  in-process: only the │
                              │  decrypted entries    │
                              │  the caller asked for │
                              └───────────────────────┘
```

- **One file**, `entries.json`, holds every credential as AES-256-GCM ciphertext.
- **One root key**, `.master.key` (machine custody) or your wallet signature
  (human custody), unlocks the vault.
- **Per-entry HKDF**: each entry has its *own* derived AES key. The HKDF info
  string is `bankon-entry:<entry_id>:<context>` — `context` is a real
  cryptographic namespace, not a label.
- **You only decrypt what you ask for**, via `retrieve(entry_id)` or
  `CredentialProvider.load_from_vault()`. The vault is then `lock()`ed.

---

## Use your vault — the 5 commands you'll actually run

All from the repo root, all with the project venv.

```bash
# 1. What's in the vault? (metadata only, no secrets)
.mindx_env/bin/python manage_credentials.py list

# 2. What providers does the vault know how to map to env vars at startup?
.mindx_env/bin/python manage_credentials.py providers

# 3. Store a credential — env-mapped (loaded into os.environ at backend start)
.mindx_env/bin/python manage_credentials.py store gemini_api_key 'AIzaSy...'

# 4. Store a credential — isolated participant namespace (NOT env-mapped;
#    only retrievable on demand by code that knows the entry_id + context)
.mindx_env/bin/python manage_credentials.py store wordpress.agent:wp_app_password \
    'xxxx xxxx xxxx xxxx xxxx xxxx' --context wordpress.agent.keys

# 5. Delete one
.mindx_env/bin/python manage_credentials.py delete openrouter_api_key
```

That's the day-to-day surface. Every other operation is one of: provisioning a
participant ([§Add a new participant](#add-a-new-participant)), becoming
shadow-overlord ([§below](#become-shadow-overlord-admin-tier--5-minutes)),
or taking custody of the vault
([§Human Overseer](#take-vault-custody-airgap-ceremony--15-minutes)).

---

## Become shadow-overlord (admin tier — 5 minutes)

Shadow-overlord is the **operator wallet** that signs requests for the
privileged HTTP routes (`/admin/cabinet/*`, `/admin/shadow/*`, `/vault/sign/*`,
`/publish/rage/authorize`, etc.). It is **not** the wallet that unlocks the
vault — that's [Human Overseer](#take-vault-custody-airgap-ceremony--15-minutes)
below. They *can* be the same wallet; you get to choose.

Everything here is just env config. No airgap, no key rotation.

### 1. Make a wallet — never exposed to this server

Use whatever you trust: MetaMask, hardware wallet, foundry's `cast wallet new`,
etc. Write down the seed phrase **offline**. You'll need the **address** here
and the **private key** only when signing challenges later.

### 2. Store the 3 values in the BANKON vault (canonical path)

All three are in `PROVIDER_ENV_MAP` (see `credential_provider.py`), so the vault
decrypts them into `os.environ` at backend startup. **Nothing in plain `.env`**:

```bash
SECRET=$(openssl rand -hex 32)   # 64 hex chars; fresh, per-environment

.mindx_env/bin/python manage_credentials.py store shadow_overlord_address '0xYourPublicAddressHere'
.mindx_env/bin/python manage_credentials.py store shadow_jwt_secret "$SECRET"
.mindx_env/bin/python manage_credentials.py store mindx_admin_addresses '0xYourPublicAddressHere'   # comma-separated for multiple
unset SECRET
```

`shadow_overlord_address` gates `/admin/shadow/*` + `/vault/sign/*`;
`mindx_admin_addresses` gates `/admin/*` + `/vault/credentials/{store,delete}`.
They almost always match. `shadow_jwt_secret` is the HMAC key for the 5-minute
JWTs the verify endpoint issues — must be ≥32 chars, and should be **different**
between dev and prod (compromise isolation).

Escape hatch — plain `.env` (if you can't reach the vault, e.g. fresh box):

```ini
SHADOW_OVERLORD_ADDRESS=0xYourPublicAddressHere
SHADOW_JWT_SECRET=<32+ random chars>
MINDX_SECURITY_ADMIN_ADDRESSES=0xYourPublicAddressHere
```

Env wins over vault when both are set (per the Config priority order documented
in `CLAUDE.md`), so `.env` is also the rotation override path.

### 3. Restart and verify

```bash
sudo systemctl restart mindx.service     # on the VPS
# or local:
./mindX.sh --frontend
```

Verify you can sign a challenge end-to-end:

```bash
# A. request a challenge for the "auth" scope
curl -s -X POST https://mindx.pythai.net/admin/shadow/challenge \
     -H 'Content-Type: application/json' -d '{"scope":"auth"}'
# → {"nonce":"0x…","message":"MINDX-SHADOW-OVERLORD scope=auth\nnonce: 0x…", ...}

# B. sign `message` with your wallet (MetaMask "personal_sign", or
#    `cast wallet sign --private-key 0x… "<message>"`, or airgap_sign.py)

# C. exchange for a 5-minute JWT
curl -s -X POST https://mindx.pythai.net/admin/shadow/verify \
     -H 'Content-Type: application/json' \
     -d '{"nonce":"0x…","signature":"0x…"}'
# → {"jwt":"eyJ…","exp":1715567890}
```

If the JWT comes back you are shadow-overlord. The much longer
[`docs/operations/SHADOW_OVERLORD_GUIDE.md`](operations/SHADOW_OVERLORD_GUIDE.md)
documents every route you can now reach.

### 3a. Or do the whole flow in the browser

The `/login` page also exposes a **Shadow-Overlord** card in the launcher grid;
clicking it sends you to the dedicated sign-in page. Once you complete the
sovereign sign-in there, returning to `/login` (or any other tab) shows the
**BANKON Vault**, **Cabinet**, and **Publish to Rage** tiles unlocked with a
golden ring — and the tier badge in the hero reads `SHADOW OVERLORD`.

`mindx_frontend_ui/shadow-overlord.html` is the browser version of the same
flow. Opens at:

- local:  http://localhost:3000/shadow-overlord
- prod:   https://mindx.pythai.net/shadow-overlord *(once the frontend route is
  reverse-proxied; see `mindx_frontend_ui/server.js:22`)*

What it does:
1. **EIP-6963 wallet detection** — picks up MetaMask, Phantom, Coinbase, etc.
   (Pattern lifted verbatim from `live/allchain.html` so it behaves like the
   agenticplace pages.)
2. **Connect Wallet** → reads your active account.
3. **Sign in as shadow-overlord** → calls `POST /admin/shadow/challenge` with
   `scope=auth`, hands the returned `message` to `personal_sign`, posts the
   resulting 65-byte signature to `POST /admin/shadow/verify`. The 5-minute
   HS256 JWT comes back and is held **only in JavaScript memory** — never
   `localStorage`, never a cookie. Re-auth = re-sign.
4. **Identity assertion is server-side.** If the recovered signer ≠ the
   configured `SHADOW_OVERLORD_ADDRESS` you get a red `403 not shadow-overlord:
   …your-wallet-short-hash…` banner — the negative path is real auth, not UI
   theatre.

The page has two visual states:

- **Idle / denied:** dim violet abyss (WebGL fragment shader extrapolated from
  `live/allchain.html` + `mindx.pythai.net/automindx`'s DeltaVerse perception
  layer — animated fbm-noise tendrils, mouse-parallax, slow ominous pulse).
- **Sovereign:** after a verified JWT arrives, `body.is-overlord` flips on, the
  shader's `u_state` uniform ramps to 1 (tendrils gain a golden crown ring,
  central eye opens, palette saturates), the `WELCOME, OVERLORD` banner
  appears, the logo glow brightens, and a "Sovereign — privileged routes
  unlocked" panel lists the admin routes you can now reach
  (`/admin/cabinet/*`, `/vault/sign/*`, `/admin/shadow/release-key/*`,
  `/admin/vault/credentials/*`, `/admin/publish-to-rage`).

Logout clears the JWT from memory, drops `is-overlord`, and ramps the shader
back. Closing the tab also clears everything (in-memory only).

---

## Take vault custody (airgap ceremony — 15 minutes)

This is the bigger upgrade: **delete `.master.key` from the server and replace
it with your wallet signature** as the unlock secret. After this, root on the
box can read the ciphertext but cannot decrypt it without you signing a
challenge.

It is fully scripted by `manage_custody.py` (connected machine) +
`scripts/vault/airgap_sign.py` (airgapped machine). The ceremony is
**atomic-or-rollback** with a two-phase commit.

Pre-flight (on the VPS):

```bash
cd /home/mindx/mindX
.mindx_env/bin/python manage_custody.py preflight
```

You should see `.master.key: exists=True`, `sentinel .human_overseer_active:
False`, `.overseer_proof.json: False`. If `.overseer_proof.json` already
exists, you're already in human custody — skip to recovery below.

### 1. Issue the challenge (connected)

```bash
.mindx_env/bin/python manage_custody.py challenge --address 0xYourOverseerAddress
# writes ./handoff_challenge.txt
```

The challenge text includes the vault salt fingerprint and the address it
commits to. Read it before signing it.

### 2. Sign on the airgap

Move `handoff_challenge.txt` to an airgapped machine (USB / QR / paper).
There, with the seed/key that never touched the connected box:

```bash
python scripts/vault/airgap_sign.py \
    --challenge-file handoff_challenge.txt \
    --out handoff_sig.json \
    --privkey-prompt              # or --keystore PATH, --mnemonic, --ledger, etc.
# writes {address, signature, message}
```

`airgap_sign.py` has no dependency on mindX — it's a single Python file with
only `eth_account`. Move `handoff_sig.json` back to the connected machine.

### 3. Dry-run (connected — non-destructive)

```bash
export MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1
.mindx_env/bin/python manage_custody.py dry-run \
    --address 0xYourOverseerAddress \
    --signature 0x<130-hex-chars>
```

This re-encrypts every entry under the new key into `entries.json.candidate`,
verifies every plaintext SHA round-trips, and writes `.rotation.ok` with a
freshness mark. **`.master.key` is still there.** The vault has not changed
yet.

### 4. Commit (connected — atomic swap)

Within 5 minutes of the dry-run:

```bash
.mindx_env/bin/python manage_custody.py commit \
    --address 0xYourOverseerAddress \
    --signature 0x<same-signature> \
    --i-am-sure
```

What happens, in order, atomically:
1. `os.replace(entries.json.candidate, entries.json)` — re-encrypted entries are now live.
2. `.overseer_proof.json` is written (the persisted signature, so the service can
   re-unlock on restart without you re-signing).
3. `.human_overseer_active` sentinel is written.
4. `.master.key` is overwritten with zeros, then deleted, then `fsync`'d.
5. One row appended to `data/governance/overseer_history.jsonl`.

You are now Human Overseer. `manage_credentials.py list` should still work
(the service re-unlocks transparently via the proof file).

### 5. Verify

```bash
.mindx_env/bin/python manage_custody.py smoke-test --base-url http://localhost:8000
ls -la mindx_backend_service/vault_bankon/        # .master.key should be GONE
                                                   # .human_overseer_active should EXIST
                                                   # .overseer_proof.json should EXIST
cat data/governance/overseer_history.jsonl        # one row
```

---

## Participant isolation — how it works today

This is the answer to *"is wordpress.agent's WP API key isolated from
gemini_api_key, isolated from the cabinet wallets?"*

| Layer | Mechanism | What it gives you |
|---|---|---|
| Per-entry cryptographic isolation | HKDF info = `bankon-entry:<entry_id>:<context>`. Each entry has its own AES key. | Compromising one entry's derived key does **not** disclose any other entry. |
| Namespace-level isolation | `context=` is part of the HKDF info string. Entries sharing a context are domain-separated as a group from entries in any other context. | Listing entries in your own namespace is fine; deriving someone else's key requires both their entry_id *and* their context as an unguessed string. |
| Process-level isolation | Filesystem permissions on `.master.key` (mode 0400, owner `mindx`). After Human Overseer takeover, the master key is your wallet signature. | Only processes running as the vault owner can unlock. Cross-agent isolation today relies on **all participants running as `mindx`** — which means cryptographic separation, not process separation. |

### Known participant namespaces

| Context | Holder | Entry ids (examples) | Loaded into env at startup? |
|---|---|---|---|
| `provider` | LLM provider keys, RPC URLs, treasury PK, allowlists — see `PROVIDER_ENV_MAP` in `credential_provider.py` | `gemini_api_key`, `openai_api_key`, `memory_anchor_treasury_pk`, `wordpress_publisher_addresses` | **yes** |
| `cabinet_provision` / `cabinet_public` | Executive cabinet wallets (8/company) | `company:<co>:cabinet:<role>:pk`, `…:address` | no — signed on demand via `/vault/sign/{agent_id}` |
| `wordpress.agent.keys` | wordpress.agent's wallet + WP API key | `wordpress.agent:pk`, `wordpress.agent:address`, `wordpress.agent:wp_app_password`, `wordpress.agent:wp_base_url`, `wordpress.agent:wp_user` | no — read on demand by the wordpress-agent service per /publish |
| `default` | fallback if no context supplied | — | — |

The rule going forward: **anything not in `PROVIDER_ENV_MAP` lives in a named
participant namespace** (`<participant>.keys`) and is decrypted on demand. Only
provider-style env-mapped secrets get `context="provider"`.

### Add a new participant

1. Pick a namespace name: `<participant>.keys` (lower-case, dot-suffixed).
2. Store its entries with `--context <namespace>`:
   ```bash
   .mindx_env/bin/python manage_credentials.py store myagent:api_key 'sk-...' \
       --context myagent.keys
   .mindx_env/bin/python manage_credentials.py store myagent:pk '0x...' \
       --context myagent.keys
   ```
3. The participant's loader code does
   ```python
   from mindx_backend_service.bankon_vault.vault import BankonVault
   v = BankonVault(); v.unlock_with_key_file()
   try:
       api_key = v.retrieve("myagent:api_key")
       pk = v.retrieve("myagent:pk")
   finally:
       v.lock()
   ```
   For agents that also need to sign things, the existing `/vault/sign/<agent_id>`
   oracle works for any `<agent_id>:pk` entry (shadow-JWT gated).

For a fuller worked example see
[`docs/WORDPRESS_PUBLISHING.md`](WORDPRESS_PUBLISHING.md) and
`agents/wordpress_agent/vault_creds.py` — the canonical pattern for a participant
that holds both an API key and a wallet key in one isolated namespace.

---

## Restart / recovery

| Situation | What to do |
|---|---|
| Service restarted, machine custody | Nothing — `CredentialProvider.load_from_vault()` runs at startup, reads `.master.key`, populates env, locks. |
| Service restarted, **human custody, proof file present** | Nothing — `agents/wordpress_agent/vault_creds.py` and (todo) `credential_provider.py` use `load_human_from_proof()` to re-unlock transparently. |
| Service restarted, human custody, **proof file missing** | `POST /vault/credentials/reunlock` (admin) with `{address, signature, message}` body, or SSH and re-issue a challenge + re-sign and write the proof. |
| You lost your overseer seed phrase | The vault is gone. Mitigate ahead of time: provision a **second** overseer address as a hot-spare via `rotate_overseer(HumanOverseer(spare))`. |
| `.rotation.ok` exists but commit hasn't run within 5 minutes | Re-run dry-run; the freshness mark expires. The candidate file is overwritten safely. |
| Pre-handoff backup snapshot of the disk exists | Wipe it. It contains the old `.master.key`. |

---

## Audit findings

What's protected, today:

- ✅ Entries are AES-256-GCM with random per-write 12-byte IVs. AAD binds
  ciphertext to its entry id (renaming = decrypt fails).
- ✅ Each entry has its own HKDF-derived key. Cross-entry compromise resistance.
- ✅ Each *context* is its own HKDF namespace. wordpress.agent's keys are
  cryptographically isolated from gemini_api_key and from the cabinet.
- ✅ `entries.json` mode 0600, `.master.key` mode 0400, `vault_dir` mode 0700.
- ✅ `list_entries()` returns metadata only — no plaintexts ever cross the API.
- ✅ Rotation is atomic-or-rollback with a two-phase commit, scratch-verify, and
  a 5-minute freshness window on `.rotation.ok`.

What's **not** protected today:

- ⚠️ **One root key unlocks everything.** Machine custody (`.master.key`) yields
  the master key, which yields every per-entry HKDF key. Cryptographic
  isolation is between entries, **not** between callers. The wordpress-agent
  service running as `User=mindx` shares the same unlock surface as everything
  else running as `mindx`. Mitigation now: keep all vault-using services under
  one well-audited user; treat `.master.key` like an SSH host key. Mitigation
  later: see "v3" below.
- ⚠️ **`list_entries()` is global to anyone who unlocked.** A process that
  unlocked the vault can enumerate all entry ids in every namespace (the
  per-entry AES keys it can't derive without the right `context`, but it knows
  the ids exist). Acceptable today because the only unlocker is mindX itself;
  worth filtering by context once we have per-participant subdirs.
- ⚠️ **`SHADOW_JWT_SECRET` is plain env, not vaulted.** Add it to
  `PROVIDER_ENV_MAP` (with `provider_id="shadow_jwt_secret"`) and vault-store
  it for consistency. Minor.
- ⚠️ **No backup story.** `entries.json` + `.salt` + `.master.key` (or
  `.overseer_proof.json` under human custody) is the entire vault. Lose any
  and the vault is unrecoverable. Mitigation: encrypted off-site backup of
  `entries.json` + `.salt` only — the proof file should never be backed up to
  a location an attacker might reach.

**v3 — "every participant in its own encrypted folder" (deferred design):**

Today `context=` is cryptographic isolation; v3 promotes it to physical
isolation. Each participant gets its own subdirectory with its own master key:

```
mindx_backend_service/vault_bankon/
├── entries.json   .salt   .master.key             ← provider/system credentials
└── participants/
    ├── wordpress.agent/
    │   entries.json   .salt   .master.key            ← only mindx (or wpagent) can read
    └── cabinet/
        └── pythai/
            entries.json   .salt   .master.key        ← only mindx (or cabinet user) can read
```

Caller passes a `participant=` to `BankonVault(...)` — opens the right subdir,
derives a *participant-specific* master key, and only sees the entries inside.
Different OS users can each be granted read access to their own subdir without
seeing the rest.

This is a real refactor (about a day's work — `vault.py:__init__` +
`store/retrieve/list_entries` + `manage_credentials.py --participant` +
migration tool). Not done yet. The current `context=` mechanism is the
operating-today equivalent and is good for everything except adversarial OS
users on the same box.

---

## Reference — files and what they do

- `mindx_backend_service/bankon_vault/vault.py` — core `BankonVault` class,
  `rotate_overseer` (the atomic ceremony's machinery).
- `mindx_backend_service/bankon_vault/overseer.py` —
  `MachineOverseer`/`HumanOverseer`/`DAIOOverseer`, `load_human_from_proof`.
- `mindx_backend_service/bankon_vault/credential_provider.py` — `PROVIDER_ENV_MAP`,
  `CredentialProvider.load_from_vault()`.
- `mindx_backend_service/bankon_vault/shadow_overlord.py` — challenge / nonce /
  JWT plumbing for the admin tier.
- `mindx_backend_service/bankon_vault/{routes,admin_routes,sign_routes}.py` — the
  HTTP surfaces.
- `manage_credentials.py` — the everyday CLI.
- `manage_custody.py` — connected-side CLI for the airgap handoff.
- `scripts/vault/airgap_sign.py` — single-file offline signer.
- `data/governance/overseer_history.jsonl` — append-only custody audit log.

Companion docs:

- [`docs/BANKON_VAULT.md`](BANKON_VAULT.md) — canonical reference (crypto stack,
  on-disk layout, route inventory).
- [`docs/operations/SHADOW_OVERLORD_GUIDE.md`](operations/SHADOW_OVERLORD_GUIDE.md)
  — full theory + every privileged route.
- [`docs/operations/SHADOW_OVERLORD_RUNBOOK.md`](operations/SHADOW_OVERLORD_RUNBOOK.md)
  — terse operator cheat-sheet.
- [`docs/LEGACY_VAULT_MIGRATION.md`](LEGACY_VAULT_MIGRATION.md) — retiring the
  old `vault_manager` + `encrypted_vault_manager` (audit-blocker for the
  handoff).
- [`docs/WORDPRESS_PUBLISHING.md`](WORDPRESS_PUBLISHING.md) — the worked example
  of an isolated participant namespace (`wordpress.agent.keys`).
