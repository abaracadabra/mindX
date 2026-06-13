# Music 4 Robots 2 Dance 2 — pro SoundCloud player

**v1.0.0-alpha · working example.** A professional SoundCloud player for web2,
the **take · own · use · share** way. One tag drops a custom-control player
(play / pause / seek / volume, lazy facade, sticky dock, light/dark) for the
*Music 4 Robots 2 Dance 2* and *takIT* (home of **takeitownit** — *"Take it, Own
it."*) albums — and links the story:

> 📖 **The story:** https://rage.pythai.net/take-it-own-it-codephreak/

Songs owned by Professor Codephreak under the gnugui *take·own·use·share*
promotional licence (GPLv3-derived). Built as a companion to the mindX
`wordpress.agent` **soundcloud.tool** — same albums, same markup, one engine
(`assets/m4r2d2-player.js`) shared by the plugin, the [mindX app](https://mindx.pythai.net/music),
and the DROP.

> This plugin is **separate from** the *mindX Publish Auth* plugin (which handles
> wallet→JWT auth and stands alone). Run them side by side.

---

## Install (WordPress) — minimal

1. **Download** `music4robots2dance2.zip` (run `./build.sh`, or grab a release).
2. WordPress admin → **Plugins → Add New → Upload Plugin** → choose the zip → **Install** → **Activate**.
3. Done. A highlights player auto-drops on the front end (default ON). To place one yourself, put this in any post/page:

   ```
   [m4r2d2]
   ```

That's it. `[m4r2d2]` with no attributes plays the highlights with controls and the story link.

### More shortcodes

```
[m4r2d2 album="takit"]                         takIT (takeitownit)
[m4r2d2 theme="light" sticky="true"]           light theme, docks while playing
[m4r2d2 lazy="true"]                           click-to-load facade (fast pages)
[m4r2d2 playlist="2249417369" color="9d7833"]  any playlist by id
[m4r2d2 track="123456789" mode="compact"]      any track
[m4r2d2 url="https://soundcloud.com/mag-magnus/sets/takit-1"]
[m4r2d2_drop]                                   a "drop": play = consent, then docks
[soundcloud ...]                               alias of [m4r2d2]
```

Or insert the **Music 4 Robots 2 Dance 2** block (Embed category) in Gutenberg.

Turn the sitewide auto-drop **off**: Settings, or
`add_filter('m4r2d2_autodrop_enabled', '__return_false');`

---

## Share it (any site, no plugin) — one line

```html
<script src="https://cdn.jsdelivr.net/gh/gnugui/music4robots2dance2@v1.0.0-alpha/assets/m4r2d2-drop.js"
        data-album="music4robots2dance2" data-sticky="true" defer></script>
```

The DROP locates its own folder, loads the player + CSS beside it, and installs a
**permission-gated** player — autoplay needs a gesture, so the play button *is*
the consent ("auto install from permission"). Configure entirely via `data-*`
(`data-album`, `data-theme`, `data-sticky`, `data-permission`, `data-target`, …).

---

## From an app (custom element or event)

```html
<script src="assets/m4r2d2-player.js"></script>

<!-- declarative -->
<m4r2d2-player></m4r2d2-player>                       <!-- highlights -->
<m4r2d2-player album="takit" theme="light"></m4r2d2-player>

<!-- programmatic -->
<script> M4R2D2.drop({ album: "music4robots2dance2", sticky: true }); </script>

<!-- injective event: anyone can fire this to inject a player -->
<script>
window.dispatchEvent(new CustomEvent("m4r2d2:drop",
  { detail: { album: "music4robots2dance2", sticky: true } }));
</script>
```

Every player drives the official **SoundCloud Widget API** — `play()`, `pause()`,
`next()`, `prev()`, `seekTo(ms)`, `setVolume(0-100)`, live time, events. Live
demo in the mindX app: **`/music`**.

---

## Files

| File | Purpose |
|------|---------|
| `music4robots2dance2.php` | Bootstrap: shortcodes, block, asset enqueue, sitewide auto-drop (default ON), iframe kses whitelist, oEmbed. |
| `includes/class-m4r2d2-embeds.php` | Embed builder + `player_html()` enhanced wrapper. Album presets + highlights default. |
| `includes/class-m4r2d2-shortcode.php` | `[m4r2d2]` / `[soundcloud]` / `[m4r2d2_drop]`. |
| `assets/m4r2d2-player.js` | The engine: `<m4r2d2-player>` element + SSR enhancer + `M4R2D2.drop` + Widget-API control bar / facade / sticky dock. |
| `assets/m4r2d2-player.css` | Themed styling (dark/light). |
| `assets/m4r2d2-drop.js` | The paste-anywhere DROP loader. |
| `build.sh` | Zip the plugin. |

## License

GPL-3.0-or-later — gnugui's **take · own · use · share**. Take it, own your copy,
use it, share it forward. https://github.com/gnugui
