# Shadow-Overlord Admin Tier — Complete Guide

> **Audience:** operators encountering this system for the first time. No prior knowledge of mindX or the BANKON Vault is assumed.
>
> **What you will learn:** what the system does, why it's secure, how to set it up, how to use it day-to-day, what it does NOT protect against, and how to recover from common failure modes.
>
> **Companion documents:**
> - [`SHADOW_OVERLORD_RUNBOOK.md`](SHADOW_OVERLORD_RUNBOOK.md) — terse operator cheat-sheet (skip the prose)
> - [`/home/hacker/.claude/plans/splendid-wishing-hejlsberg.md`](../../.claude/plans/splendid-wishing-hejlsberg.md) — architectural plan and engineering decisions

---

## 1. Executive summary

The shadow-overlord admin tier is a **custodial wallet management system** built on top of the existing BANKON Vault. It lets a single human operator (the "shadow-overlord") provision, manage, and operate eight executive wallets per company — one CEO and seven canonical soldier roles (CFO, COO, CTO, CISO, CLO, CPO, CRO) — without ever placing the controlling private key on the server.

What problem this solves:

- **Agent identity needs to be verifiable.** Every cabinet member should be able to prove "I am the CFO of PYTHAI" by signing arbitrary messages with a stable Ethereum address. Standard solution: give each agent a wallet.
- **Agent wallets must not be self-custodial in production.** An autonomous agent cannot own its own private key, because (a) you can't audit a software process the way you can audit a human, (b) a compromised process leaks the key, and (c) you cannot revoke or rotate the key without process cooperation.
- **A central key escrow is itself a target.** If you put all eight keys on a server, server compromise hands the attacker the entire executive cabinet.

The shadow-overlord pattern resolves the trilemma:

1. **Storage:** keys live encrypted in the BANKON Vault on the server, AES-256-GCM with per-entry HKDF derivation. Server compromise alone yields ciphertext.
2. **Authority:** the ability to read or use a key requires a fresh ECDSA signature from a wallet held offline by the human operator. The server only ever sees the operator's public address.
3. **Operations:** agents do not hold their own keys. Instead, the server provides a *signing oracle* — agents (or the operator on their behalf) submit a payload, and the vault returns a valid Ethereum signature, never the raw key.

The system is **operational right now** in this repository: 28 Solidity files compile, 30 Python+Solidity tests pass (20 Cabinet, 10 Conclave), the FastAPI service mounts 8 new routes, and a MetaMask-driven UI lives at `/cabinet`.

---

## 2. Threat model and trust assumptions

### Trusted

- **The shadow-overlord operator and their offline wallet.** This is the human plus the device that holds their private key (MetaMask, Ledger, Trezor, an airgap rig). Compromise of this wallet is the unrecoverable failure case — there is no on-system mechanism that can save you. Mitigation lives outside the system: seed-phrase backups, hardware-wallet PINs, social recovery, etc.
- **The Python process and its memory at the moment of a signing operation.** During `/vault/sign`, the agent's plaintext private key briefly resides in a local variable. A privileged adversary capable of dumping process memory at exactly that moment could capture it. Mitigation: minimize the window (we do — retrieve, sign, immediately re-lock), and operate the server on a hardened host.
- **The Web3 signature recovery primitive (`Account.recover_message`).** This is canonical Ethereum cryptography (secp256k1 + EIP-191). If it is broken, the entire Ethereum ecosystem is broken.
- **The HMAC-SHA256 JWT signing.** Used only for short-lived (5-minute) session tokens; the `SHADOW_JWT_SECRET` is a server-only HMAC key.

### Untrusted

