# Music 4 Robots 2 Dance 2 — pro SoundCloud player

One audio-player engine, three surfaces (WordPress, the mindX app, a paste-anywhere
DROP), driven by the official **SoundCloud Widget API**. Companion to the
`wordpress.agent` **soundcloud.tool**. The story it promotes:
[rage.pythai.net/take-it-own-it-codephreak](https://rage.pythai.net/take-it-own-it-codephreak/)
(post 802). **take · own · use · share** — GPL-3.0.

> Separate from the **mindX Publish Auth** plugin (wallet→JWT, `mindx_wordpress_plugin/`),
> which is important standalone. Run them side by side.

## Components

| Where | What |
|-------|------|
| Engine | `music4robots2dance2_wordpress_plugin/assets/m4r2d2-player.js` — `<m4r2d2-player>` custom element + SSR enhancer + `M4R2D2.drop()`. Control bar (play/pause/prev/next/seek/volume/time), lazy facade, sticky dock, light/dark. |
| DROP | `assets/m4r2d2-drop.js` — paste-anywhere loader + `m4r2d2:drop` injective event + auto-install-from-permission (play = consent). |
| WordPress | `music4robots2dance2_wordpress_plugin/` (v1.0.0-alpha) — `[m4r2d2]`/`[soundcloud]`/`[m4r2d2_drop]`, Gutenberg block, sitewide auto-drop (default ON, filter `m4r2d2_autodrop_enabled`), iframe kses whitelist, oEmbed. |
| mindX app | `mindx_frontend_ui/music.html` (route `/music`) + `mindx_frontend_ui/m4r2d2/*` (assets, served at `/m4r2d2/`) — same engine, in-app player + DROP demo. |
| soundcloud.tool | `agents/wordpress_agent/soundcloud.py` — `embed/playlist_embed/track_embed/album_embed` (plain) + `player_config/widget_player/drop_snippet` (pro). |
| Endpoints | `POST /soundcloud/embed`, `POST /soundcloud/player`, `POST /soundcloud/player_config`, `GET /soundcloud/drop` (wordpress.agent server). |

## Albums (KNOWN_PLAYLISTS)

| key | title | id | notes |
|-----|-------|----|-------|
| `music4robots2dance2` | Music 4 Robots 2 Dance 2 | 2216206346 | visual; the highlights / zero-config default |
| `takit` | takIT | 2249417369 | home of **takeitownit** — *"Take it, Own it."*, inspired by github.com/gnugui |

Artist: Mag Magnus (Magnusson) — soundcloud.com/mag-magnus. Songs owned by
Professor Codephreak under the gnugui *take·own·use·share* promotional licence
(GPLv3-derived).

## Usage

**WordPress** (minimal): activate the plugin → `[m4r2d2]` (or leave the default
sitewide auto-drop on).

```
[m4r2d2]                                   highlights + controls + story link
[m4r2d2 album="takit" theme="light"]
[m4r2d2 lazy="true" sticky="true"]
[m4r2d2 playlist="2249417369" color="9d7833"]
[m4r2d2_drop]                              play = consent, then docks
```

**App / any site**:

```html
<script src=".../assets/m4r2d2-player.js"></script>
<m4r2d2-player></m4r2d2-player>
<script> M4R2D2.drop({ album: "music4robots2dance2", sticky: true }); </script>
<!-- injective event -->
<script>window.dispatchEvent(new CustomEvent("m4r2d2:drop",{detail:{album:"takit"}}));</script>
```

**Share (one line)**:

```html
<script src="https://cdn.jsdelivr.net/gh/gnugui/music4robots2dance2@v1.0.0-alpha/assets/m4r2d2-drop.js"
        data-album="music4robots2dance2" data-sticky="true" defer></script>
```

## GitHub

- Canonical single-file v1.0.0: `github.com/gnugui/music4robots2dance2` (main).
- This pro-player example: branch `pro-player-v1-alpha`, `examples/pro-player-v1-alpha/`.

## Tests

`tests/test_soundcloud_player.py` (player_config / widget_player / drop_snippet).
JS validated with `node --check`.
