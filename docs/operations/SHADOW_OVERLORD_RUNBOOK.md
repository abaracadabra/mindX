# Shadow-Overlord Runbook — BANKON Vault Admin Tier

> One-page operator manual. The architectural plan is at
> [`/home/hacker/.claude/plans/splendid-wishing-hejlsberg.md`](../../.claude/plans/splendid-wishing-hejlsberg.md).

---

## What this is

The shadow-overlord is the **offline-held key** that authorizes privileged BANKON Vault operations:
provisioning a company's executive cabinet (CEO + 7 soldier wallets), signing on behalf of any of those agents
(vault-as-oracle), clearing a cabinet, or releasing a private key in plaintext.

The server stores **only the shadow-overlord's public address**. The private key lives in MetaMask, a hardware
wallet, or an airgap signing rig — and never touches the server. JWT theft alone cannot trigger any state change;
every privileged endpoint requires a *fresh* per-op ECDSA signature on top of the JWT.

---

## One-time server setup

1. Generate the shadow-overlord wallet on a clean device:
   ```bash
   cast wallet new            # foundry — prints address + key
   # OR a hardware wallet, OR `python scripts/vault/airgap_sign.py --new`
   ```
   Record the **address** (public). Back up the **seed phrase / private key** offline. Do not put the private key on the server.

2. Configure the server:
   ```bash
   export SHADOW_OVERLORD_ADDRESS=0x<your_public_addr>
   export SHADOW_JWT_SECRET=$(openssl rand -hex 32)
   ```
   Both belong in your systemd unit / `.env`. The address is public; the JWT secret is a server-only HMAC key —
   rotate quarterly.

   Optional dual-shadow continuity (recommended for production):
   ```
   SHADOW_OVERLORD_ADDRESS_PRIMARY=0x...
   SHADOW_OVERLORD_ADDRESS_BACKUP=0x...
   ```
   *(Note: dual-address support is a planned extension — currently only the single `SHADOW_OVERLORD_ADDRESS` is honored.)*

3. Restart the service. Confirm:
   ```bash
   curl -sX POST https://mindx.pythai.net/admin/shadow/challenge -d '{"scope":"auth"}' -H 'content-type: application/json'
   # → {"nonce":"0x…","message":"MINDX-SHADOW-OVERLORD scope=auth\nnonce: 0x…","expires_at":...}
   ```
   A 503 means `SHADOW_OVERLORD_ADDRESS` is missing.

---

## Each admin session

1. Open `https://mindx.pythai.net/cabinet`.
2. **Connect Wallet** → MetaMask (or hardware wallet via MetaMask).
3. **Authenticate as Shadow-Overlord** → MetaMask prompts you to sign the challenge text. Approve.
   The page now holds a 5-minute JWT in browser memory.
4. **Provision PYTHAI Cabinet** to mint the 8 wallets — sign a second challenge.
5. To **sign as an agent**: pick the agent in the drop-down, paste the message, click *Sign as Agent*,
   approve the third MetaMask prompt. The vault returns a valid signature without ever exposing the private key.
6. JWT auto-expires in 5 minutes; re-authenticate as needed.

---

## Hardware-wallet / airgap session

```bash
# 1. Get the challenge
curl -sX POST https://mindx.pythai.net/admin/shadow/challenge \
  -H 'content-type: application/json' -d '{"scope":"auth"}' > challenge.json

# 2. Sign offline (Ledger/Trezor or keystore)
python scripts/vault/airgap_sign.py \
    --challenge-text "$(jq -r .message challenge.json)" \
    --keystore ~/.airgap/shadow.json \
    --out shadow_sig.json
# Or: --paste-sig if signing via the hardware wallet's own UI

# 3. Submit the signature
curl -sX POST https://mindx.pythai.net/admin/shadow/verify \
  -H 'content-type: application/json' \
  -d "$(jq -nc --argjson c $(<challenge.json) --argjson s $(<shadow_sig.json) '{nonce:$c.nonce, signature:$s.signature}')"
# → {"jwt":"...","exp":...}
```

