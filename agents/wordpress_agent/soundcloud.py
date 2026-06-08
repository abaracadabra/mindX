# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""soundcloud.tool — SoundCloud audio embeds for the wordpress.agent.

Single responsibility: turn a SoundCloud resource (a track or a playlist/set)
into the exact HTML that WordPress will render — the ``w.soundcloud.com`` player
``<iframe>`` plus the small attribution ``<div>`` SoundCloud requires. Pure and
deterministic: same inputs → byte-identical HTML. No network, no auth, no state.

Why a tool and not just pasted HTML: SoundCloud's own "Embed → WordPress" flow
(https://help.soundcloud.com/hc/en-us/articles/115003448667) hands you a blob of
iframe markup with a dozen query params. This module makes that blob a *function*
so AuthorAgent (and the music4robots2dance2 WP plugin) can mint correct,
consistent embeds for any track/playlist, and so the album's canonical players
live in one place.

Boundary note: this module *renders* embed HTML. It never publishes — the
WordpressAgent does that. The article/plugin decide where the HTML goes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any
from urllib.parse import quote, urlparse

# SoundCloud's HTML5 widget host. The player takes a single ``url=`` param
# pointing at either a public permalink (soundcloud.com/...) or an API resource
# (api.soundcloud.com/{tracks,playlists}/...), plus display flags.
PLAYER_BASE = "https://w.soundcloud.com/player/"

# Default visual heights SoundCloud uses: ~166px for a compact track, 300px for
# a "visual" (full-bleed artwork) player, 450px for a playlist with the tracklist.
HEIGHT_TRACK = 166
HEIGHT_VISUAL = 300
HEIGHT_PLAYLIST = 450

# SoundCloud brand orange, used as the default waveform/accent color.
COLOR_DEFAULT = "ff5500"

# The highlights: the rage.pythai.net story the pro player promotes by default.
ARTICLE_URL = "https://rage.pythai.net/take-it-own-it-codephreak/"
DEFAULT_ALBUM = "music4robots2dance2"


def _norm_color(color: str) -> str:
    """Normalize an accent color to the bare 6-hex form SoundCloud expects.

    Accepts ``#ff5500``, ``ff5500``, ``%23ff5500``; returns ``ff5500``.
    """
    c = (color or "").strip().lstrip("#")
    if c.lower().startswith("%23"):
        c = c[3:]
    return c or COLOR_DEFAULT


def playlist_resource_url(playlist_id: int | str, *, use_urn: bool = True) -> str:
    """API resource URL for a playlist/set.

    SoundCloud's current embed generator points the player at the URN form
    (``soundcloud:playlists:<id>``); the bare-numeric form also resolves. We
    default to the URN form to match freshly-generated embeds byte-for-byte.
    """
    pid = str(playlist_id).strip()
    tail = f"soundcloud:playlists:{pid}" if use_urn else pid
    return f"https://api.soundcloud.com/playlists/{tail}"


def track_resource_url(track_id: int | str, *, use_urn: bool = True) -> str:
    """API resource URL for a single track."""
    tid = str(track_id).strip()
    tail = f"soundcloud:tracks:{tid}" if use_urn else tid
    return f"https://api.soundcloud.com/tracks/{tail}"


def build_player_url(
    resource_url: str,
    *,
    color: str = COLOR_DEFAULT,
    auto_play: bool = False,
    visual: bool = False,
    hide_related: bool = False,
    show_comments: bool = True,
    show_user: bool = True,
    show_reposts: bool = False,
    show_teaser: bool = True,
) -> str:
    """Assemble the ``w.soundcloud.com/player/?...`` URL.

    ``resource_url`` is single-encoded into the ``url=`` param (so the API URN's
    inner colons become ``%3A``, matching SoundCloud's output). Boolean flags are
    rendered lowercase, the order matching SoundCloud's generator for stable diffs.
    """

    def b(v: bool) -> str:
        return "true" if v else "false"

    # safe="/:" keeps the scheme's "://" and path slashes readable while encoding
    # the URN's colons — reproduces the `https%3A//.../soundcloud%3Aplaylists%3A..`
    # shape SoundCloud emits.
    enc = quote(resource_url, safe="/")
    params = (
        f"url={enc}"
        f"&color=%23{_norm_color(color)}"
        f"&auto_play={b(auto_play)}"
        f"&hide_related={b(hide_related)}"
        f"&show_comments={b(show_comments)}"
        f"&show_user={b(show_user)}"
        f"&show_reposts={b(show_reposts)}"
        f"&show_teaser={b(show_teaser)}"
    )
    if visual:
        params += "&visual=true"
    return f"{PLAYER_BASE}?{params}"


@dataclass(slots=True, frozen=True)
class Attribution:
    """The credit line SoundCloud's ToS requires beneath an embed."""

    author_name: str
    author_url: str
    title: str = ""
    title_url: str = ""

    def to_html(self) -> str:
        # Matches SoundCloud's emitted attribution div (font stack + muted color),
        # all interpolated values HTML-escaped.
        style_wrap = (
            "font-size: 10px; color: #cccccc;line-break: anywhere;word-break: normal;"
            "overflow: hidden;white-space: nowrap;text-overflow: ellipsis; "
            "font-family: Interstate,Lucida Grande,Lucida Sans Unicode,Lucida Sans,"
            "Garuda,Verdana,Tahoma,sans-serif;font-weight: 100;"
        )
        style_a = "color: #cccccc; text-decoration: none;"
        parts = [
            f'<a href="{escape(self.author_url)}" title="{escape(self.author_name)}" '
            f'target="_blank" style="{style_a}">{escape(self.author_name)}</a>'
        ]
        if self.title:
            href = escape(self.title_url or self.author_url)
            parts.append(
                f'<a href="{href}" title="{escape(self.title)}" '
                f'target="_blank" style="{style_a}">{escape(self.title)}</a>'
            )
        inner = " · ".join(parts)
        return f'<div style="{style_wrap}">{inner}</div>'


def embed(
    resource_url: str,
    *,
    attribution: Attribution | None = None,
    width: str = "100%",
    height: int = HEIGHT_PLAYLIST,
    color: str = COLOR_DEFAULT,
    auto_play: bool = False,
    visual: bool = False,
    hide_related: bool = False,
    show_comments: bool = True,
    show_user: bool = True,
    show_reposts: bool = False,
    show_teaser: bool = True,
) -> str:
    """Render the full embed: the player ``<iframe>`` + optional attribution div.

    This is the canonical output the wordpress.agent hands to WordPress. The
    iframe carries the ``allow="autoplay; encrypted-media"`` permissions
    SoundCloud needs and is responsive via ``width="100%"``.
    """
    src = build_player_url(
        resource_url,
        color=color,
        auto_play=auto_play,
        visual=visual,
        hide_related=hide_related,
        show_comments=show_comments,
        show_user=show_user,
        show_reposts=show_reposts,
        show_teaser=show_teaser,
    )
    iframe = (
        f'<iframe width="{escape(str(width))}" height="{int(height)}" '
        f'scrolling="no" frameborder="no" allow="autoplay; encrypted-media" '
        f'src="{escape(src)}"></iframe>'
    )
    if attribution is not None:
        return iframe + attribution.to_html()
    return iframe


def playlist_embed(
    playlist_id: int | str,
    *,
    attribution: Attribution | None = None,
    color: str = COLOR_DEFAULT,
    height: int = HEIGHT_PLAYLIST,
    visual: bool = False,
    auto_play: bool = False,
    use_urn: bool = True,
    **flags: Any,
) -> str:
    """Embed a playlist/set by id."""
    return embed(
        playlist_resource_url(playlist_id, use_urn=use_urn),
        attribution=attribution,
        color=color,
        height=height,
        visual=visual,
        auto_play=auto_play,
        **flags,
    )


def track_embed(
    track_id: int | str,
    *,
    attribution: Attribution | None = None,
    color: str = COLOR_DEFAULT,
    height: int = HEIGHT_TRACK,
    visual: bool = False,
    auto_play: bool = False,
    use_urn: bool = True,
    **flags: Any,
) -> str:
    """Embed a single track by id."""
    return embed(
        track_resource_url(track_id, use_urn=use_urn),
        attribution=attribution,
        color=color,
        height=height,
        visual=visual,
        auto_play=auto_play,
        **flags,
    )


def embed_from_url(
    permalink: str,
    *,
    attribution: Attribution | None = None,
    color: str = COLOR_DEFAULT,
    height: int | None = None,
    visual: bool = False,
    auto_play: bool = False,
    **flags: Any,
) -> str:
    """Embed any public SoundCloud permalink (track or set).

    The player accepts a ``soundcloud.com/...`` URL directly, so this is the most
    robust path when you have a link but not the numeric id. Height defaults to a
    set-sized player for ``/sets/`` URLs, track-sized otherwise.
    """
    is_set = "/sets/" in urlparse(permalink).path
    h = height if height is not None else (HEIGHT_PLAYLIST if is_set else HEIGHT_TRACK)
    return embed(
        permalink,
        attribution=attribution,
        color=color,
        height=h,
        visual=visual,
        auto_play=auto_play,
        **flags,
    )


# ── Known albums — the Professor Codephreak / Mag Magnus tribute set ──────────
# "takIT" embodies the take-own-use-share ethos that the github.com/gnugui repo
# inspired; "Music 4 Robots 2 Dance 2" is the album these embeds promote.
ARTIST = Attribution(author_name="Mag Magnus", author_url="https://soundcloud.com/mag-magnus")

KNOWN_PLAYLISTS: dict[str, dict[str, Any]] = {
    "takit": {
        "playlist_id": 2249417369,
        "title": "takIT",
        "set_url": "https://soundcloud.com/mag-magnus/sets/takit-1",
        "color": "9d7833",
        "height": HEIGHT_PLAYLIST,
        "visual": False,
        # The song is "takeitownit" — it expresses as "Take it, Own it." (and,
        # in the open-source spirit, use it and share it) — inspired by the
        # github.com/gnugui repository.
        "blurb": "home of \"takeitownit\" — Take it, Own it. (use it · share it) — inspired by github.com/gnugui",
    },
    "music4robots2dance2": {
        "playlist_id": 2216206346,
        "title": "Music  4 Robots 2 Dance 2",
        "set_url": "https://soundcloud.com/mag-magnus/sets/music-for-robots-to-dance-2",
        "color": "ff5500",
        "height": HEIGHT_VISUAL,
        "visual": True,
        "blurb": "the album robots dance to",
    },
}


def album_embed(key: str, *, auto_play: bool = False, **overrides: Any) -> str:
    """Embed one of the KNOWN_PLAYLISTS by key (``takit`` / ``music4robots2dance2``)."""
    spec = KNOWN_PLAYLISTS.get(key.strip().lower())
    if spec is None:
        raise KeyError(f"unknown album {key!r}; known: {sorted(KNOWN_PLAYLISTS)}")
    attribution = Attribution(
        author_name=ARTIST.author_name,
        author_url=ARTIST.author_url,
        title=spec["title"],
        title_url=spec["set_url"],
    )
    return playlist_embed(
        spec["playlist_id"],
        attribution=attribution,
        color=overrides.get("color", spec["color"]),
        height=overrides.get("height", spec["height"]),
        visual=overrides.get("visual", spec["visual"]),
        auto_play=auto_play,
    )


# ── GitHub README support ─────────────────────────────────────────────────────
# GitHub sanitizes HTML in Markdown — <iframe> is stripped, so a live player is
# impossible in a README. The accepted workaround is a clickable artwork/badge
# linking to SoundCloud. We render that as pure Markdown.
SOUNDCLOUD_BADGE = (
    "https://img.shields.io/badge/SoundCloud-Listen-ff5500"
    "?logo=soundcloud&logoColor=white&style=for-the-badge"
)


def readme_badge_md(set_url: str, label: str = "Listen on SoundCloud") -> str:
    """A shields.io SoundCloud badge linking to a set — safe for GitHub READMEs."""
    return f"[![{escape(label)}]({SOUNDCLOUD_BADGE})]({set_url})"


def readme_album_md(key: str, *, artwork_url: str = "") -> str:
    """A README block for a known album: heading, blurb, badge (+ optional artwork).

    ``artwork_url`` (e.g. the set's cover image) becomes a clickable thumbnail —
    the closest GitHub allows to an inline player.
    """
    spec = KNOWN_PLAYLISTS.get(key.strip().lower())
    if spec is None:
        raise KeyError(f"unknown album {key!r}; known: {sorted(KNOWN_PLAYLISTS)}")
    lines = [f"### 🎧 {spec['title']} — {ARTIST.author_name}", "", f"_{spec['blurb']}_", ""]
    if artwork_url:
        lines.append(f'<a href="{escape(spec["set_url"])}"><img src="{escape(artwork_url)}" '
                     f'alt="{escape(spec["title"])}" width="320"></a>')
        lines.append("")
    lines.append(readme_badge_md(spec["set_url"]))
    lines.append("")
    return "\n".join(lines)


# ── Pro player (m4r2d2-player.js) — Widget-API control bar, lazy facade, sticky ──
# These emit the *enhanced wrapper* the music4robots2dance2 player upgrades, plus
# a JSON config and a paste-anywhere DROP snippet — so AuthorAgent, the WP plugin,
# and the mindX app all produce the same player from one source of truth.

def _resolve_pro(album=None, *, url=None, playlist_id=None, track_id=None,
                 color=None, visual=None, height=None, title=None) -> dict:
    spec = KNOWN_PLAYLISTS.get((album or "").strip().lower()) if album else None
    if not (url or playlist_id or track_id) and spec is None:
        spec = KNOWN_PLAYLISTS[DEFAULT_ALBUM]  # zero-config → the highlights
    if url:
        resource = url
        def_h = HEIGHT_PLAYLIST if "/sets/" in url else HEIGHT_TRACK
    elif track_id:
        resource = track_resource_url(track_id)
        def_h = HEIGHT_TRACK
    elif playlist_id:
        resource = playlist_resource_url(playlist_id)
        def_h = HEIGHT_PLAYLIST
    else:
        resource = playlist_resource_url(spec["playlist_id"])
        def_h = spec["height"]
    return {
        "resource": resource,
        "color": _norm_color(color or (spec["color"] if spec else COLOR_DEFAULT)),
        "visual": visual if visual is not None else (spec["visual"] if spec else False),
        "height": int(height) if height else def_h,
        "title": title or (spec["title"] if spec else ""),
    }


def player_config(album: str | None = None, *, url=None, playlist_id=None, track_id=None,
                  color=None, visual=None, height=None, theme: str = "dark",
                  controls: bool = True, sticky: bool = False, lazy: bool = False,
                  autoplay: bool = False, story: str | None = ARTICLE_URL,
                  story_label: str = "▶ the story", title=None,
                  artist: str = ARTIST.author_name) -> dict[str, Any]:
    """JSON-serializable player config for the app (drive M4R2D2.drop / element)."""
    r = _resolve_pro(album, url=url, playlist_id=playlist_id, track_id=track_id,
                     color=color, visual=visual, height=height, title=title)
    src = build_player_url(r["resource"], color=r["color"], visual=r["visual"], auto_play=autoplay)
    return {
        "album": album or (None if (url or playlist_id or track_id) else DEFAULT_ALBUM),
        "resource": r["resource"], "src": src, "color": r["color"], "visual": r["visual"],
        "height": r["height"], "theme": "light" if theme == "light" else "dark",
        "controls": bool(controls), "sticky": bool(sticky), "lazy": bool(lazy),
        "autoplay": bool(autoplay), "story": story or "", "story_label": story_label,
        "title": r["title"], "artist": artist,
    }


def widget_player(album: str | None = None, **kwargs: Any) -> str:
    """Enhanced wrapper HTML the m4r2d2 player upgrades (control bar/facade/dock).

    Progressive enhancement: the iframe renders and plays without JS unless
    ``lazy=True``. Accepts the same kwargs as :func:`player_config`.
    """
    cfg = player_config(album, **kwargs)
    data = {
        "class": "m4r2d2-embed",
        "data-enhanced": "1",
        "data-theme": cfg["theme"],
        "data-controls": "true" if cfg["controls"] else "false",
        "data-sticky": "true" if cfg["sticky"] else "false",
        "data-lazy": "true" if cfg["lazy"] else "false",
        "data-autoplay": "true" if cfg["autoplay"] else "false",
        "data-title": cfg["title"],
        "data-artist": cfg["artist"],
        "data-story": cfg["story"],
        "data-story-label": cfg["story_label"],
        "data-src": cfg["src"],
        "data-height": str(cfg["height"]),
    }
    open_tag = "<div" + "".join(f' {k}="{escape(str(v), quote=True)}"' for k, v in data.items()) + ">"
    inner = ""
    if not cfg["lazy"]:
        inner = (
            f'<iframe class="m4r2d2__iframe" width="100%" height="{cfg["height"]}" '
            f'scrolling="no" frameborder="no" allow="autoplay; encrypted-media" loading="lazy" '
            f'title="{escape(cfg["title"], quote=True)}" src="{escape(cfg["src"], quote=True)}"></iframe>'
        )
    return open_tag + inner + "</div>"


def drop_snippet(asset_base_url: str, *, album: str = DEFAULT_ALBUM, sticky: bool = True,
                 theme: str = "dark", permission: str = "ask", defer: bool = True) -> str:
    """The shareable DROP: a single <script> that auto-installs the player.

    ``asset_base_url`` is the directory that serves ``m4r2d2-drop.js`` (a CDN like
    jsDelivr, the WP plugin's ``/assets``, or the mindX app). Minimal as possible.
    """
    base = asset_base_url.rstrip("/")
    attrs = {
        "src": f"{base}/m4r2d2-drop.js",
        "data-album": album, "data-sticky": "true" if sticky else "false",
        "data-theme": "light" if theme == "light" else "dark",
        "data-permission": permission,
    }
    s = "<script" + "".join(f' {k}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    if defer:
        s += " defer"
    return s + "></script>"


__all__ = [
    "PLAYER_BASE",
    "HEIGHT_TRACK",
    "HEIGHT_VISUAL",
    "HEIGHT_PLAYLIST",
    "COLOR_DEFAULT",
    "ARTICLE_URL",
    "DEFAULT_ALBUM",
    "Attribution",
    "ARTIST",
    "KNOWN_PLAYLISTS",
    "playlist_resource_url",
    "track_resource_url",
    "build_player_url",
    "embed",
    "playlist_embed",
    "track_embed",
    "embed_from_url",
    "album_embed",
    "player_config",
    "widget_player",
    "drop_snippet",
    "readme_badge_md",
    "readme_album_md",
    "SOUNDCLOUD_BADGE",
]
