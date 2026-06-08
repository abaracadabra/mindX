=== Music 4 Robots 2 Dance 2 ===
Contributors: mindx, magmagnus, gnugui
Tags: soundcloud, audio, embed, music, oembed, shortcode, block
Requires at least: 5.6
Tested up to: 6.5
Requires PHP: 7.4
Stable tag: 0.1.0
License: GPL-3.0-or-later
License URI: https://www.gnu.org/licenses/gpl-3.0.html

SoundCloud audio embeds across web2, the take·own·use·share way. Ships the "Music 4 Robots 2 Dance 2" and "takIT" (takeitownit) albums as one-line shortcodes and a Gutenberg block.

== Description ==

A small, single-purpose plugin for embedding SoundCloud tracks and playlists
anywhere on a WordPress site, the gnugui way: **take it, own it, use it, share it.**

* `[m4r2d2]` — embeds the *Music 4 Robots 2 Dance 2* album.
* `[m4r2d2 album="takit"]` — embeds *takIT*, home of the "takeitownit" song.
* `[m4r2d2 playlist="2249417369" color="9d7833"]` — any playlist by id.
* `[m4r2d2 track="123456789" visual="true"]` — any track by id.
* `[m4r2d2 url="https://soundcloud.com/mag-magnus/sets/takit-1"]` — any permalink.
* `[soundcloud ...]` — alias of `[m4r2d2]`.
* A server-rendered **Gutenberg block** ("Music 4 Robots 2 Dance 2", Embed category).

It also:

* **Whitelists the SoundCloud player iframe** in post content so editors without
  the `unfiltered_html` capability can still embed (only the SoundCloud widget
  host is allowed — not arbitrary iframes).
* (Re)registers the **SoundCloud oEmbed provider** so a bare `/sets/` URL on its
  own line auto-embeds.

It is the WordPress companion to the mindX `wordpress.agent` `soundcloud.tool`
(`POST /soundcloud/embed`), which renders byte-identical embed HTML — the same
album presets, the same attribution, server-side.

== Philosophy ==

gnugui — **take · own · use · share** (https://github.com/gnugui). The song
"takeitownit" expresses it as *"Take it, Own it."* This plugin is GPLv3: take it,
own your copy, use it freely, share it forward under the same terms.

== Installation ==

1. Upload the `music4robots2dance2` folder to `/wp-content/plugins/`.
2. Activate through the *Plugins* menu in WordPress.
3. Drop `[m4r2d2]` into any post/page, or add the "Music 4 Robots 2 Dance 2"
   block.

== Changelog ==

= 0.1.0 =
* Initial release: `[m4r2d2]`/`[soundcloud]` shortcodes, album presets
  (music4robots2dance2, takit), Gutenberg block, iframe kses whitelist, oEmbed
  provider registration.
