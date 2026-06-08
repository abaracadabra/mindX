# Music 4 Robots 2 Dance 2 — WordPress plugin

SoundCloud audio embeds across web2, the **take · own · use · share** way.

Ships the *Music 4 Robots 2 Dance 2* and *takIT* (home of **takeitownit** — *"Take
it, Own it."*) albums as one-line shortcodes and a Gutenberg block, whitelists the
SoundCloud player iframe so any editor can embed safely, and (re)registers the
SoundCloud oEmbed provider.

Companion to the mindX `wordpress.agent` **`soundcloud.tool`**
(`agents/wordpress_agent/soundcloud.py`, `POST /soundcloud/embed`) — same album
presets, same attribution, rendered byte-identically on either side.

## 🎧 The albums

### Music 4 Robots 2 Dance 2 — Mag Magnus

_the album robots dance to_

[![Listen on SoundCloud](https://img.shields.io/badge/SoundCloud-Listen-ff5500?logo=soundcloud&logoColor=white&style=for-the-badge)](https://soundcloud.com/mag-magnus/sets/music-for-robots-to-dance-2)

### takIT — Mag Magnus

_home of "takeitownit" — Take it, Own it. (use it · share it) — inspired by [github.com/gnugui](https://github.com/gnugui)_

[![Listen on SoundCloud](https://img.shields.io/badge/SoundCloud-Listen-ff5500?logo=soundcloud&logoColor=white&style=for-the-badge)](https://soundcloud.com/mag-magnus/sets/takit-1)

> **Why a badge and not a player?** GitHub sanitizes HTML in Markdown — `<iframe>`
> is stripped, so a live SoundCloud player can't render in a README. A linked
> badge (or a clickable cover-art thumbnail) is the accepted workaround. The live
> players render in WordPress via the shortcode/block below. The
> `soundcloud.readme_md` / `M4R2D2_Embeds` helpers generate this badge markup.

## Usage

```text
[m4r2d2]                                  → Music 4 Robots 2 Dance 2 album
[m4r2d2 album="takit"]                    → takIT (takeitownit)
[m4r2d2 playlist="2249417369" color="9d7833"]
[m4r2d2 track="123456789" visual="true"]
[m4r2d2 url="https://soundcloud.com/mag-magnus/sets/takit-1"]
[soundcloud ...]                          → alias of [m4r2d2]
```

Or insert the **Music 4 Robots 2 Dance 2** block (Embed category) in Gutenberg.

## Files

| File | Purpose |
|------|---------|
| `music4robots2dance2.php` | Plugin bootstrap: shortcode + block registration, iframe kses whitelist, oEmbed provider. |
| `includes/class-m4r2d2-embeds.php` | Pure embed builder (PHP mirror of `soundcloud.py`): resource URL → player URL → iframe + attribution. Album presets. |
| `includes/class-m4r2d2-shortcode.php` | `[m4r2d2]` / `[soundcloud]` renderer (shared by the block). |
| `uninstall.php` | Clean removal (no options are persisted; this is a safety no-op). |
| `build.sh` | Zip the plugin for upload. |

## License

GPL-3.0-or-later — gnugui's **take · own · use · share**. Take it, own your copy,
use it, share it forward under the same terms. https://github.com/gnugui
