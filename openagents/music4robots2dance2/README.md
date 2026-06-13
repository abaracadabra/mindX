<div align="center">

# music4robots2dance2

### *music for robots to dance to* — a complete, forkable SoundCloud interface for WordPress

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-d4af37.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![WordPress Plugin](https://img.shields.io/badge/WordPress-plugin-0a0a12.svg)](https://wordpress.org/)
[![version](https://img.shields.io/badge/version-1.0.0-d4af37.svg)](readme.txt)

*take it · own it · use it · share it*

</div>

A small, self-contained WordPress plugin that puts a full SoundCloud player on
any post or page — **shortcode**, **Gutenberg block**, **oEmbed**, and a
cypherpunk2048-styled frame. Built to support the link in
**[rage.pythai.net/take-it-own-it-codephreak](https://rage.pythai.net/take-it-own-it-codephreak/)**.

Downloadable. Forkable. GPLv3. No build step, no CDN, no tracking — one PHP file,
one stylesheet, one block script. Read it, change it, run your own.

## Install

**Download:** grab the prebuilt
[`music4robots2dance2.zip`](https://github.com/gnugui/music4robots2dance2/releases/latest/download/music4robots2dance2.zip)
from the [latest release](https://github.com/gnugui/music4robots2dance2/releases/latest)
(or the green *Code → Download ZIP*), then **Plugins → Add New → Upload Plugin**
in WordPress and activate.

**Fork:** clone this repo, drop the folder into `wp-content/plugins/`, activate.

## Use

```text
[music4robots2dance2 url="https://soundcloud.com/codephreak"]
[soundcloud url="https://soundcloud.com/your/track" color="d4af37" title="music4robots2dance2"]
```

- **Block:** add the **“m4r2d2 player”** block (Embed category) and paste a URL.
- **oEmbed:** just paste a `soundcloud.com` link on its own line.
- **Defaults:** *Settings → music4robots2dance2* (default URL + accent colour).

| Attribute | Default | Notes |
|---|---|---|
| `url` | `https://soundcloud.com/codephreak` | track, set, or user URL |
| `color` | `d4af37` | hex accent, no `#` |
| `visual` | `true` | big artwork player |
| `autoplay` | `false` | robots ask first |
| `height` | auto | pixels |
| `title` | — | optional caption |

## Why it exists

So an article on [RAGE](https://rage.pythai.net) — the aggregation & publishing
company — can carry the music with it, on infrastructure the author owns. It is
the same posture as everything in the [cypherpunk2048](https://github.com/cypherpunk2048)
standard and its sibling [GNUVAULT](https://github.com/gnugui/GNUVAULT): open,
client-side, yours to fork.

## License

[**GPL-3.0-or-later**](LICENSE). *take it, own it, use it, share it.*