The same pattern applies to `cabinet.provision`, `vault.sign`, `cabinet.clear`, and `release.key` scopes — only
the challenge `scope` and `params` differ. See the endpoint table in the plan file or `cabinet.html` for the
exact parameters per scope.

---

## Endpoint cheat-sheet

| Action | Method + path | Scope | Extra body |
|---|---|---|---|
| Auth | `POST /admin/shadow/{challenge,verify}` | `auth` | — |
| Preflight cabinet | `GET /admin/cabinet/{co}/preflight` | (JWT only) | — |
| Provision cabinet | `POST /admin/cabinet/{co}/provision` | `cabinet.provision` | `params={company:CO}` |
| Clear cabinet | `POST /admin/cabinet/{co}/clear` | `cabinet.clear` | `confirm: "DESTROY-{CO}-CABINET"` |
| Sign as agent | `POST /vault/sign/{agent_id:path}` | `vault.sign` | `params={agent_id, message_sha256}; message` |
| Release key (emergency) | `POST /admin/shadow/release-key/{agent_id:path}` | `release.key` | `confirm: "RELEASE-PRIVATE-KEY"` |
| Public read | `GET /cabinet/{co}` | (none) | — |

JWT: `Authorization: Bearer <jwt>`. Required for everything except the challenge/verify pair and the public read.

---

## Recovery scenarios

| Scenario | Recovery |
|---|---|
| **Shadow-overlord key lost** | No recovery via the lost key — by design. Operator changes `SHADOW_OVERLORD_ADDRESS` env + restarts; old cabinet ciphertext remains in the vault but is unreadable to the new shadow. Re-`provision` to mint a fresh cabinet. *Plan ahead*: keep an offline seed-phrase backup, or run dual-address mode (planned extension). |
| **JWT secret leaked** | Rotate `SHADOW_JWT_SECRET`, restart. All in-flight sessions invalidated; cabinet contents unaffected. |
| **Vault locked after restart** | Existing flow: `POST /vault/credentials/reunlock`. Flow A reads `.overseer_proof.json`; Flow B accepts a fresh `{address, signature, message}` body. |
| **Cabinet compromised (one agent's pk leaked)** | `POST /admin/cabinet/{co}/clear` (with `DESTROY-{CO}-CABINET` confirm) → re-provision. All 8 wallets get fresh keypairs; on-chain holdings on the old addresses must be migrated separately (out of this system's scope). |
| **Audit trail review** | All shadow-overlord ops emit `kind="admin.shadow_overlord_action"` catalogue events; query via `/insight/eval/...` or read `data/logs/catalogue_events.jsonl` directly. |

---

## Threat model summary

| Threat | Mitigation |
|---|---|
| Server reads vault on disk | `entries.json` is AES-256-GCM ciphertext; `.master.key` is deleted under HumanOverseer custody. Disk read alone yields no plaintext. |
| Stolen JWT | JWT alone authorizes only `/preflight` and read-only ops. Every state change requires a fresh ECDSA signature. JWT TTL = 5 min. JWT held only in JS memory. |
| Replay attacks | Each nonce is single-use, 120s TTL, server-canonical; `consume_signed_challenge` uses constant-time comparison and atomic mark-consumed. |
| Signing-oracle abuse (signing arbitrary payloads) | Only the human shadow-overlord can call `/vault/sign`. The challenge embeds `sha256(message)` — any payload tamper between challenge and submission causes a 400. |
| Stale shadow address (e.g. lost wallet) | Operator updates env + restart. Old shadow's signatures will fail verification. Cabinet contents survive (different KDF path). |

---

## Verification before shipping changes

```bash
cd /home/hacker/mindX
/home/hacker/mindX/.mindx_env/bin/python -m pytest tests/bankon_vault/test_shadow_overlord.py tests/bankon_vault/test_cabinet.py -c /dev/null -q
# 20 passed
```

The integration smoke also lives in the test_cabinet.py file — `test_sign_as_agent_returns_valid_sig_no_pk_leak`
is the cryptographic proof that the vault signs on the agent's behalf without leaking the private key.
