# Protocol

The plugin exposes four REST routes under `/wp-json/mindx/v1/`. Auth flow is wallet-signature → short-lived JWT.

## Sequence

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

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET  | `/wp-json/mindx/v1/auth/challenge` | none | Returns `{challenge_id, message, expires_at}`. Challenge is held in a WP transient with a configurable TTL (default 5 min). |
| POST | `/wp-json/mindx/v1/auth/verify`    | none (signature gates everything) | Body: `{challenge_id, address, signature}`. On success returns `{token, token_type:"Bearer", user_id, expires_at}`. The challenge_id is consumed (one-time). |
| GET  | `/wp-json/mindx/v1/auth/whoami`    | Bearer JWT | Returns the verified JWT claims + mapped WP user info. Useful for client smoke tests. |
| GET  | `/wp-json/mindx/v1/auth/diagnose`  | none | Defensive diagnostic. Returns plugin version, whether `gmp` is loaded, JWT secret present, allowlist entry count, TTLs. Never echoes secrets, addresses, or the audit log. |

## Signature envelope (EIP-191)

The agent signs the `message` field from `/auth/challenge` using EIP-191 `personal_sign`. The plugin reconstructs the EIP-191 envelope (`"\x19Ethereum Signed Message:\n" + len(message) + message`) and recovers the signer with `ecrecover`. The recovered address is compared (case-insensitive, lowercased) against the configured allowlist. The challenge message contains the WP host name, so a signature minted for `site-a.com` does not verify against `site-b.com`.

## JWT shape

- Algorithm: **HS256** with a 32-byte server-side secret generated at plugin activation.
- TTL: **30 minutes** (override via `mindx_auth_jwt_ttl` option).
- Claims: `iss` (WP site URL), `sub` (WP user id), `iat`, `exp`, plus `address` (the verified wallet address).

`rest_authentication_errors` filter maps the `sub` claim back to a WP user so subsequent `/wp/v2/posts` calls run with that user's caps. The filter never *weakens* any other WP auth path — it only adds a user when a valid Bearer JWT is presented.

## Implementation files

- `mindx-publish-auth.php` — plugin bootstrap, activation hooks, helper functions.
- `includes/class-mindx-auth-rest.php` — route registration + handlers.
- `includes/class-mindx-auth-jwt.php` — HS256 mint / verify.
- `includes/secp256k1.php` — pure-PHP secp256k1 ECDSA recovery (needs `gmp`).
- `includes/keccak.php` — pure-PHP Keccak-256 used by the EIP-191 hash.
- `includes/class-mindx-auth-settings.php` — admin Settings page + `determine_current_user` filter.