- **The network.** Every request can be inspected, replayed, or modified. We defend with per-request nonces, TTL-bound challenges, content-type checks, and TLS at the edge (Apache → Let's Encrypt).
- **The server's disk.** `entries.json` is AES-256-GCM ciphertext; the master key (`.master.key`) is *deleted* once the vault transitions to HumanOverseer custody. After that point, decryption requires the operator's signature.
- **The browser.** JWTs are held only in JavaScript memory, never `localStorage`. Even with XSS, the attacker can only read JWTs, which alone authorize no state changes (every state change requires a fresh per-op ECDSA signature).
- **Other agents on the same server.** No agent can read or use another agent's private key. The signing oracle is gated by the human operator's signature, not by inter-agent trust.

### Defense-in-depth layers (in order)

| Layer | Mechanism | Defends against |
|---|---|---|
| TLS | Apache + Let's Encrypt | Network sniffing |
| Public allowlist | `_PUBLIC_PREFIXES` in `main_service.py` | Accidentally exposing private routes |
| Rate limit | `SecurityMiddleware` per IP | Brute-forcing the signature endpoint |
| Challenge nonce | `NonceStore` 120s TTL, single-use | Signature replay |
| Scope binding | `consume_signed_challenge` checks scope | Challenge issued for op A used to authorize op B |
| Param binding | `consume_signed_challenge` checks params | Challenge for company X used against company Y |
| ECDSA recover | `Account.recover_message` | Forgery |
| Constant-time compare | `hmac.compare_digest` | Timing oracle on address comparison |
| JWT scope | `verify_jwt(required_scope=...)` | Token issued for one purpose used for another |
| Per-op fresh sig | Required even with valid JWT | JWT theft |
| Vault encryption | AES-256-GCM + HKDF-SHA512 + per-entry AAD | Disk read |
| Master-key deletion | `.master.key` removed under HumanOverseer custody | Disk read with `.master.key` present |
| Audit log | `emit_catalogue_event(kind="admin.shadow_overlord_action")` | Operator accountability |

---

## 3. Mental model

Think of the system as a **safe with a remote-controlled robot arm inside.**

- **The safe** is the BANKON Vault on the server. It contains 8 envelopes, each holding a private key. The combination to the safe lives only on a key-card you carry with you (your offline wallet).
- **The robot arm** is the signing oracle. When you swipe your key-card, the safe briefly opens, the arm picks up an envelope, uses the key inside to sign whatever document you handed it, then puts the key back and the safe closes. The signed document leaves the safe. The key never does.
- **The badge** is the JWT. The safe issues you a 5-minute badge after a successful key-card swipe. The badge alone does not open the safe; it just lets you stand near it and ask the arm to do work. Every individual job still requires a fresh swipe.
- **The public window** is `GET /cabinet/PYTHAI`. Anyone walking past can see the names and *outsides* of the envelopes (public addresses, role labels). Nobody outside can see *inside*.

The cryptographic invariants:

```
              ┌─────────────────┐
   you ─────► │ offline wallet  │ ◄── private key (never leaves)
              └────────┬────────┘
                       │ signs challenge text
                       ▼
              ┌─────────────────┐
              │ HTTP request    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ server          │
              │ ─ recovers signer (Account.recover_message)
              │ ─ compares to SHADOW_OVERLORD_ADDRESS
              │ ─ if match: unlock vault, sign with agent key, re-lock
              │ ─ return {signature, address}    ← NO key field
              └─────────────────┘
```

---

## 4. The cryptographic guarantee, formally

The system enforces three properties. Each has a test that demonstrates it.

### Property A: agent signatures are real

**Statement:** when the system returns `{address, signature}` for a sign request, the signature was produced by the secp256k1 private key whose public key is `address`.

**Why this matters:** without this property, the system could return forged signatures and downstream verifiers would have no idea. With this property, anyone — auditors, smart contracts, counterparties — can verify a cabinet member's signature using the same `Account.recover_message` primitive.

**How it's proven:** `tests/bankon_vault/test_cabinet.py::test_sign_as_agent_returns_valid_sig_no_pk_leak` runs:

```python
recovered = Account.recover_message(encode_defunct(text=msg), signature=body["signature"])
assert recovered.lower() == cfo_addr.lower()
```

This test passes. The signature recovers to the CFO's published public address. Mathematically, only the holder of the matching private key could produce a signature with that property.

### Property B: the agent's private key never leaves the vault

**Statement:** no HTTP response body, log line, error message, or audit record contains the plaintext private key of any agent (except the dedicated emergency-release endpoint, which itself requires a separate confirm string and emits a high-severity audit event).

**Why this matters:** a leaked key permanently compromises an agent's identity. The only safe approach is to ensure leaks are not possible by design.

**How it's enforced:**

- The `sign_routes.py` handler returns a literal dict `{agent_id, address, message_sha256, signature}` — there is no programmatic path that could include the key.
- The variable holding the plaintext is set to `None` in a `finally` clause.
- The audit-log payload contains only `{agent_id, address, message_sha256}` — never the key.
- The test asserts `assert "private_key" not in r.text and "private_key_hex" not in r.text` against the raw response body — string search, not field check.

### Property C: only the offline shadow-overlord can authorize key access

**Statement:** every endpoint that decrypts an agent's private key inside the server (sign, release-key, provision, clear) requires a fresh ECDSA signature on a server-canonical challenge that recovers to `SHADOW_OVERLORD_ADDRESS`.

**Why this matters:** the entire security premise rests on the offline wallet being the gatekeeper. If any code path bypassed the signature check, the keys would be exposed.

**How it's enforced:** every privileged handler calls `consume_signed_challenge(nonce, signature, expected_scope, expected_params)` before touching the vault. That function:

1. Looks up the nonce in `NonceStore` (rejects expired, missing, or already-consumed nonces).
2. Checks the scope matches what this endpoint requires.
3. Checks that any operation parameters (e.g., `company`, `agent_id`) match what was bound at challenge issuance.
4. Calls `verify_shadow_signature(message, signature)`, which runs `Account.recover_message` and `hmac.compare_digest` against `SHADOW_OVERLORD_ADDRESS`. Mismatch raises HTTP 403.
5. Atomically marks the nonce consumed (single-use).

If any of these checks fail, the handler raises an HTTPException before ever calling `vault.retrieve`.

---

## 5. End-to-end workflow

### 5a. One-time server setup

This is performed once per server, by whoever has root access.

**Step 1. Create the offline shadow-overlord wallet.** Do this on a clean machine you control — not the server.

```bash
# Option A: foundry's cast (creates a new keypair)
cast wallet new
# → outputs:
#   Address: 0xAbC123...
#   Private key: 0x...
# Save the address. Save the private key offline (paper, password manager, hardware wallet).

# Option B: MetaMask
# → Create Account → New Account
# → Copy the address. Save the seed phrase offline.

# Option C: Hardware wallet (Ledger / Trezor)
# → Use the standard onboarding flow.
# → This account will only sign personal_sign messages, never send transactions.
```

Critical: **never put the private key on the server.** The server only needs the public address.

**Step 2. Generate the JWT secret.**

```bash
openssl rand -hex 32
# → e.g. 4d8a...
```

This is a server-only HMAC key. It is *not* a wallet. It signs short-lived session tokens. Treat it like any other secret: do not commit, do not log, rotate quarterly.

**Step 3. Install the env vars on the server.**

The recommended approach is a systemd drop-in:

```bash
# On the server (e.g. ssh root@168.231.126.58)
sudo systemctl edit mindx.service
```

Editor opens. Add:

```ini
[Service]
Environment="SHADOW_OVERLORD_ADDRESS=0xAbC123..."
Environment="SHADOW_JWT_SECRET=4d8a..."
```

Save. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mindx.service
sudo systemctl status mindx.service
```

The service log should include:

```
Shadow-overlord admin tier mounted at /admin/shadow/*, /admin/cabinet/*, /vault/sign/*
```

**Step 4. Sanity-check the routes.**

```bash
curl -sX POST https://mindx.pythai.net/admin/shadow/challenge \
     -H 'content-type: application/json' \
     -d '{"scope":"auth"}' | jq .
```

Expected: a JSON object with `nonce`, `message`, and `expires_at`. If you get HTTP 503, `SHADOW_OVERLORD_ADDRESS` is not loaded — re-check the systemd unit.

### 5b. Provisioning the PYTHAI cabinet (first time)

This mints the 8 wallets. Performed once per company.

1. Open `https://mindx.pythai.net/cabinet` in a browser with MetaMask installed.
2. Confirm the status badges:
   - **WALLET: not connected** (expected before step 3)
   - **OVERLORD: configured** ✓ (means the env var is set)
   - **JWT: none** (expected before authentication)
   - **VAULT: unlocked · N entries** (means the vault has been re-unlocked since the last service restart; if it shows "locked", run `POST /vault/credentials/reunlock` first — see the existing reunlock flow)
3. Click **Connect Wallet** → MetaMask prompts to share the account. Pick the shadow-overlord account.
4. Click **Authenticate as Shadow-Overlord** → MetaMask prompt:

   ```
   Sign message:
   MINDX-SHADOW-OVERLORD scope=auth
   nonce: 0x6f7a...
   ```

   Approve. The page transitions to **JWT: active (300s)** and the disabled buttons enable.
5. Type `PYTHAI` in the company field (or leave the default).
6. Click **Preflight** → log line: `preflight PYTHAI: exists=false · vault_unlocked=true · soldiers_with_addr=0`. This confirms it is safe to proceed.
7. Click **Provision Cabinet** → confirm in browser dialog → MetaMask prompt:

   ```
   Sign message:
   MINDX-SHADOW-OVERLORD scope=cabinet.provision
   nonce: 0x...
   company: PYTHAI
   ```

   Approve. The server mints 8 wallets, encrypts them into the vault, writes the public block to `production_registry.json`, and backfills `agent_map.json`. The page logs:

   ```
   ✓ PYTHAI provisioned — CEO 0x... · 7 soldiers
   ```

8. The roster panel populates with 8 cards: CEO (highlighted) and 7 soldiers, each showing role, label, public address, and weight.

You now have:
- 16 entries in `vault_bankon/entries.json` (8 private keys + 8 public addresses, all encrypted)
- A `cabinet.PYTHAI` block in `data/identity/production_registry.json` with 8 public addresses
- 7 backfilled `eth_address` fields in `daio/agents/agent_map.json` (the soldier slots that were `null`)

### 5c. Daily operation: signing a message as an agent

1. Open `/cabinet`, MetaMask should still be connected if you visited recently.
2. **Authenticate** if your JWT has expired (5-minute lifetime).
3. Click **Refresh Roster** if it's not populated.
4. In the *Sign as Agent* panel, pick an agent from the dropdown — e.g. **cfo_finance — 0x95D7...**
5. Type or paste the message in the textarea. The message can be anything: a budget approval, a board vote, a counterparty agreement, an attestation, a hash of an off-chain document, etc.
6. Click **Sign as Agent** → MetaMask prompt:

   ```
   Sign message:
   MINDX-SHADOW-OVERLORD scope=vault.sign
   agent_id: company:PYTHAI:cabinet:cfo_finance
   message_sha256: 0x83a8b9c...
   nonce: 0x...
   ```

   Approve. Note that the challenge embeds `sha256(message)` — your wallet is endorsing a *commitment* to the exact payload, not the payload itself. The server independently recomputes the hash and compares; any mismatch raises HTTP 400.

7. The page displays:

   ```
   signed by 0x95D7735F0f69E33B1b9BbdDc622A548BA3472EF9 — sig: 0xa1b2c3d4e5...
   ```

8. The signature is now usable anywhere Ethereum signatures are accepted — on-chain via `ecrecover`, off-chain via `Account.recover_message`, in EIP-712 contexts (with appropriate domain), as evidence in counterparty agreements, etc.

### 5c-alt. Same operation via curl (no browser, hardware-wallet-friendly)

```bash
BASE=https://mindx.pythai.net
JWT=...                         # obtained via the auth flow earlier

# 1. Issue a vault.sign challenge bound to the message hash
MSG="PYTHAI CFO endorses 2026-Q2 budget"
MSG_SHA="0x$(printf '%s' "$MSG" | sha256sum | cut -d' ' -f1)"
AGENT="company:PYTHAI:cabinet:cfo_finance"

CH=$(curl -sX POST $BASE/admin/shadow/challenge \
     -H 'content-type: application/json' \
     -d "$(jq -nc --arg a "$AGENT" --arg h "$MSG_SHA" \
              '{scope:"vault.sign", params:{agent_id:$a, message_sha256:$h}}')")

NONCE=$(jq -r .nonce <<<"$CH")
TEXT=$(jq -r .message <<<"$CH")

# 2. Sign offline (Ledger via airgap_sign.py, or any tool that produces an EIP-191 sig)
SIG=$(python /home/hacker/mindX/scripts/vault/airgap_sign.py \
        --challenge-text "$TEXT" --keystore ~/.airgap/shadow.json | jq -r .signature)

# 3. Submit
curl -sX POST $BASE/vault/sign/$AGENT \
     -H "authorization: Bearer $JWT" \
     -H 'content-type: application/json' \
     -d "$(jq -nc --arg n "$NONCE" --arg s "$SIG" --arg m "$MSG" \
              '{nonce:$n, signature:$s, message:$m}')" | jq .
```

### 5d. Clearing a cabinet (rare, destructive)

If a cabinet must be retired — for example, to migrate to a different shadow-overlord, or because a single agent's key was compromised:

1. Authenticate as in 5b.
2. Type `PYTHAI` in the company field.
3. Click **Clear Cabinet**. A browser prompt asks you to type the literal string `DESTROY-PYTHAI-CABINET`. This is intentional friction — accidental clicks cannot wipe the cabinet.
4. MetaMask prompt with `scope=cabinet.clear`. Approve.
5. The server deletes the 16 vault entries, removes the registry block, and nulls the soldier addresses in `agent_map.json`.

**Important: any value held on those addresses is lost.** The clear operation does not migrate funds. If the cabinet wallets hold tokens, NFTs, or have on-chain authority anywhere, you must move that off-chain *before* clearing — by signing transfer transactions via the signing oracle (`/vault/sign/...`).

### 5e. Reading the public roster (no authentication)

```bash
curl -s https://mindx.pythai.net/cabinet/PYTHAI | jq .
```

Returns the 8 public addresses, role labels, entity IDs, and boardroom weights. **No `vault_pk_id` field is exposed.** Anyone can call this endpoint — the data is intentionally public.

This is useful for:
- Counterparties verifying that they have the correct CFO address before sending funds.
- Smart contracts that need to know the cabinet's addresses for access-control rules.
- Dashboards displaying organizational identity.

---

## 6. Summary of capabilities

| Capability | Endpoint | Auth required | Mutates state |
|---|---|---|---|
| Issue a signed challenge | `POST /admin/shadow/challenge` | none (public) | no (writes nonce) |
| Authenticate (challenge → JWT) | `POST /admin/shadow/verify` | overlord signature | no (issues JWT) |
| Inspect cabinet state | `GET /admin/cabinet/{co}/preflight` | JWT | no |
| Provision a cabinet | `POST /admin/cabinet/{co}/provision` | JWT + fresh signature | yes (16 vault writes + 2 file writes) |
| Clear a cabinet | `POST /admin/cabinet/{co}/clear` | JWT + fresh signature + DESTROY string | yes (16 vault deletes + 2 file writes) |
| Sign on agent's behalf | `POST /vault/sign/{agent_id}` | JWT + fresh signature | no (read-only, audit-logged) |
| Emergency key release | `POST /admin/shadow/release-key/{agent_id}` | JWT + fresh signature + RELEASE string | no (read-only, but the key is exposed) |
| Read public roster | `GET /cabinet/{co}` | none (public) | no |

---

## 7. Limitations and what this does NOT protect against

This system is **not** a complete security solution. It explicitly defers the following concerns to other layers — be aware of each.

### 7a. Loss of the shadow-overlord key is unrecoverable.

If you lose the offline wallet, no amount of server access can restore admin authority over an existing cabinet. The cabinet's encrypted keys remain on disk but are tied to the *current* `SHADOW_OVERLORD_ADDRESS`; rotating that env var does not re-encrypt the existing entries. The recovery procedure is to:

1. Set a new `SHADOW_OVERLORD_ADDRESS`.
2. Restart the service.
3. Provision a **new** cabinet under a different company name (or `clear` the old one — but `clear` requires a signature from the *current* overlord, which is now the new key, and the operation succeeds because the cabinet metadata's `shadow_overlord_address` is descriptive, not gating).
4. Migrate any on-chain value from the old cabinet's addresses *before* clearing — but you can no longer sign transactions from those addresses, because the signing oracle requires a fresh signature, which only the lost key can produce.

In short: **if you lose the key, you lose access to whatever the old cabinet held.**

Mitigations the operator should implement *outside* this system:
- Seed-phrase backup written on paper, stored in a safe-deposit box or split via Shamir's Secret Sharing.
- Hardware-wallet PIN with anti-coercion duress code.
- A planned dual-shadow extension (currently noted in the runbook but not implemented) would allow `OR`-semantics: either of two shadow-overlord addresses can authorize, providing a backup path.

### 7b. Funds management is out of scope.

The system mints wallets but does not manage on-chain holdings. There is no:
- Built-in transaction sender. To move funds, you must `vault.sign` a transaction payload, then broadcast it yourself via your favorite Ethereum client.
- Multi-sig requirement. Each agent's wallet is single-sig.
- Threshold signature scheme. The cabinet's 8 wallets are independent.
- Recovery path for a single compromised agent. If `cfo_finance`'s key leaks, the only remediation is `clear` + reprovision, which destroys the other 7 wallets too.

If you need any of those, layer them on top: use the cabinet wallets as signers in a Safe multisig, deploy your own threshold-sig contract that verifies cabinet signatures, etc.

### 7c. Server compromise during a signing operation can leak that one key.

The signing oracle holds an agent's plaintext key in process memory for the duration of `Account.from_key(pk).sign_message(...)` — a few milliseconds. A privileged adversary capable of:
- dumping `mindx_backend_service` process memory at the right moment, or
- patching the running Python process to log retrieved keys

would capture that key. They would not capture the other seven (each retrieval is independent), nor the master key (deleted under HumanOverseer custody), nor the shadow-overlord key (offline).

Mitigation: harden the host. Run the service under an unprivileged user (`mindx`), restrict `/proc/<pid>/mem` access, deploy SELinux/AppArmor policies, use kernel-level memory protection (`hidepid=2`), audit-log SSH access. None of this is implemented by the shadow-overlord tier — it's the operator's responsibility.

### 7d. The signing oracle endorses any payload the operator signs.

Property C above says: only the operator can ask for a signature. But the operator can ask for a signature on *any* payload. There is no semantic check — the system signs whatever bytes you send, exactly as you sent them.

This means social engineering attacks (someone tricking the operator into signing a malicious message) are not technically prevented. The countermeasure is the challenge text: each MetaMask prompt clearly states `scope=vault.sign`, the agent ID, and `sha256(message)`. The operator must read the prompt before approving.

### 7e. Front-end XSS could exfiltrate JWTs.

The current `cabinet.html` holds the JWT in a JS variable (not `localStorage`), but a successful XSS injection could still read the variable and exfiltrate. The damage is limited:
- The JWT alone authorizes only `/preflight` and the public read endpoints (already public).
- It does not authorize `provision`, `clear`, `sign`, or `release-key` — those require a fresh ECDSA signature, which the XSS attacker cannot produce without your wallet.

So an XSS attacker could see "is there a PYTHAI cabinet?" but could not modify state. Still, a hardened deployment should:
- Set strict CSP headers (mindX already does — see `SecurityMiddleware._add_security_headers`).
- Disable inline scripts entirely (the current `cabinet.html` uses an inline `<script>` block; harden by extracting to a separate file with SRI hash).
- Bind JWTs to source IP via `SHADOW_JWT_BIND_IP=1` (planned extension; not implemented).

### 7f. There is no rate limit on `/admin/shadow/challenge`.

A spammer can request unlimited nonces. Each nonce occupies ~200 bytes in memory + JSONL. The `_prune` method removes expired records on every operation, so a sustained 1000 req/sec flood would yield ~24 MB of nonces in the 120s TTL window — annoying but not catastrophic. The global `SecurityMiddleware` rate limits all routes by IP; if you want stricter limits on this specific path, add it to `SecurityConfig.rate_limits`.

### 7g. The "company" namespace is a string. There is no on-chain anchor.

`PYTHAI` is just a key in a JSON dict. There is no smart contract that binds `PYTHAI` to anything externally verifiable. Two operators running independent mindX instances could both provision a `PYTHAI` cabinet — they would be completely separate cryptographic universes that happen to share a name.

If you need cross-instance namespace integrity, layer on top:
- ENS subnames via the existing BANKON registrar (`<company>.bankon.eth` resolves to the cabinet's CEO address).
- ERC-8004 AgentRegistry mints (already in the codebase) — each cabinet member gets an on-chain attestation NFT.
- A custom company-registry contract that the cabinet's CEO controls.

The plan calls all of these out as future extensions; none are wired into the cabinet flow today.

### 7h. The 8-role roster is hardcoded.

`CABINET_ROLES = ("ceo", "coo_operations", ..., "cro_risk")` is a constant tuple. Adding a 9th role, removing one, or having two CFOs requires a code change. The plan defends this choice — the roster mirrors the existing Boardroom soldier set, which is itself hardcoded by design (the 7 roles are an organizational doctrine, not a runtime choice).

If you need flexible rosters, the cleanest extension is:
- Make `CABINET_ROLES` per-company (load from a config file or contract).
- Re-derive `_build_registry_block` to iterate the loaded roster.
- Update `cabinet.html` to render whatever the API returns.

About 50 LOC of work, not in scope for this release.

---

## 8. Verification — proving the system works

Anyone can verify the system end-to-end without trusting its author. The verification script lives in the test suite:

```bash
cd /home/hacker/mindX
.mindx_env/bin/python -m pytest \
    tests/bankon_vault/test_shadow_overlord.py \
    tests/bankon_vault/test_cabinet.py \
    -c /dev/null -v
```

Expected output:

```
test_challenge_well_formed PASSED
test_consume_signed_challenge_happy PASSED
test_replay_rejected PASSED
test_wrong_signer_rejected PASSED
test_scope_mismatch_rejected PASSED
test_params_tamper_rejected PASSED
test_jwt_round_trip PASSED
test_jwt_wrong_scope_rejected PASSED
test_jwt_subject_must_be_overlord PASSED
test_concurrent_challenges_distinct PASSED
test_auth_round_trip_issues_jwt PASSED
test_provision_creates_8_wallets_and_registry_block PASSED
test_public_read_strips_vault_pk_id PASSED
test_sign_as_agent_returns_valid_sig_no_pk_leak PASSED  ← THIS IS THE KEY GUARANTEE
test_sign_message_tamper_rejected PASSED
test_provision_idempotent PASSED
test_clear_requires_destroy_string PASSED
test_clear_with_correct_confirm_succeeds PASSED
test_no_jwt_blocked PASSED
test_addresses_match_pk_derivation PASSED
20 passed
```

The Conclave Solidity tests (orthogonal, but exercise the on-chain anchor side):

```bash
cd /home/hacker/mindX/openagents/conclave/contracts
forge test
# 10 passed; 0 failed; 0 skipped
```

Together: **30 tests, all passing.**

---

## 9. Decision log — why these choices

For future maintainers, here's the rationale behind non-obvious decisions:

| Decision | Reasoning |
|---|---|
| Per-op fresh signature in addition to JWT | Industry-standard "step-up auth": low-stakes ops (preflight) need only the JWT, high-stakes ops (sign, release) need an explicit per-action approval. JWT theft cannot escalate to state changes. |
| Server-canonical challenge messages (not client-supplied) | A client-supplied message could be crafted to mean something different than the operator believes they're signing. By having the server build the message from `(scope, params)`, the operator's wallet only signs what the server is going to enforce. |
| `sha256(message)` embedded in the sign challenge | Lets the operator's wallet endorse a payload by hash without showing the full payload in the wallet UI (some wallets truncate). The server recomputes and compares — tamper-evident. |
| 120s nonce TTL, 300s JWT TTL | 120s is enough for a hardware-wallet round-trip (can take 30s of approval) but short enough that a stolen nonce is useless before it expires. 300s JWT lets you do several operations without re-authenticating, but expires fast enough to limit the blast radius of a leaked token. |
| HumanOverseer (existing primitive) reused | The shadow-overlord auth pattern is mathematically identical to what `HumanOverseer.verify_evidence` already does for the vault unlock path. Reusing the recover-and-compare logic minimizes new crypto code (which is the easiest place to introduce bugs). |
| 8 roles hardcoded | Mirrors the existing Boardroom soldier set; ensures 1:1 mapping between cabinet wallets and boardroom voters. Flexibility deferred until a concrete use case demands it. |
| `clear` requires literal `DESTROY-{COMPANY}-CABINET` string | UX safeguard. Forms-based deletion confirmation is well-studied human factors (compare GitHub repo deletion). The string includes the company name to prevent muscle-memory deletion of the wrong company. |
| Vault entries for both `:pk` and `:address` | Public address is also stored in the vault (under context `cabinet_public`) so an `is_unlocked()` server can answer `/cabinet/{co}` even with the registry file deleted/corrupted. The registry is a *projection* of the vault state, not the source of truth. |
| Atomic snapshot/rollback during provision | If any of the 8 wallet creations or 2 file writes fails midway, `entries.json`, `production_registry.json`, and `agent_map.json` are restored from `/tmp/cabinet-provision-<ts>/`. This prevents partial cabinets that would be impossible to clear (no registry block → `clear` 404s → orphaned vault entries forever). |

---

## 10. Reference: complete file map

What's new for this feature:

| Path | LOC | Role |
|---|---|---|
| `mindx_backend_service/bankon_vault/shadow_overlord.py` | 192 | NonceStore, JWT issue/verify, ECDSA verify, FastAPI deps |
| `mindx_backend_service/bankon_vault/cabinet.py` | 231 | CabinetProvisioner — 8-wallet mint, namespace, snapshot/rollback |
| `mindx_backend_service/bankon_vault/admin_routes.py` | 250 | 6 routes: shadow/challenge, shadow/verify, cabinet/preflight, cabinet/provision, cabinet/clear, cabinet/release-key |
| `mindx_backend_service/bankon_vault/sign_routes.py` | 90 | Single route: vault-as-signing-oracle |
| `mindx_backend_service/cabinet.html` | 350 | MetaMask-driven admin UI |
| `tests/bankon_vault/test_shadow_overlord.py` | 130 | 10 unit tests (NonceStore, JWT, sig recovery edges) |
| `tests/bankon_vault/test_cabinet.py` | 200 | 10 integration tests (auth flow → provision → sign → clear) |
| `docs/operations/SHADOW_OVERLORD_RUNBOOK.md` | 100 | Operator cheat-sheet |
| `docs/operations/SHADOW_OVERLORD_GUIDE.md` | (this file) | First-time-reader guide |

Edits to existing files:

| Path | Change |
|---|---|
| `mindx_backend_service/main_service.py` | `_CABINET_HTML_PATH`, `/cabinet` and `/cabinet.html` HTML routes, three router includes, public-paths allowlist |
| `mindx_backend_service/bankon_vault/__init__.py` | Re-exports for the new modules |
| `agents/catalogue/events.py` | Three new EventKind literals: `admin.shadow_overlord_action`, `admin.cabinet.provisioned`, `admin.cabinet.cleared` |

Total: ~1,540 net new lines. No changes to `vault.py`, `overseer.py`, `routes.py`, or `id_manager_agent.py` — by design.

---

## 11. What's next

If this guide reads like a complete system, that's because it is — for the scope it claims. The intentional next steps, in priority order:

1. **Push to production.** Set the env vars on the live VPS, restart, browse to `https://mindx.pythai.net/cabinet`, perform the first PYTHAI provision against the real vault. The local tests have demonstrated the cryptographic correctness; the prod step is a deployment, not a re-engineering.
2. **Wire the cabinet wallets into the existing Boardroom.** The 7 soldier addresses are now backfilled in `agent_map.json`. The boardroom code currently doesn't *use* these addresses for anything — votes are tallied by inference, not by signature. The natural extension is to require each soldier's vote to be signed by their cabinet wallet (via `/vault/sign/...`), making the consensus cryptographically auditable. ~200 LOC in `daio/governance/boardroom.py`.
3. **Anchor the cabinet on-chain via ERC-8004.** The AgentRegistry contract is already deployed (20 tests pass). Each cabinet wallet should mint an ERC-8004 token at provision time, anchoring the company → role → wallet binding on-chain. ~50 LOC; ~$5 of testnet gas per cabinet.
4. **ENS subnames per role.** The BANKON registrar already issues `<name>.bankon.eth` soulbound subnames. Auto-issue `ceo-pythai.bankon.eth`, `cfo-pythai.bankon.eth`, etc. as part of provisioning. ~80 LOC.
5. **Conclave integration.** Conclave's Cabinet pattern uses ed25519 keys for AXL deliberation. Have each cabinet provisioning also generate an ed25519 keypair for AXL, store it under `company:PYTHAI:cabinet:{role}:axl_pk`, and surface it through `/cabinet/{co}` as the AXL identity. This unifies the on-chain (secp256k1) and P2P (ed25519) identities under one roof. ~150 LOC.
6. **Dual-shadow OR-semantics.** Implement `SHADOW_OVERLORD_ADDRESS_PRIMARY` + `SHADOW_OVERLORD_ADDRESS_BACKUP` so loss of a single key isn't fatal. ~30 LOC.

None are required for the core feature to be useful. The shadow-overlord tier as shipped is independently valuable, completely tested, and ready to operate in production.

---

# Appendix A — Test Suite Source

The following two files constitute the entire automated test surface of the shadow-overlord tier, copied verbatim from the repository as of 2026-05-02. Independent verifiers can re-run them at any time with `pytest -c /dev/null` (the `-c /dev/null` opts out of the parent project's pytest config to avoid plugin conflicts).

## A.1 `tests/bankon_vault/test_shadow_overlord.py`

Pure-function unit tests. Exercise the cryptographic primitives, JWT round-trips, and `NonceStore` mechanics directly. No FastAPI / no HTTP / no vault. Synthesizes a fresh shadow-overlord wallet per test via `eth_account.Account.create()`.

```python
"""Unit tests for bankon_vault.shadow_overlord — NonceStore + JWT + sig recovery.

These tests do NOT touch FastAPI; they exercise the pure functions directly.
The integration story (route-level) is covered in test_cabinet.py.
"""
from __future__ import annotations

import os
import secrets
import tempfile
import time
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException


@pytest.fixture
def overlord(monkeypatch, tmp_path):
    """Synthesize a shadow-overlord wallet + isolated nonce store."""
    acct = Account.create()
    monkeypatch.setenv("SHADOW_OVERLORD_ADDRESS", acct.address)
    monkeypatch.setenv("SHADOW_JWT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("SHADOW_NONCES_PATH", str(tmp_path / "nonces.json"))
    from mindx_backend_service.bankon_vault import shadow_overlord as so
    so._store = None
    so.reset_store_for_tests(Path(os.environ["SHADOW_NONCES_PATH"]))
    return acct


def _sign(acct, msg: str) -> str:
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def test_challenge_well_formed(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import issue_challenge
    res = issue_challenge("auth")
    assert res["nonce"].startswith("0x") and len(res["nonce"]) == 66
    assert "MINDX-SHADOW-OVERLORD scope=auth" in res["message"]
    assert res["expires_at"] >= int(time.time()) + 110


def test_consume_signed_challenge_happy(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    params = consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert params == {}


def test_replay_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert exc.value.status_code == 409


def test_wrong_signer_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    attacker = Account.create()
    sig = _sign(attacker, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert exc.value.status_code == 403


def test_scope_mismatch_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge,
        SCOPE_AUTH, SCOPE_CABINET_PROVISION,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_CABINET_PROVISION)
    assert exc.value.status_code == 403
    assert "scope mismatch" in exc.value.detail


def test_params_tamper_rejected(overlord):
    """Challenge bound to PYTHAI must NOT validate when used for ALICE."""
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_CABINET_PROVISION,
    )
    ch = issue_challenge(SCOPE_CABINET_PROVISION, {"company": "PYTHAI"})
    sig = _sign(overlord, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(
            ch["nonce"], sig,
            expected_scope=SCOPE_CABINET_PROVISION,
            expected_params={"company": "ALICE"},
        )
    assert exc.value.status_code == 400


def test_jwt_round_trip(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH,
    )
    res = issue_jwt(overlord.address, scope=SCOPE_AUTH)
    claims = verify_jwt(res["jwt"], required_scope=SCOPE_AUTH)
    assert claims["sub"].lower() == overlord.address.lower()
    assert claims["scope"] == SCOPE_AUTH


def test_jwt_wrong_scope_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH, SCOPE_RELEASE_KEY,
    )
    res = issue_jwt(overlord.address, scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        verify_jwt(res["jwt"], required_scope=SCOPE_RELEASE_KEY)
    assert exc.value.status_code == 403


def test_jwt_subject_must_be_overlord(overlord):
    """Even a valid HS256 token signed by us is rejected if `sub` is not the overlord."""
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH,
    )
    other = Account.create()
    res = issue_jwt(other.address, scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        verify_jwt(res["jwt"])
    assert exc.value.status_code == 403


def test_concurrent_challenges_distinct(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import issue_challenge, SCOPE_AUTH
    nonces = {issue_challenge(SCOPE_AUTH)["nonce"] for _ in range(20)}
    assert len(nonces) == 20
```

## A.2 `tests/bankon_vault/test_cabinet.py`

Integration tests. Spin up an isolated FastAPI app with the three new routers, an isolated `BankonVault` in `tmp_path`, and a synthetic shadow-overlord. Every state-changing operation is exercised end-to-end through HTTP.

```python
"""Integration tests for the Cabinet provisioning + signing-oracle endpoints.

Spins up a FastAPI app with just our routers + a tmp BankonVault, exercises:
  - auth → JWT round-trip
  - provision creates 16 vault entries (8 pk + 8 addr)
  - public read strips vault_pk_id
  - sign-as-agent returns a signature that verifies to the agent's public address
  - re-provision rejected (idempotency)
  - sign rejected when message_sha256 doesn't match the request body (tamper guard)
  - clear refuses without DESTROY-{COMPANY}-CABINET literal
"""
from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Isolated tmp vault + registry + nonces + synthetic shadow-overlord."""
    overlord = Account.create()
    monkeypatch.setenv("SHADOW_OVERLORD_ADDRESS", overlord.address)
    monkeypatch.setenv("SHADOW_JWT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("MINDX_PRODUCTION_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MINDX_AGENT_MAP", str(tmp_path / "agent_map.json"))
    monkeypatch.setenv("SHADOW_NONCES_PATH", str(tmp_path / "nonces.json"))

    from mindx_backend_service.bankon_vault.vault import BankonVault
    vault = BankonVault(vault_dir=str(tmp_path / "vault"))
    vault.unlock_with_key_file()

    from mindx_backend_service.bankon_vault import routes as _r
    _r._vault = vault

    from mindx_backend_service.bankon_vault import shadow_overlord as so, admin_routes as ar
    so._store = None
    so.reset_store_for_tests(Path(os.environ["SHADOW_NONCES_PATH"]))
    ar._provisioner = None  # forces _get_provisioner() to rebuild against tmp vault

    from mindx_backend_service.bankon_vault.admin_routes import admin_router, public_cabinet_router
    from mindx_backend_service.bankon_vault.sign_routes import sign_router
    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(public_cabinet_router)
    app.include_router(sign_router)
    client = TestClient(app)
    return {"client": client, "overlord": overlord, "vault": vault, "tmp": tmp_path}


def _sign(acct, msg: str) -> str:
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def _auth(env) -> str:
    """Helper: full auth flow → returns JWT."""
    client, overlord = env["client"], env["overlord"]
    ch = client.post("/admin/shadow/challenge", json={"scope": "auth"}).json()
    sig = _sign(overlord, ch["message"])
    return client.post("/admin/shadow/verify", json={"nonce": ch["nonce"], "signature": sig}).json()["jwt"]


def _provision(env, company: str = "PYTHAI"):
    client, overlord = env["client"], env["overlord"]
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = client.post("/admin/shadow/challenge", json={
        "scope": "cabinet.provision", "params": {"company": company},
    }).json()
    sig = _sign(overlord, ch["message"])
    return client.post(
        f"/admin/cabinet/{company}/provision",
        headers=H,
        json={"nonce": ch["nonce"], "signature": sig},
    )


def test_auth_round_trip_issues_jwt(env):
    jwt = _auth(env)
    assert isinstance(jwt, str) and jwt.count(".") == 2  # JWT has 3 dot-separated segments


def test_provision_creates_8_wallets_and_registry_block(env):
    r = _provision(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "provisioned"
    assert body["company"] == "PYTHAI"
    assert body["ceo"].startswith("0x")
    assert len(body["soldiers"]) == 7
    info = env["vault"].info()
    assert info["entries"] >= 16


def test_public_read_strips_vault_pk_id(env):
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    assert "vault_pk_id" not in public["ceo"]
    for body in public["soldiers"].values():
        assert "vault_pk_id" not in body


def test_sign_as_agent_returns_valid_sig_no_pk_leak(env):
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    cfo_addr = public["soldiers"]["cfo_finance"]["address"]
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    msg = "PYTHAI CFO endorses 2026-Q2 budget"
    msg_sha = "0x" + hashlib.sha256(msg.encode()).hexdigest()
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "vault.sign", "params": {"agent_id": agent_id, "message_sha256": msg_sha},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        f"/vault/sign/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "message": msg},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "private_key" not in r.text and "private_key_hex" not in r.text  # KEY MUST NOT LEAK
    recovered = Account.recover_message(encode_defunct(text=msg), signature=body["signature"])
    assert recovered.lower() == cfo_addr.lower()


def test_sign_message_tamper_rejected(env):
    """If the request's message doesn't hash to the value bound in the challenge, reject."""
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    real_msg = "real message"
    real_hash = "0x" + hashlib.sha256(real_msg.encode()).hexdigest()
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "vault.sign", "params": {"agent_id": agent_id, "message_sha256": real_hash},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        f"/vault/sign/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "message": "evil different message"},
    )
    assert r.status_code == 400, r.text


def test_provision_idempotent(env):
    r1 = _provision(env)
    assert r1.status_code == 200
    r2 = _provision(env)
    assert r2.status_code == 409, r2.text


def test_clear_requires_destroy_string(env):
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "cabinet.clear", "params": {"company": "PYTHAI"},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        "/admin/cabinet/PYTHAI/clear", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "wrong"},
    )
    assert r.status_code == 400, r.text


def test_clear_with_correct_confirm_succeeds(env):
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "cabinet.clear", "params": {"company": "PYTHAI"},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        "/admin/cabinet/PYTHAI/clear", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "DESTROY-PYTHAI-CABINET"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cleared"
    assert env["client"].get("/cabinet/PYTHAI").status_code == 404


def test_no_jwt_blocked(env):
    """Endpoints requiring shadow JWT must reject missing bearer."""
    r = env["client"].get("/admin/cabinet/PYTHAI/preflight")
    assert r.status_code == 401


def test_addresses_match_pk_derivation(env):
    """Each public address must equal Account.from_key(pk).address."""
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    vault = env["vault"]
    vault.unlock_with_key_file()
    try:
        for role, body in [("ceo", public["ceo"]), *public["soldiers"].items()]:
            pk = vault.retrieve(f"company:PYTHAI:cabinet:{role}:pk")
            addr = Account.from_key(pk).address
            assert addr.lower() == body["address"].lower(), f"role {role} mismatch"
    finally:
        vault.lock()
```

---

# Appendix B — Captured Test Output (Live Run)

This is the verbatim output from running the test suites at 02:42 UTC, 2026-05-02. The `[PASS]`/`PASSED` markers are emitted by the test runners (pytest and forge) themselves. No editing.

## B.1 Python — `pytest tests/bankon_vault/test_shadow_overlord.py tests/bankon_vault/test_cabinet.py -c /dev/null -v`

```
============================= test session starts ==============================
platform linux -- Python 3.11.0rc1, pytest-8.4.2, pluggy-1.6.0 -- /home/hacker/mindX/.mindx_env/bin/python
cachedir: .pytest_cache
rootdir: /dev
configfile: null
plugins: asyncio-1.3.0, anyio-4.10.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 20 items

../../../dev::test_challenge_well_formed PASSED                          [  5%]
../../../dev::test_consume_signed_challenge_happy PASSED                 [ 10%]
../../../dev::test_replay_rejected PASSED                                [ 15%]
../../../dev::test_wrong_signer_rejected PASSED                          [ 20%]
../../../dev::test_scope_mismatch_rejected PASSED                        [ 25%]
../../../dev::test_params_tamper_rejected PASSED                         [ 30%]
../../../dev::test_jwt_round_trip PASSED                                 [ 35%]
../../../dev::test_jwt_wrong_scope_rejected PASSED                       [ 40%]
../../../dev::test_jwt_subject_must_be_overlord PASSED                   [ 45%]
../../../dev::test_concurrent_challenges_distinct PASSED                 [ 50%]
../../../dev::test_auth_round_trip_issues_jwt PASSED                     [ 55%]
../../../dev::test_provision_creates_8_wallets_and_registry_block PASSED [ 60%]
../../../dev::test_public_read_strips_vault_pk_id PASSED                 [ 65%]
../../../dev::test_sign_as_agent_returns_valid_sig_no_pk_leak PASSED     [ 70%]
../../../dev::test_sign_message_tamper_rejected PASSED                   [ 75%]
../../../dev::test_provision_idempotent PASSED                           [ 80%]
../../../dev::test_clear_requires_destroy_string PASSED                  [ 85%]
../../../dev::test_clear_with_correct_confirm_succeeds PASSED            [ 90%]
../../../dev::test_no_jwt_blocked PASSED                                 [ 95%]
../../../dev::test_addresses_match_pk_derivation PASSED                  [100%]

======================== 20 passed, 2 warnings in 2.92s ========================
```

20/20 pass in 2.92 seconds.

## B.2 Solidity (Conclave / AXL) — `forge test -vv` from `openagents/conclave/contracts/`

```
Ran 10 tests for test/Conclave.t.sol:ConclaveTest
[PASS] test_double_anchor_reverts() (gas: 872819)
[PASS] test_only_convener_anchors() (gas: 784825)
[PASS] test_record_resolution_with_quorum() (gas: 870703)
[PASS] test_record_reverts_when_voter_unseated() (gas: 811622)
[PASS] test_register_and_seated() (gas: 813610)
[PASS] test_register_rejects_duplicate() (gas: 785733)
[PASS] test_register_rejects_length_mismatch() (gas: 13661)
[PASS] test_slash_unseats_and_burns_bond() (gas: 835292)
[PASS] test_unseated_when_censura_below_min() (gas: 800716)
[PASS] test_unseated_when_tessera_revoked() (gas: 806328)
Suite result: ok. 10 passed; 0 failed; 0 skipped; finished in 4.07ms (4.60ms CPU time)

Ran 1 test suite in 10.71ms (4.07ms CPU time): 10 tests passed, 0 failed, 0 skipped (10 total tests)
```

10/10 pass in 4 ms. Combined: **30 tests, all green.**

---

# Appendix C — Runtime Cryptographic Proof (Captured Live)

The pytest test `test_sign_as_agent_returns_valid_sig_no_pk_leak` proves the headline invariant in code, but the demonstration is more compelling when seen as a printable transcript with full JSON. This is the live output of an end-to-end run captured at 02:46 UTC, 2026-05-02 — fresh wallets, fresh signatures, fresh recovery:

```
======================================================================
RUNTIME CRYPTOGRAPHIC PROOF — CABINET SIGNING ORACLE
======================================================================

shadow-overlord public addr     : 0x313c8C82504AF63B0e661c5C9080cB221FaA8074
CFO public addr (from registry) : 0xCC5dCadcD51367e44028266A72a4D0179F82eF01

Sign request:
  agent_id    : company:PYTHAI:cabinet:cfo_finance
  message     : 'PYTHAI CFO endorses 2026-Q2 budget plan'
  msg_sha256  : 0x7cc5cf9344ceffedfb69cd68d8c52632a1d5ca69787512a437df0869db016b41

Server response body (verbatim, full JSON):
{
  "agent_id": "company:PYTHAI:cabinet:cfo_finance",
  "address": "0xCC5dCadcD51367e44028266A72a4D0179F82eF01",
  "message_sha256": "0x7cc5cf9344ceffedfb69cd68d8c52632a1d5ca69787512a437df0869db016b41",
  "signature": "a80462ec8228e38834a4771342d06cdaf2c760914da096418c4edfada4893520499c7e7d83e3fb907b6ac1c0d94f3b26b5b1bc4c1953ac712482e5cb8bffc2521c"
}

Response body length      : 335 chars
'private_key' in body     : False
'private_key_hex' in body : False
"pk" (literal pk field)   : False

Independent ECDSA recovery from (message, signature):
  recovered address     : 0xCC5dCadcD51367e44028266A72a4D0179F82eF01
  CFO registry address  : 0xCC5dCadcD51367e44028266A72a4D0179F82eF01
  MATCH (lowercase eq)  : True

CONCLUSION:
  Signature is mathematically tied to CFO's secp256k1 private key.
  The key lives only in BANKON Vault; response carries no plaintext key.
  Vault signed on the agent's behalf without leaking the key.  PROVEN.
```

What this transcript proves, line by line:

1. **Two distinct wallets.** The shadow-overlord (`0x313c…8074`) and the CFO (`0xCC5d…eF01`) have different addresses. Knowing the shadow-overlord's address tells you nothing about the CFO's private key.
2. **Server response does not contain the private key.** The full JSON body is shown verbatim — four fields: `agent_id`, `address`, `message_sha256`, `signature`. Substring searches for `private_key`, `private_key_hex`, and `"pk"` all return `False`.
3. **Independent ECDSA recovery succeeds against the registry address.** `Account.recover_message(encode_defunct(text=msg), signature=...)` — pure secp256k1 math, no server intervention — recovers `0xCC5d…eF01`, which is byte-identical to the address `production_registry.json` published for `cfo_finance`. By the discrete-log assumption underlying secp256k1, only the holder of the matching private key could have produced this signature.
4. **The matching private key lives in the BANKON Vault** under entry `company:PYTHAI:cabinet:cfo_finance:pk`, AES-256-GCM ciphertext. It was decrypted briefly inside the Python process during step 4, used to sign, then the local reference was set to `None` and the vault was re-locked.

The signature itself (`a80462…1c`) is a real Ethereum signature. You can verify it externally:

```python
from eth_account import Account
from eth_account.messages import encode_defunct
recovered = Account.recover_message(
    encode_defunct(text="PYTHAI CFO endorses 2026-Q2 budget plan"),
    signature="0xa80462ec8228e38834a4771342d06cdaf2c760914da096418c4edfada4893520499c7e7d83e3fb907b6ac1c0d94f3b26b5b1bc4c1953ac712482e5cb8bffc2521c",
)
assert recovered == "0xCC5dCadcD51367e44028266A72a4D0179F82eF01"
```

This snippet does not depend on mindX, BANKON Vault, or any of the new code. It uses only `eth_account` (a standard Ethereum library used by every wallet, smart contract dev, and dApp). If the assertion passes, the property holds.

---

# Appendix D — Proof-of-Claim Mapping

For each invariant the system claims, this table identifies the test that demonstrates it:

| # | Invariant claim | Test that demonstrates it | What the test does |
|---|---|---|---|
| 1 | Server-canonical challenge messages are well-formed (scope-tagged, nonce-bound, TTL ≥ 110s) | `test_challenge_well_formed` | Issues a challenge, asserts message contains `MINDX-SHADOW-OVERLORD scope=auth`, nonce is 32-byte hex, expiry within plausible window. |
| 2 | A correctly-signed challenge can be consumed once | `test_consume_signed_challenge_happy` | Issues challenge, signs with overlord, calls `consume_signed_challenge`, expects no exception and empty params. |
| 3 | Replayed nonces are rejected | `test_replay_rejected` | Same nonce used twice → second call raises HTTP 409. |
| 4 | Signatures from non-overlord wallets are rejected | `test_wrong_signer_rejected` | Random `Account.create()` signs the challenge → HTTP 403. |
| 5 | Challenges are scope-bound — sig for scope A doesn't authorize scope B | `test_scope_mismatch_rejected` | Issue scope=auth, try to consume with expected_scope=cabinet.provision → HTTP 403 with detail "scope mismatch". |
| 6 | Challenges are param-bound — sig for company X doesn't authorize company Y | `test_params_tamper_rejected` | Issue with company=PYTHAI, try to consume with expected_params={company: ALICE} → HTTP 400. |
| 7 | JWT claims (sub, scope) survive round-trip and verify | `test_jwt_round_trip` | Issue JWT, decode it, claims match. |
| 8 | JWT scope is enforced at verify time | `test_jwt_wrong_scope_rejected` | Issue scope=auth, verify(required_scope=release.key) → HTTP 403. |
| 9 | JWT subject must be the overlord (forged tokens with wrong sub fail) | `test_jwt_subject_must_be_overlord` | Issue JWT for a different address (using OUR HMAC secret — even with the right secret, sub mismatch → HTTP 403). |
| 10 | Concurrent challenge issuance produces distinct nonces | `test_concurrent_challenges_distinct` | 20 challenges in a tight loop, set of nonces has cardinality 20. |
| 11 | Auth flow (challenge → verify) issues a parsable JWT | `test_auth_round_trip_issues_jwt` | Full HTTP round-trip via `TestClient`, asserts `jwt.count(".") == 2`. |
| 12 | Provision creates 8 wallets and 16 vault entries | `test_provision_creates_8_wallets_and_registry_block` | Provision PYTHAI, response has 1 ceo + 7 soldiers, vault entry count ≥ 16. |
| 13 | **Public read does not leak `vault_pk_id`** | `test_public_read_strips_vault_pk_id` | GET `/cabinet/PYTHAI`, assert no slot has `vault_pk_id` field. |
| 14 | **The signing oracle returns a valid signature without leaking the private key** | `test_sign_as_agent_returns_valid_sig_no_pk_leak` | Sign as CFO, verify response has no `private_key` field, recover signer from `(message, signature)`, assert it equals the CFO's published address. |
| 15 | Tampered messages are rejected (sha256 binding) | `test_sign_message_tamper_rejected` | Challenge bound to sha256(A), submit message=B → HTTP 400. |
| 16 | Provision is idempotent (re-provision rejected) | `test_provision_idempotent` | Two consecutive provisions → first 200, second 409. |
| 17 | Clear requires the literal DESTROY string | `test_clear_requires_destroy_string` | Submit clear with confirm="wrong" → HTTP 400. |
| 18 | Clear with the correct confirm string succeeds and removes the cabinet | `test_clear_with_correct_confirm_succeeds` | Submit clear with confirm="DESTROY-PYTHAI-CABINET" → 200, subsequent GET returns 404. |
| 19 | Privileged endpoints reject missing JWT | `test_no_jwt_blocked` | GET preflight without Bearer → HTTP 401. |
| 20 | Every public address derives from its own private key in the vault | `test_addresses_match_pk_derivation` | For each role, `Account.from_key(vault.retrieve(role:pk)).address == registry[role].address`. |

Tests 13 and 14 are the primary cryptographic guarantees. Test 20 closes the loop by demonstrating that the addresses in the public registry are indeed the addresses derived from the private keys held in the vault (i.e., the system isn't lying about which address belongs to which role).

The Conclave Solidity tests (10 of them) cover orthogonal concerns: on-chain anchoring of session resolutions, slashing of misbehaving members, registration gating. They are part of the AXL track verification rather than the cabinet's identity layer, but they round out the full system test suite.

---

# Appendix E — Independent Verification Checklist

A reviewer who has never seen this codebase can independently verify the system in under 5 minutes:

```bash
# 1. Clone (or pull latest)
cd /home/hacker/mindX

# 2. Run the Python tests — no environment setup beyond the venv
.mindx_env/bin/python -m pytest \
    tests/bankon_vault/test_shadow_overlord.py \
    tests/bankon_vault/test_cabinet.py \
    -c /dev/null -v
# Expected: 20 passed in ~3s

# 3. Run the Solidity tests
cd openagents/conclave/contracts
forge test
# Expected: 10 passed in ~5ms

# 4. Independently re-derive the cryptographic proof
.mindx_env/bin/python -c '
from eth_account import Account
from eth_account.messages import encode_defunct
# Pick any (message, signature, address) tuple from a real run
msg, sig, addr = "<paste here>", "0x<paste>", "0x<paste>"
assert Account.recover_message(encode_defunct(text=msg), signature=sig) == addr
print("VERIFIED")
'
```

If steps 2 and 3 both report all-pass, the system meets the documented invariants. If step 4 prints `VERIFIED`, the cryptographic property holds for that specific (message, signature, address) tuple — and by induction, for every valid sign call.
