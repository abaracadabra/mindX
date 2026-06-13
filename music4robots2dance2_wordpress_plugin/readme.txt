=== Music 4 Robots 2 Dance 2 ===
Contributors: mindx, magmagnus, gnugui
Tags: soundcloud, audio, player, music, oembed, shortcode, block, widget-api
Requires at least: 5.6
Tested up to: 6.5
Requires PHP: 7.4
Stable tag: 1.0.0-alpha
License: GPL-3.0-or-later
License URI: https://www.gnu.org/licenses/gpl-3.0.html

Pro SoundCloud player for web2, the take·own·use·share way. One shortcode [m4r2d2] drops a custom-control player for the "Music 4 Robots 2 Dance 2" + "takIT" (takeitownit) albums. v1 alpha working example.

== Description ==

A professional SoundCloud player you can set up in seconds and hand to anyone.

* `[m4r2d2]` — the **highlights**: Music 4 Robots 2 Dance 2 with a custom control
  bar (play/pause, prev/next, seek, volume, live time), light/dark theme, and a
  link to the story at https://rage.pythai.net/take-it-own-it-codephreak/
* `[m4r2d2 album="takit"]` — takIT, home of the "takeitownit" song.
* `[m4r2d2 lazy="true"]` — click-to-load facade (fast pages).
* `[m4r2d2 sticky="true"]` — docks to the bottom of the screen while playing.
* `[m4r2d2 url=... | playlist=... | track=...]` — any SoundCloud resource.
* `[m4r2d2_drop]` — a "drop": permission-gated (the play button is the consent),
  then docks.
* A server-rendered **Gutenberg block** and a paste-anywhere **DROP** loader.

Every player drives the official SoundCloud Widget API. The same engine powers
the mindX app player (`/music`) and the standalone DROP — one source of truth.

This plugin is **separate from** the mindX Publish Auth plugin (wallet→JWT auth),
which is important standalone; run them side by side.

== Philosophy ==

gnugui — **take · own · use · share** (https://github.com/gnugui). The song
"takeitownit" expresses it as *"Take it, Own it."* Songs owned by Professor
Codephreak under the gnugui promotional licence (GPLv3-derived). GPLv3: take it,
own your copy, use it, share it forward.

== Installation ==

1. Upload `music4robots2dance2.zip` via Plugins → Add New → Upload Plugin.
2. Activate.
3. Drop `[m4r2d2]` into any post/page (or just leave the default sitewide
   auto-drop on).

To share on a non-WordPress site, paste one script tag — see README.md.

== Changelog ==

= 1.0.0-alpha =
* Pro player: SoundCloud Widget API control bar, lazy facade, sticky dock,
  light/dark, story link, highlights default.
* Framework-agnostic engine `assets/m4r2d2-player.js` — `<m4r2d2-player>` custom
  element + SSR enhancer + `M4R2D2.drop()`.
* The DROP: `assets/m4r2d2-drop.js` paste-anywhere loader + `m4r2d2:drop`
  injective event + auto-install-from-permission.
* Sitewide auto-drop (default ON, filterable), `[m4r2d2_drop]` shortcode.
* Shared with the mindX app (`/music`) and the wordpress.agent soundcloud.tool.

= 0.1.0 =
* Initial release: shortcodes, album presets, Gutenberg block, iframe kses
  whitelist, oEmbed provider.
