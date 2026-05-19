# Install

## Requirements

- WordPress 5.6+
- PHP 7.4+
- PHP `gmp` extension (for ECDSA recovery). Most shared hosts including Hostinger have it enabled by default. Confirm via `/wp-json/mindx/v1/auth/diagnose`.

## One-click (WP admin)

1. Download `mindx-publish-auth.zip` from the [Releases](https://github.com/cryptoagi/mindx_wordpress_plugin/releases) page.
2. WordPress admin → **Plugins** → **Add New** → **Upload Plugin**.
3. Upload the zip and activate.

## Manual (SSH)

```bash
cd /path/to/wp-content/plugins/
git clone https://github.com/cryptoagi/mindx_wordpress_plugin.git mindx-publish-auth
```

Activate via WP admin.

## Configure (one minute)

1. **Settings** → **mindX Publish Auth**.
2. In the **Allowlist** box, paste one line per agent:
   ```
   0x1f0F44a5d800C060084A58525B717AC156Ab070b  codephreak
   ```
   That binds the agent's wallet address (left column) to the WordPress user it impersonates (right column). The plugin rejects any line whose user does not exist.
3. **Save**.

The agent can now mint a JWT and publish.

## Rotate the JWT secret

After suspected compromise, click **Rotate JWT secret** on the same Settings page. All outstanding tokens become invalid immediately; agents will mint fresh tokens on their next `/auth/challenge` → `/auth/verify` round-trip.

## Diagnose

```bash
curl https://your-wp-host/wp-json/mindx/v1/auth/diagnose | jq
```

Reports plugin version, whether `gmp` is loaded, whether the JWT secret is configured, allowlist entry count (no addresses, no PII), and the configured TTLs.

## Uninstall (full wipe)

In the Plugins list, click **Delete** (not Deactivate). The uninstall handler clears all plugin-owned `wp_options` entries and outstanding challenge transients. User accounts and user_meta are left intact.

## Build the zip yourself

```bash
git clone https://github.com/cryptoagi/mindx_wordpress_plugin.git
cd mindx_wordpress_plugin
bash build.sh
# Produces mindx-publish-auth.zip with a printed sha256.
```

`build.sh` excludes `.git/`, `docs/`, `build.sh`, and `.gitignore` from the bundle — WordPress doesn't need them at runtime.
