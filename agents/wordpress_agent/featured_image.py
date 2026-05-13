# SPDX-License-Identifier: Apache-2.0
"""Featured-image rotation for wordpress.agent publishes.

Picks the best-fit graphic from /home/hacker/mindX/gfx/ for any article
based on title + tags + an optional explicit topic hint, then uploads it
to the wordpress.agent /media endpoint and returns the resulting WordPress
``media_id`` for use as ``featured_media`` on the next ``/publish`` call.

Two contracts:
  1. ``FeaturedImagePicker.pick()`` is pure; never raises; returns a Path
     under ``/home/hacker/mindX/gfx/`` (always one of the existing assets).
  2. ``attach_featured_image()`` is best-effort; on any failure (wordpress.agent
     down, WordPress 5xx, file unreadable) it logs a warning and returns None,
     so the calling ``publish_to_rage`` can proceed without a featured image
     rather than abort.

Topic → file mapping is curated, not heuristic. New mappings are a one-line
edit; the test suite ``tests/test_featured_image_picker.py`` pins the
existing assertions so nothing rotates by accident.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("wordpress_agent.featured_image")


GFX_ROOT = Path("/home/hacker/mindX/gfx")


# Topic keywords (lowercased, substring-matched against title + tags) →
# filename in GFX_ROOT. Order in the dict is the priority order for ties.
# The "default" key is the fallback when no keyword matches.
TOPIC_TO_FILE: dict[str, str] = {
    # Competition / governance / boardroom — the inaugural-article surface.
    "competition":      "war_council_gold.png",
    "competitive":      "war_council_gold.png",
    "boardroom":        "AgenticPlaceboardmeeting.jpeg",
    "council":          "war_council_global.png",
    "censura":          "war_council_global.png",
    "dojo":             "war_council_green.png",

    # Marketplace + distribution.
    "agenticplace":     "AgenticPlace.png",
    "marketplace":      "mysticalmarketplace.webp",
    "distribution":     "AgenticPlace1.png",

    # Identity + vault + BANKON.
    "bankon":           "bankonvault.png",
    "vault":            "bankonvault.png",
    "bonafide":         "BONAFIDE.png",
    "bona fide":        "BONAFIDE.png",
    "identity":         "BONAFIDE.png",

    # mindX self-references.
    "mindx":            "mindX.png",
    "self-healing":     "doorway2.webp",
    "self healing":     "doorway2.webp",
    "machine dreaming": "mysticalmarketplace.webp",
    "dream":            "mysticalmarketplace.webp",

    # Competitors / peers (positive framing).
    "openclaw":         "sevensoldiers.png",
    "hermes":           "sevensoldiers.png",
    "swarmclaw":        "sevensoldiers.png",
    "peers":            "sevensoldiers.png",

    # THOT / iNFT / cryptographic substrate.
    "thot":             "THOTH.png",
    "inft":             "THOTH.png",
    "merkle":           "THOTH.png",
    "matryoshka":       "THOTH.png",

    # Skills.
    "skill":            "doorway3.webp",
    "curator":          "doorway3.webp",
    "manifest":         "doorway3.webp",

    # Shadow-overlord / privileged paths.
    "shadow-overlord":  "shadow_overlord.png",
    "shadow overlord":  "shadow_overlord.png",

    # Generic fallback.
    "default":          "doorway1.webp",
}


class FeaturedImagePicker:
    """Curated rotation over /home/hacker/mindX/gfx/ assets.

    Maps article topics to on-brand featured images. Falls back to
    ``doorway1.webp`` when nothing matches. Never raises.
    """

    def __init__(self, gfx_root: Optional[Path] = None,
                 topic_map: Optional[dict[str, str]] = None):
        self.gfx_root = Path(gfx_root) if gfx_root is not None else GFX_ROOT
        self.topic_map = dict(topic_map) if topic_map is not None else dict(TOPIC_TO_FILE)

    def pick(
        self,
        *,
        title: str = "",
        tags: Optional[list[str]] = None,
        topic: Optional[str] = None,
    ) -> Path:
        """Pick the best-fit image. Search order:

          1. Explicit ``topic`` keyword (lowercased + stripped) in the map.
          2. Any keyword in the map that appears as a substring of the
             title or any tag (case-insensitive). First match in dict
             order wins.
          3. The ``default`` entry (doorway1.webp).

        Always returns a Path that exists under ``self.gfx_root``. If the
        mapped file is missing on disk (e.g. asset rotated out), falls
        back to the first existing doorway*.webp/png in the root.
        """
        # Mode 1: explicit topic.
        if topic:
            key = topic.strip().lower()
            if key in self.topic_map:
                p = self._resolve(self.topic_map[key])
                if p is not None:
                    return p

        # Mode 2: keyword scan over title + tags.
        haystack = " ".join(
            ((title or "").lower(),) + tuple((t or "").lower() for t in (tags or []))
        )
        for keyword, filename in self.topic_map.items():
            if keyword == "default":
                continue
            if keyword in haystack:
                p = self._resolve(filename)
                if p is not None:
                    return p

        # Mode 3: default fallback.
        return self._resolve(self.topic_map["default"]) or self._first_doorway()

    def _resolve(self, filename: str) -> Optional[Path]:
        """Return the Path if the file exists under gfx_root, else None."""
        p = self.gfx_root / filename
        return p if p.exists() else None

    def _first_doorway(self) -> Path:
        """Hard fallback: the first doorway* asset that exists, regardless
        of extension. Returns gfx_root itself only if no doorway exists
        (which means the gfx tree is broken — caller can decide what to
        do with that)."""
        for stem in ("doorway1", "doorway2", "doorway3", "doorway4", "doorway5"):
            for ext in (".webp", ".png", ".jpeg", ".jpg"):
                p = self.gfx_root / f"{stem}{ext}"
                if p.exists():
                    return p
        return self.gfx_root


# ─── Upload helper ──────────────────────────────────────────────────


async def attach_featured_image(
    wp_agent_url: str,
    image_path: Path,
    alt_text: str,
    *,
    caption: Optional[str] = None,
    title: Optional[str] = None,
    timeout_s: float = 30.0,
) -> Optional[int]:
    """POST the image to wordpress.agent's ``/media`` endpoint.

    Returns the WordPress ``media_id`` on success, or ``None`` on any
    failure (logged warning). Caller can then pass the id as
    ``featured_media`` to the subsequent ``/publish`` call.

    Args:
        wp_agent_url:  Base URL of wordpress.agent, e.g. ``http://127.0.0.1:8765``.
        image_path:    Path to a real image file on local disk.
        alt_text:      Required for SEO + accessibility.
        caption:       Optional WordPress caption.
        title:         Optional WordPress media title (defaults to filename).
        timeout_s:     HTTP timeout.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning("featured_image: %s missing on disk", image_path)
        return None

    url = wp_agent_url.rstrip("/") + "/media"
    try:
        content_type = _content_type_for(image_path)
        with open(image_path, "rb") as fh:
            data = fh.read()

        files = {"file": (image_path.name, data, content_type)}
        form: dict[str, str] = {"alt_text": alt_text}
        if caption:
            form["caption"] = caption
        if title:
            form["title"] = title

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, files=files, data=form)
            resp.raise_for_status()
            body = resp.json()

        media_id = body.get("media_id") or body.get("id")
        if not isinstance(media_id, int):
            logger.warning(
                "featured_image: unexpected media response shape %r", body
            )
            return None
        return media_id
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning(
            "featured_image: upload of %s failed: %s", image_path.name, exc
        )
        return None


def _content_type_for(path: Path) -> str:
    """Map common image extensions to their MIME types."""
    ext = path.suffix.lower()
    return {
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif":  "image/gif",
        ".svg":  "image/svg+xml",
    }.get(ext, "application/octet-stream")


__all__ = [
    "GFX_ROOT",
    "TOPIC_TO_FILE",
    "FeaturedImagePicker",
    "attach_featured_image",
]
