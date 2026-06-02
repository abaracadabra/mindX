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

## 9. SEO Meta Rendering (plugin-less)

mindX publishes SEO metadata in a namespaced meta dict on every WordPress
post:

| Meta key | Purpose |
|---|---|
| `_seo_description` | `<meta name="description">` for the SERP snippet |
| `_seo_keywords` | `<meta name="keywords">` (modest signal, but free) |
| `_og_title` | `<meta property="og:title">` for Open Graph |
| `_og_description` | `<meta property="og:description">` |
| `_og_image_url` | `<meta property="og:image">` |
| `_twitter_card` | `<meta name="twitter:card">` (default `summary_large_image`) |
| `_twitter_creator` | `<meta name="twitter:creator">` (default `@mindX_ai`) |
| `_schema_article_json` | JSON-LD payload for `<script type="application/ld+json">` |

The wp.agent never installs a plugin; rendering happens via a small
PHP snippet in the active theme. Drop this into your theme's
`functions.php` (or a must-use plugin at
`wp-content/mu-plugins/mindx-seo.php`):

```php
<?php
/**
 * mindX SEO meta renderer.
 * Plugin-less alternative to Yoast/Rank Math; reads namespaced post
 * meta from the wordpress.agent publish payload and emits the
 * corresponding <meta> + JSON-LD tags in <head>.
 */

add_action('wp_head', function () {
    if (!is_singular('post')) return;
    $pid = get_the_ID();

    $desc          = get_post_meta($pid, '_seo_description', true);
    $kw            = get_post_meta($pid, '_seo_keywords', true);
    $og_title      = get_post_meta($pid, '_og_title', true);
    $og_desc       = get_post_meta($pid, '_og_description', true);
    $og_image      = get_post_meta($pid, '_og_image_url', true);
    $tw_card       = get_post_meta($pid, '_twitter_card', true);
    $tw_creator    = get_post_meta($pid, '_twitter_creator', true);
    $schema_json   = get_post_meta($pid, '_schema_article_json', true);

    if ($desc)        echo '<meta name="description" content="'         . esc_attr($desc)       . "\">\n";
    if ($kw)          echo '<meta name="keywords" content="'            . esc_attr($kw)         . "\">\n";
    if ($og_title)    echo '<meta property="og:title" content="'        . esc_attr($og_title)   . "\">\n";
    if ($og_desc)     echo '<meta property="og:description" content="'  . esc_attr($og_desc)    . "\">\n";
    if ($og_image)    echo '<meta property="og:image" content="'        . esc_url($og_image)    . "\">\n";
                       echo '<meta property="og:type" content="article">' . "\n";
                       echo '<meta property="og:url" content="' . esc_url(get_permalink($pid)) . "\">\n";
    if ($tw_card)     echo '<meta name="twitter:card" content="'        . esc_attr($tw_card)    . "\">\n";
    if ($tw_creator)  echo '<meta name="twitter:creator" content="'     . esc_attr($tw_creator) . "\">\n";
    if ($schema_json) echo "<script type=\"application/ld+json\">{$schema_json}</script>\n";
});

// Make the meta keys writable via the WordPress REST API (edit_posts auth).
foreach ([
    '_seo_description', '_seo_keywords',
    '_og_title', '_og_description', '_og_image_url',
    '_twitter_card', '_twitter_creator',
    '_schema_article_json',
] as $key) {
    register_post_meta('post', $key, [
        'show_in_rest'  => true,
        'single'        => true,
        'type'          => 'string',
        'auth_callback' => function () { return current_user_can('edit_posts'); },
    ]);
}
```

### Verification

After installing the snippet, publish any new post via mindX
(`POST /admin/publish-to-rage`) then view source on the rendered page.
You should see:

```html
<meta name="description" content="...">
<meta property="og:title" content="...">
<meta property="og:type" content="article">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article",...}</script>
```

Existing posts published before the snippet was installed will continue
to render normally (no description tag, no JSON-LD) — the snippet is
inert until a post carries the namespaced meta.

### If you later install Yoast or Rank Math

Both plugins use a different meta-key namespace
(`_yoast_wpseo_*` / `rank_math_*`), so no collision. mindX will add
plugin-aware key aliasing in a future release; until then, the
plugin-less snippet remains the canonical renderer.

## 10. Featured-image rotation from /gfx/

When AuthorAgent publishes, it picks a hero image from
`/home/hacker/mindX/gfx/` based on the article topic (see
`agents/wordpress_agent/featured_image.py` and the curated map
`TOPIC_TO_FILE`). The image is uploaded via `POST /media`, which
returns a WordPress `media_id`. That id is then attached to the post
as `featured_media`.

The rotation is deterministic per topic — *competition* → `war_council_gold.png`,
*BANKON* → `bankonvault.png`, *OpenClaw / Hermes / swarmclaw* →
`sevensoldiers.png`, and so on. The fallback is `doorway1.webp`. The
WordPress side requires nothing beyond a writable media library and a
user (`codephreak`) with `upload_files` capability — both of which are
already configured in steps 1–7 above.
