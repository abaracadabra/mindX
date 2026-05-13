# Hostinger WordPress Setup for WordPress.agent

The `rage.pythai.net` site runs on Hostinger's managed PHP/Apache environment.
This document covers the one-time WordPress-side configuration the agent
depends on.

## 1. Application Password

The agent authenticates with WordPress Application Passwords, not the user
login password and not XML-RPC.

1. Log in to `https://rage.pythai.net/wp-admin`.
2. Navigate to `Users → Profile`.
3. Scroll to `Application Passwords`.
4. Enter `wordpress-agent-vps` as the name.
5. Click `Add New Application Password`.
6. Copy the 24-character spaced string. It will not be shown again.
7. Paste it into `WP_APP_PASSWORD` in `/etc/wordpress-agent/wordpress-agent.env`
   on the VPS, **including the spaces or hyphens**.

To revoke later, return to the same screen and click `Revoke` next to the
named entry.

## 2. Permalinks

The REST API requires non-default permalinks.

1. `Settings → Permalinks`.
2. Select `Post name` (or any non-default option).
3. Save changes.

If permalinks are set to `Plain`, the REST API will return PHP errors instead
of JSON.

## 3. REST API Reachability

Verify the REST API is reachable from the VPS:

```bash
curl -s https://rage.pythai.net/wp-json/wp/v2/ | jq '.namespace'
# Expected: "wp/v2"
```

If this returns HTML or a 403/404, one of the following is interfering:

- A security plugin (Wordfence, iThemes Security, Hostinger's own hardening)
  blocking `/wp-json/`. Allowlist the VPS egress IP or disable the rule.
- A `.htaccess` rule rejecting non-browser User-Agents. The agent sends a
  recognizable User-Agent (`mindX-WordpressAgent/0.1`); allowlist it.
- Hostinger's "Disable XML-RPC" toggle, which on some templates also blocks
  REST API endpoints. Confirm REST is enabled.

## 4. Caching

If LiteSpeed Cache or another full-page cache is active:

- Add `wp-json` and `wp-json/*` to the cache exclusion rules.
- Disable cache for logged-in users (the agent is effectively logged in via
  Application Password).

Without this, scheduled posts may appear inconsistently because cache layers
serve stale category/tag listings.

## 5. wp-cron

WordPress's scheduled-post mechanism depends on `wp-cron.php` being triggered.
Hostinger sometimes disables the default `wp-cron` and recommends a system
cron entry instead. Verify by:

1. Setting `define('DISABLE_WP_CRON', false);` in `wp-config.php` (or removing
   any `define('DISABLE_WP_CRON', true);`), OR
2. Adding a Hostinger cron job that hits
   `https://rage.pythai.net/wp-cron.php?doing_wp_cron` every 5 minutes.

The Hostinger cron job approach is more reliable on shared hosting because
`wp-cron` only fires when a visitor hits the site otherwise. Scheduled
publishing through WordPress.agent depends on this firing.

## 6. Optional: Custom Post Meta Whitelist

WordPress filters which post meta fields can be set via REST. To allow the
agent's provenance fields (`_mindx_content_hash`, `_x402_receipts`,
`_anchor_tx_hash`), add to your active theme's `functions.php` or a custom
plugin:

```php
add_action('init', function () {
    register_post_meta('post', '_mindx_content_hash', [
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'string',
        'auth_callback' => fn() => current_user_can('edit_posts'),
    ]);
    register_post_meta('post', '_x402_receipts', [
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'string',
        'auth_callback' => fn() => current_user_can('edit_posts'),
    ]);
    register_post_meta('post', '_anchor_tx_hash', [
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'string',
        'auth_callback' => fn() => current_user_can('edit_posts'),
    ]);
});
```

Without this snippet, the `meta` field on `/publish` calls is silently
ignored. The post still publishes; only the provenance metadata is dropped.

## 7. User Capabilities

The `codephreak` WordPress user must have at least the `Editor` role to
publish posts via REST. `Author` is insufficient if you need to publish on
behalf of others. `Administrator` works but is over-privileged.

## 8. Verification Checklist

Run this from the VPS once everything is configured:

```bash
# 1. Reachability
curl -s https://rage.pythai.net/wp-json/wp/v2/ | jq '.namespace'

# 2. Auth
curl -s -u "codephreak:xxxx-xxxx-xxxx-xxxx-xxxx-xxxx" \
    https://rage.pythai.net/wp-json/wp/v2/users/me | jq '.id, .name'

# 3. Agent health
curl -s http://127.0.0.1:8765/healthz | jq
```

All three should succeed. If any fail, fix that layer before moving up.
