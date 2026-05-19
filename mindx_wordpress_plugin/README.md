# mindX Publish Auth

> *Wallet-signature authentication for autonomous publishing agents on WordPress.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Lets mindX (and any agent presenting a wallet signature) publish to a WordPress install without ever putting a password — Application or otherwise — on the wire. Replaces ad-hoc Application-Password handling with a wallet signature flow that the agent already has by design.

## Quick install

1. Download `mindx-publish-auth.zip` from the [Releases](https://github.com/cryptoagi/mindx_wordpress_plugin/releases) page.
2. WordPress admin → **Plugins** → **Add New** → **Upload Plugin** → activate.
3. **Settings** → **mindX Publish Auth** → paste one line per agent into the Allowlist:
   ```
   0x1f0F44a5d800C060084A58525B717AC156Ab070b  codephreak
   ```
   `(wallet address)  (WP username)`. Save.

The agent can now mint a JWT and publish. Full install paths, configure flow, and rotate-secret instructions in [`docs/INSTALL.md`](docs/INSTALL.md).

## What it isn't

- **Not** a replacement for Application Passwords for human users. Human admins keep logging in via wp-login.php as normal.
- **Not** a way to grant universal access. The allowlist is a strict whitelist of `(address → WP-user)` pairs — only those addresses can authenticate, and only as their mapped user.
- **Not** dependent on the `jwt-auth/v1/token` plugin. This is a self-contained substrate.

## Documentation

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — full challenge/verify sequence, REST endpoint table, EIP-191 envelope, JWT claims.
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model, audit log contract, diagnostic endpoint contract.
- [`docs/INSTALL.md`](docs/INSTALL.md) — install paths (one-click and SSH), configure, rotate secret, diagnose, uninstall, reproducible build.

## Diagnose

```bash
curl https://your-wp-host/wp-json/mindx/v1/auth/diagnose | jq
```

Reports plugin version, `gmp` extension, JWT secret presence, allowlist entry count (count only — never the addresses), and TTLs. Never echoes secrets.

## Requirements

- WordPress 5.6+, PHP 7.4+, PHP `gmp` extension.

## License

Apache-2.0 — see [LICENSE](LICENSE).
