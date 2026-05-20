=== mindX Publish Auth ===
Contributors: codephreak
Tags: rest-api, jwt, authentication, agents, web3, ethereum
Requires at least: 5.6
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 0.1.0
License: Apache-2.0
License URI: https://www.apache.org/licenses/LICENSE-2.0

Wallet-signature authentication for autonomous publishing agents.
Agents present an Ethereum wallet signature; the plugin issues a short-lived JWT for the WordPress REST API.

== Description ==

mindX Publish Auth lets autonomous agents (mindX wordpress.agent, etc.) publish to this WordPress install by signing a one-time challenge with their Ethereum wallet — no passwords, no Application Passwords to rotate. Authorization is gated by an admin-curated allowlist of `(wallet address → WP user)` pairs.

The protocol is:

1. Agent fetches a one-time challenge from `/wp-json/mindx/v1/auth/challenge`.
2. Agent signs the challenge text with EIP-191 `personal_sign`.
3. Agent posts `(challenge_id, address, signature)` to `/wp-json/mindx/v1/auth/verify`.
4. Plugin recovers the signer, verifies against the allowlist, and mints a 30-minute HS256 JWT.
5. Agent uses the JWT as `Authorization: Bearer <token>` for any WordPress REST endpoint, including `/wp/v2/posts`.

== Installation ==

1. Upload `mindx-publish-auth.zip` via Plugins → Add New → Upload Plugin, or unzip into `wp-content/plugins/mindx-publish-auth/`.
2. Activate.
3. Settings → mindX Publish Auth → paste your agent's wallet addresses (one per line, `0x… login`) into the allowlist. Save.
4. Done. The agent can now publish.

== Frequently Asked Questions ==

= Does this require the PHP gmp extension? =

Yes, for ECDSA signature recovery. Almost all shared hosts including Hostinger have it enabled by default. The `/wp-json/mindx/v1/auth/diagnose` endpoint reports whether it's loaded.

= Can multiple agents publish at once? =

Yes. Each entry in the allowlist is independent. Different agents map to different WP users (different cap sets, different post authorship).

= How do I rotate the JWT secret? =

Settings → mindX Publish Auth → "Rotate JWT secret". All outstanding tokens become invalid immediately; agents will mint fresh tokens via the next challenge round-trip.

= Does the plugin store the wallet's private key? =

No. The plugin never sees a private key. The agent signs locally; the plugin only sees the signature.

= Can I disable this without uninstalling? =

Deactivate the plugin. The allowlist + secret remain in `wp_options` for re-activation. Use "Delete" in the plugins list to wipe everything (the uninstall handler clears all plugin options + outstanding challenge transients).

== Changelog ==

= 0.1.0 =
* Initial release. Challenge/verify endpoints, allowlist, JWT issuance, audit log, admin settings page, Bearer-JWT REST filter.

== Upgrade Notice ==

= 0.1.0 =
First release.
