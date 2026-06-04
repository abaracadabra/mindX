# Security model

| Threat | Mitigation |
|---|---|
| **Replay of an old signature** | One-time `challenge_id`, marked consumed on first verify. Challenge transient expires in 5 min by default (`mindx_auth_challenge_ttl`). |
| **Cross-site signature reuse** | Challenge string includes the site's hostname and is signed in the EIP-191 envelope, so a signature for `site-a.com` does not verify against `site-b.com`. |
| **Stolen JWT** | HS256 with a 32-byte server-side secret; tokens expire in 30 min; admin can rotate the secret with one click on the Settings page and invalidate every outstanding token immediately. |
| **Compromised wallet** | Operator removes the address from the allowlist via the admin page. The agent's WP-user capability is gone immediately on next verify. |
| **Brute-forcing addresses** | The allowlist is closed-set; signatures from non-listed addresses are rejected at the verify step (HTTP 403). |
| **Unauthenticated WP-REST publishing** | The plugin's `determine_current_user` filter only adds a user when the JWT verifies; it does not weaken any other auth path. |
| **Plugin-owned private keys** | The plugin never sees a private key. The agent signs locally; the plugin only sees the signature. |

## Audit log

Every successful authentication, every failed verification, and every secret rotation lands in a ring buffer (last 50 events) visible on the admin page. Captured per event:

- `at` — timestamp
- `kind` — `auth.success`, `auth.fail`, `secret.rotate`, etc.
- `ip` — source IP from `$_SERVER['REMOTE_ADDR']`
- `data` — small payload (verified address, error code, etc.). Never includes a JWT, a signature, or the JWT secret.

The audit log lives in the `mindx_auth_audit_log` wp_option and is non-autoloaded.

## Diagnostic endpoint contract

`GET /wp-json/mindx/v1/auth/diagnose` is intentionally unauthenticated so operators can confirm the plugin is healthy without minting a token first. It returns:

- `plugin_version`
- `gmp_loaded` (bool)
- `random_bytes_ok` (bool)
- `allowlist_entries` (count only — never the addresses)
- `jwt_secret_present` (bool)
- `challenge_ttl_s`, `jwt_ttl_s`
- `signature_path_runnable` (bool)

It never echoes the JWT secret, the allowlist contents, or the audit log payload.

## Uninstall

The uninstall handler (`uninstall.php`) — which fires only on **Delete** (not Deactivate) — removes every plugin-owned `wp_options` entry and clears any outstanding challenge transients. It does NOT touch user accounts or user_meta — those belong to WordPress, not this plugin.
