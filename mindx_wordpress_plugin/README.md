# mindX Publish Auth

> *Wallet-signature authentication for autonomous publishing agents on WordPress.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Lets mindX (and any agent presenting a wallet signature) publish to a
WordPress install without ever putting a password — Application or
otherwise — on the wire. Replaces ad-hoc Application-Password handling
with a wallet signature flow that the agent already has by design.

## How it works

```
┌────────────────────┐                  ┌──────────────────────────┐
│ wordpress.agent    │                  │  rage.pythai.net (WP)    │
│ (mindX side)       │                  │  + mindX Publish Auth    │
└────────────────────┘                  └──────────────────────────┘
          │                                          │
          │   GET /wp-json/mindx/v1/auth/challenge   │
          │ ───────────────────────────────────────► │
          │                                          │   stores challenge
          │ ◄─────────────────────────────────────── │   in transient (5 min TTL)
          │   {challenge_id, message, expires_at}    │
          │                                          │
   sign(message)                                     │
   with vault-held                                   │
   wordpress.agent:pk                                │
          │                                          │
          │   POST /wp-json/mindx/v1/auth/verify     │
          │   {challenge_id, address, signature}     │
          │ ───────────────────────────────────────► │
          │                          1. recover signer from sig
          │                          2. allowlist check
          │                          3. map address → WP user
          │                          4. mint HS256 JWT (30 min)
          │ ◄─────────────────────────────────────── │
          │   {token, expires_at, user_id}           │
          │                                          │
          │   POST /wp-json/wp/v2/posts              │
          │   Authorization: Bearer <jwt>            │
          │ ───────────────────────────────────────► │
          │                                          │   plugin filter logs
          │                                          │   the JWT's sub user in;
          │                                          │   WP core applies caps
          │ ◄─────────────────────────────────────── │
          │   201 Created                            │
          │                                          │
```

## What it isn't

- **Not** a replacement for Application Passwords for human users.
  Human admins keep logging in via wp-login.php as normal.
- **Not** a way to grant universal access. The allowlist is a strict
  whitelist of `(address → WP-user)` pairs — only those addresses can
  authenticate, and only as their mapped user.
- **Not** dependent on the `jwt-auth/v1/token` plugin. This is a
  self-contained substrate.

## Install (Hostinger / cPanel / WP admin)

### One-click (WP admin)

1. Download `mindx-publish-auth.zip` from the mindX repo.
2. WordPress admin → Plugins → Add New → Upload Plugin.
3. Upload the zip, activate.

### Manual (SSH)

```bash
cd /path/to/wp-content/plugins/
git clone https://github.com/AgenticPlace/mindX.git tmp-mindx
cp -r tmp-mindx/mindx_wordpress_plugin ./mindx-publish-auth
rm -rf tmp-mindx
```

Then activate via WP admin.

## Configure (one minute)

1. Settings → mindX Publish Auth.
2. In the **Allowlist** box, paste one line per agent:
   ```
   0x1f0F44a5d800C060084A58525B717AC156Ab070b  codephreak
   ```
   That binds mindX's wordpress.agent wallet (left column) to the
   WordPress user it impersonates (right column). The plugin will
   reject any line whose user doesn't exist.
3. Save. That's the entire setup.

To rotate the JWT signing secret (e.g. after suspected compromise),
click **Rotate JWT secret** on the same page — all outstanding tokens
become invalid immediately.

## Diagnose

The plugin exposes an unauthenticated diagnostic endpoint:

```bash
curl https://rage.pythai.net/wp-json/mindx/v1/auth/diagnose | jq
```

Reports:

- Plugin version
- Whether PHP `gmp` is loaded (required for signature verify)
- Whether the JWT secret is configured
- Allowlist entry count (no addresses, no PII)
- Challenge + JWT TTLs

The endpoint never echoes the JWT secret, the allowlist contents, or
the audit log.

## Requirements

- WordPress 5.6+
- PHP 7.4+
- PHP `gmp` extension (for ECDSA recovery). Most shared hosts including
  Hostinger have it enabled by default.

## Security model

| Threat | Mitigation |
|---|---|
| **Replay of an old signature** | One-time challenge_id, marked consumed on first verify, transient expires in 5 min by default. |
| **Cross-site signature reuse** | Challenge string includes the site's hostname and is signed in the EIP-191 envelope, so a signature for `site-a.com` does not verify for `site-b.com`. |
| **Stolen JWT** | HS256 with a 32-byte server-side secret; tokens expire in 30 min; admin can rotate the secret with one click and invalidate every outstanding token immediately. |
| **Compromised wallet** | Operator removes the address from the allowlist via the admin page. The agent's WP-user capability is gone immediately. |
| **Brute-forcing addresses** | The allowlist is closed-set; signatures from non-listed addresses are rejected at the verify step (HTTP 403). |
| **Unauthenticated WP-REST publishing** | The plugin's `determine_current_user` filter only adds a user when the JWT verifies; it does not weaken any other auth path. |

## Audit log

Every successful authentication, every failed verification, and every
secret rotation lands in a ring buffer (last 50 events) visible on the
admin page. Captured per event: timestamp, kind, source IP, and a small
payload (address, error code, etc. — never a JWT or signature).

## License

Apache-2.0 — see `LICENSE`.
