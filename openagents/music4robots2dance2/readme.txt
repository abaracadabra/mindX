=== music4robots2dance2 ===
Contributors: codephreak, cypherpunk2048
Tags: soundcloud, music, embed, player, oembed, block, shortcode
Requires at least: 5.8
Tested up to: 6.7
Requires PHP: 7.2
Stable tag: 1.0.0
License: GPL-3.0-or-later
License URI: https://www.gnu.org/licenses/gpl-3.0.html

music for robots to dance to — a complete, forkable SoundCloud interface for WordPress: shortcode, Gutenberg block, oEmbed, cypherpunk2048-styled player.

== Description ==

music4robots2dance2 puts a full SoundCloud player on any post or page. It is one
PHP file, one stylesheet, and one block script — no build step, no CDN, no
tracking. Read it, change it, run your own. Built to support the link in
https://rage.pythai.net/take-it-own-it-codephreak/ .

Features:

* Shortcodes: `[music4robots2dance2 url="…"]`, `[soundcloud url="…"]`, `[m4r2d2 url="…"]`
* Gutenberg block: "m4r2d2 player" (server-rendered)
* oEmbed: paste a soundcloud.com link on its own line
* Settings → music4robots2dance2: default URL + accent colour
* cypherpunk2048 styling (dark + gold), GPLv3, forkable

take it, own it, use it, share it.

== Installation ==

1. Upload the `music4robots2dance2` folder to `/wp-content/plugins/`, or install
   the ZIP via Plugins → Add New → Upload Plugin.
2. Activate the plugin.
3. Use the shortcode, the block, or paste a SoundCloud link.

== Frequently Asked Questions ==

= Does it phone home or track listeners? =
No. It renders SoundCloud's own player iframe and adds a stylesheet. Nothing else.

= Can I fork it? =
Yes — that is the point. GPL-3.0-or-later. https://github.com/gnugui/music4robots2dance2

== Changelog ==

= 1.0.0 =
* Initial release: shortcode, block, oEmbed, settings, cypherpunk2048 styling.
