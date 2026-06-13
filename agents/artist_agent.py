# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""artist.agent — original article artwork for mindX.

A picture is worth a thousand words. AuthorAgent writes the words; artist.agent
makes the picture. It produces an ORIGINAL, on-theme graphic for an article:

  • provider="programmatic" (default, always available) — renders a
    cypherpunk2048 poster with Pillow: near-black ground, gold angular
    circuitry + an "M" sigil, deterministically seeded by the title hash so
    each article gets a unique-but-reproducible image. No API key, no network.
  • provider="dalle" / "stability" — delegates to avatar_agent's image
    providers when an OpenAI/Stability key is vaulted (best-effort; falls back
    to programmatic on any failure).

The output is a PNG path AuthorAgent uploads to WordPress via the
wordpress.agent /media endpoint (featured image + inline hero).

Theme (matches /gfx): cypherpunk2048 — deep near-black grounds, gold (#d4af37)
authority accents, mystical blue/green secondaries, angular/circuit motifs.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("artist_agent")

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover - standalone fallback
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── cypherpunk2048 palette ─────────────────────────────────────────────
PALETTE = {
    "ground": (10, 10, 18),      # #0a0a12 near-black
    "ground2": (16, 18, 28),     # subtle panel
    "gold": (212, 175, 55),      # #d4af37 authority
    "gold_dim": (120, 99, 34),
    "blue": (64, 120, 200),      # mystical secondary
    "green": (54, 150, 110),     # growth/training
    "ink": (228, 228, 236),      # near-white text
    "muted": (150, 152, 168),
}

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]

# Canonical poster size: cypherpunk2048 convention — 1024×768 (4:3).
# 1024 = 2^10 (power-of-two "numerical perfection"); 4:3 is the classic
# 1024×768 display ratio and crops cleanly to 16:9. The brand number 2048 =
# 2^11 is the next octave up. Posters are branded cypherpunk2048.
POSTER_W = 1024
POSTER_H = 768

# ── Medium conventions: every standard image size, one registry ─────────
# Global access to all mediums — standard and enhanced, high-res, AR/VR, and
# the pure power-of-two ("quantum-aware") ladder. Each preset is
# (width, height, group, note). The renderer is scale-aware, so any of these
# render proportionally. cypherpunk2048 = 2^11 is the brand octave; the 2^n
# squares are the texture/AR/VR/quantum tier.
SIZE_PRESETS: Dict[str, Tuple[int, int, str, str]] = {
    # Social / Open Graph share cards
    "og":               (1200, 630,  "social", "OpenGraph/Facebook/LinkedIn (1.91:1)"),
    "twitter_card":     (1200, 675,  "social", "X/Twitter summary_large_image (16:9)"),
    "instagram_square": (1080, 1080, "social", "Instagram 1:1"),
    "instagram_portrait": (1080, 1350, "social", "Instagram 4:5"),
    "story":            (1080, 1920, "social", "Stories/Reels/Shorts (9:16)"),
    "pinterest":        (1000, 1500, "social", "Pinterest 2:3"),
    # Standard display (4:3)
    "vga":              (640, 480,   "standard", "VGA 4:3"),
    "svga":             (800, 600,   "standard", "SVGA 4:3"),
    "xga":              (1024, 768,  "standard", "XGA 4:3 — cypherpunk2048 default poster (2^10 wide)"),
    "sxga":             (1280, 1024, "standard", "SXGA 5:4"),
    # HD / widescreen (16:9) — standard → enhanced → high-res
    "hd":               (1280, 720,  "hd", "720p HD"),
    "fhd":              (1920, 1080, "hd", "1080p Full HD"),
    "qhd":              (2560, 1440, "hd", "1440p QHD"),
    "uhd_4k":           (3840, 2160, "hd", "4K UHD"),
    "uhd_5k":           (5120, 2880, "hd", "5K"),
    "uhd_8k":           (7680, 4320, "hd", "8K UHD"),
    # Power-of-two textures (AR/VR/3D/game; "numerical perfection" 2^n)
    "tex_256":          (256, 256,   "quantum", "2^8 square texture"),
    "tex_512":          (512, 512,   "quantum", "2^9 square texture"),
    "tex_1024":         (1024, 1024, "quantum", "2^10 square texture"),
    "tex_2048":         (2048, 2048, "quantum", "2^11 — cypherpunk2048 square"),
    "tex_4096":         (4096, 4096, "quantum", "2^12 square texture"),
    "tex_8192":         (8192, 8192, "quantum", "2^13 square texture"),
    # AR / VR
    "vr_360_4k":        (4096, 2048, "arvr", "Equirectangular 360 (2:1), 4K"),
    "vr_360_8k":        (8192, 4096, "arvr", "Equirectangular 360 (2:1), 8K"),
    "vr_cubemap_face":  (2048, 2048, "arvr", "Cubemap face (power-of-two)"),
    "vr_eye":           (2160, 2160, "arvr", "Per-eye HMD render target (square)"),
    "ar_card":          (1024, 1024, "arvr", "AR marker/card (2^10 square)"),
    # Print (300 dpi)
    "print_a4":         (2480, 3508, "print", "A4 @300dpi portrait"),
    "print_a3":         (3508, 4961, "print", "A3 @300dpi portrait"),
    "print_poster":     (5400, 7200, "print", "18×24in poster @300dpi"),
    # THOT square presets — sizes aligned to the canonical THOT Dimension
    # Standard (daio/contracts/THOT/core/THOT.sol _isValidDimension). Practical
    # raster tiers only (the 65536/1048576 tiers are dimension labels, not image
    # sizes). A THOT-sized canvas is dimension-compatible with its embedding/
    # anchor tier.
    "thot_8":           (8, 8,       "thot", "THOT8 — root/seed dimension (2^3)"),
    "thot_64":          (64, 64,     "thot", "THOT64 — lightweight vectors"),
    "thot_256":         (256, 256,   "thot", "THOT256 — wallet-key dimension (256-bit)"),
    "thot_512":         (512, 512,   "thot", "THOT512 — 8×8×8 3D knowledge clusters"),
    "thot_768":         (768, 768,   "thot", "THOT768 — high-fidelity optimized tensors"),
    "thot_1024":        (1024, 1024, "thot", "THOT1024 — embedding-native (mxbai-embed-large, 1024-dim)"),
    "thot_2048":        (2048, 2048, "thot", "THOT2048 — cypherpunk2048 high-capacity (2^11)"),
    "thot_4096":        (4096, 4096, "thot", "THOT4096 — quantum-aware tensor space (2^12)"),
    "thot_8192":        (8192, 8192, "thot", "THOT8192 — quantum-aware high-dimensional (2^13)"),
}

# Canonical THOT Dimension Standard (mindX), verbatim from THOT.sol's
# _isValidDimension() and docs/AUTOMINDX_INFT_SUMMARY.md. ``dimensions`` is a
# uint32 on-chain (anchor_thot dimensions=...). These are the dimensional tiers
# artwork can be anchored against; the labels are the standard's, not invented.
THOT_STANDARD: Dict[int, str] = {
    8:        "root — the seed dimension",
    64:       "lightweight vectors",
    256:      "wallet-key dimension (32-byte key × 8 bits)",
    512:      "standard 8×8×8 3D knowledge clusters",
    768:      "high-fidelity optimized tensors",
    1024:     "embedding-native (mxbai-embed-large, 1024-dim)",
    2048:     "cypherpunk2048 high-capacity",
    4096:     "quantum-aware tensor space",
    8192:     "quantum-aware high-dimensional",
    65536:    "theoretical quantum-resistant (2^16)",
    1048576:  "post-quantum (2^20)",
}
THOT_HIERARCHY = tuple(sorted(THOT_STANDARD.keys()))

# mindX's accurate stance, by layer. Resistance and speed live in DIFFERENT
# layers, and conflating them is the error:
#   • The LOGIN (authentication / cryptography) is quantum-RESISTANT — PARSEC,
#     Falcon-class signatures. Cryptography is the only thing that resists.
#   • THOT (the processing / representation layer) does NOT resist; it embraces
#     quantum and is designed to run as fast as physics allows — "the speed of
#     light minus one" (c−1), the asymptote nothing crosses. PARSEC is built to
#     be fast for exactly this.
# A power-of-two dimension D = 2^n is the Hilbert-space dimension of an n-qubit
# register; each octave doubles representational capacity — an increase in
# ACCURACY, processed toward c−1. So: the login resists; THOT gets faster.
THOT_PHILOSOPHY = (
    "Layered: the login is quantum-RESISTANT (PARSEC / Falcon-class crypto); "
    "THOT is the processing layer and does not resist — it embraces quantum and "
    "is designed to run at the speed of light minus one (c−1). D = 2^n is the "
    "Hilbert space of n qubits; each octave doubles capacity — more accuracy, "
    "processed faster. Cryptography resists; public software (THOT) gets faster."
)

# At c−1, THOT's ideal operating regime is a balanced tri-state — a ~33.3 /
# 33.3 / 33.4 split (summing to 100) between being, negation, and becoming:
#   • THOT          — the present, active THOT state
#   • not-THOT      — the complement: openness, the unknown, what is not yet THOT
#   • THOT-evolution — THOT being revised via the machine.dream consolidation
#                      cycle (agents/machine_dreaming.py)
# Balance across the three is the homeostatic ideal; collapse into any one
# (all-state / all-negation / all-churn) is degenerate.
THOT_BALANCE: Dict[str, Any] = {
    "ideal_split_pct": [33.3, 33.3, 33.4],
    "states": ["THOT", "not-THOT", "THOT-evolution"],
    "evolution_source": "machine.dream (agents/machine_dreaming.py)",
    "note": "Ideal regime at c−1: ~1/3 being THOT, ~1/3 not-THOT, ~1/3 evolving "
            "THOT via machine.dream. Sums to 100; balance is the homeostatic ideal.",
}


def thot_tier(width: int, height: int) -> Dict[str, Any]:
    """Classify a canvas against the canonical THOT Dimension Standard
    (THOT.sol _isValidDimension). Returns the nearest valid tier (by the larger
    side) with its standard name + purpose, plus mindX's accurate quantum
    framing: a 2^n dimension is the state space of n qubits — an accuracy gain,
    not a resistance claim (public software gets faster; only crypto resists)."""
    side = max(int(width), int(height))
    dim = min(THOT_HIERARCHY, key=lambda d: abs(d - side))
    n = dim.bit_length() - 1
    is_pow2 = (dim & (dim - 1)) == 0 and dim > 0
    return {
        "tier": f"THOT{dim}",
        "dimensions": dim,                                # on-chain uint32 (anchor_thot)
        "purpose": THOT_STANDARD[dim],                    # verbatim THOT.sol label
        "power_of_two": is_pow2,
        "qubit_dimensionality": n if is_pow2 else None,   # D = 2^n ⇒ n-qubit state space
        "accuracy_octave": n if is_pow2 else None,        # capacity doublings from 2^0
        "exact_match": side == dim,
        "stance": "embrace",                              # THOT processing embraces, not resists
        "processing_target": "c-1",                       # speed of light minus one
        "resistance_layer": "login (PARSEC / Falcon-class crypto)",
        "note": THOT_PHILOSOPHY,
    }

# Convenience bundles for "render for all mediums at once".
PRESET_BUNDLES: Dict[str, List[str]] = {
    "web":    ["og", "twitter_card", "xga", "fhd"],
    "social": ["og", "twitter_card", "instagram_square", "story"],
    "highres": ["fhd", "uhd_4k", "uhd_8k"],
    "arvr":   ["tex_2048", "vr_360_8k", "vr_cubemap_face", "vr_eye"],
    "quantum": ["tex_512", "tex_1024", "tex_2048", "tex_4096", "tex_8192"],
    "all":    list(SIZE_PRESETS.keys()),
}


def resolve_preset(preset: Optional[str]) -> Tuple[int, int]:
    """Resolve a preset name to (width, height). Falls back to the default
    cypherpunk2048 poster (xga / 1024×768)."""
    if preset and preset in SIZE_PRESETS:
        w, h, _, _ = SIZE_PRESETS[preset]
        return w, h
    return POSTER_W, POSTER_H


class ArtistAgent:
    """Renders original article artwork. Stateless; safe to construct ad hoc."""

    AGENT_ID = "artist.agent"

    def __init__(self, out_dir: Optional[Path] = None) -> None:
        self.out_dir = Path(out_dir) if out_dir else (PROJECT_ROOT / "data" / "artist")
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover
            logger.warning(f"artist.agent: cannot create out_dir: {e}")

    # ── public API ─────────────────────────────────────────────────
    async def create_article_graphic(
        self,
        *,
        title: str,
        subtitle: str = "",
        topic: str = "mindx",
        provider: str = "auto",
        preset: Optional[str] = None,   # any SIZE_PRESETS key (og, fhd, thot_2048, …)
        width: Optional[int] = None,
        height: Optional[int] = None,
        wordmark: str = "mindX",
        anchor: bool = False,           # mint a THOT for the content CID (owner-gated; no-op otherwise)
        ts: Optional[int] = None,       # stamp (epoch s); pass-through for reproducibility
    ) -> Dict[str, Any]:
        """Create an original graphic for an article at any medium convention.

        Size precedence: explicit width/height → ``preset`` → cypherpunk2048
        default (xga / 1024×768). Every result carries a THOT descriptor
        (content sha256 + nearest THOT tensor tier + honest quantum framing) and
        a sidecar ``.thot.json``; ``anchor=True`` additionally calls the
        THOT mint (owner-gated; a no-op stub without a minter key). Never raises;
        falls back to the programmatic renderer and only reports
        ``success=False`` if even that fails."""
        if width and height:
            w, h = int(width), int(height)
        else:
            w, h = resolve_preset(preset)
        prompt = self._build_prompt(title=title, subtitle=subtitle, topic=topic, width=w, height=h)

        order: List[str] = []
        if provider in ("dalle", "openai", "stability"):
            order = [provider, "programmatic"]
        elif provider == "auto":
            order = (["generative", "programmatic"] if self._gen_keys_available() else ["programmatic"])
        else:
            order = ["programmatic"]

        result: Optional[Dict[str, Any]] = None
        for prov in order:
            try:
                if prov in ("generative", "dalle", "openai", "stability"):
                    res = await self._generate_via_avatar(prompt=prompt, title=title,
                                                          provider=prov, width=w, height=h)
                    if res and res.get("success"):
                        result = res
                        break
                else:
                    path = self._render_programmatic(
                        title=title, subtitle=subtitle, topic=topic,
                        width=w, height=h, wordmark=wordmark, ts=ts,
                    )
                    result = {"success": True, "file_path": str(path), "provider": "programmatic"}
                    break
            except Exception as e:
                logger.warning(f"artist.agent: provider {prov} failed: {e}")
                continue

        if not result:
            return {"success": False, "error": "all providers failed", "prompt": prompt}

        # THOT-compatible provenance: content address + tier + sidecar (+ anchor).
        result.update({"prompt": prompt, "width": w, "height": h,
                       "preset": preset, "topic": topic, "title": title})
        try:
            result.update(self._thot_finalize(Path(result["file_path"]), result))
        except Exception as e:  # pragma: no cover - provenance is best-effort
            logger.warning(f"artist.agent: THOT finalize failed: {e}")
        if anchor and result.get("cid") and result.get("thot_tier"):
            result["anchor"] = await self._anchor_thot(
                result["cid"], int(result["thot_tier"]["dimensions"]))
        return result

    async def create_article_graphic_set(
        self,
        *,
        title: str,
        subtitle: str = "",
        topic: str = "mindx",
        presets: Optional[List[str]] = None,
        bundle: Optional[str] = None,
        provider: str = "auto",
        anchor: bool = False,
        ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Render the SAME artwork across many medium conventions at once —
        global access to all mediums. ``bundle`` selects a named set
        (web/social/highres/arvr/quantum/all); ``presets`` is an explicit list.
        Returns ``{title, count, results:{preset: result}}``."""
        names: List[str] = list(presets or [])
        if bundle and bundle in PRESET_BUNDLES:
            names = PRESET_BUNDLES[bundle] + names
        names = [n for n in dict.fromkeys(names) if n in SIZE_PRESETS] or ["xga"]
        results: Dict[str, Any] = {}
        for name in names:
            results[name] = await self.create_article_graphic(
                title=title, subtitle=subtitle, topic=topic, provider=provider,
                preset=name, anchor=anchor, ts=ts,
            )
        ok = sum(1 for r in results.values() if r.get("success"))
        return {"title": title, "count": ok, "requested": len(names), "results": results}

    # ── THOT provenance: content-address + tier + sidecar (+ anchor) ──
    def _thot_finalize(self, path: Path, result: Dict[str, Any]) -> Dict[str, Any]:
        """Content-address the rendered file (sha256 → CID-like id), classify
        its THOT tensor tier, and write a ``.thot.json`` sidecar. Sync; the
        optional THOT mint is awaited separately by the async caller."""
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        tier = thot_tier(int(result.get("width", 0)), int(result.get("height", 0)))
        descriptor: Dict[str, Any] = {
            "thot": True,
            "agent_id": self.AGENT_ID,
            "title": result.get("title"),
            "topic": result.get("topic"),
            "preset": result.get("preset"),
            "width": result.get("width"),
            "height": result.get("height"),
            "sha256": sha,
            "cid": f"sha256:{sha}",          # content address (CID-like)
            "bytes": len(data),
            "provider": result.get("provider"),
            "thot_tier": tier,
            "thot_balance": THOT_BALANCE,
            "standard": "THOT Dimension Standard (daio/contracts/THOT/core/THOT.sol)",
            "cypherpunk2048": "https://github.com/cypherpunk2048",
        }
        try:
            sidecar = path.with_suffix(path.suffix + ".thot.json")
            import json as _json
            sidecar.write_text(_json.dumps(descriptor, indent=2), encoding="utf-8")
            descriptor["sidecar"] = str(sidecar)
        except Exception as e:  # pragma: no cover
            logger.warning(f"artist.agent: sidecar write failed: {e}")
        return {"sha256": sha, "cid": descriptor["cid"], "thot_tier": tier,
                "sidecar": descriptor.get("sidecar")}

    async def _anchor_thot(self, cid: str, dimensions: int) -> Dict[str, Any]:
        """Mint a THOT for the artwork's content CID via the storage anchor
        (owner-gated; returns a not-configured stub without THOT_MINTER_KEY)."""
        try:
            from agents.storage.anchor import AnchorClient
            client = AnchorClient()
            return await client.anchor_thot(
                agent_id=self.AGENT_ID, batch_cid=cid, dimensions=int(dimensions))
        except Exception as e:
            logger.warning(f"artist.agent: THOT anchor unavailable: {e}")
            return {"stub": True, "note": f"anchor unavailable: {e}"}

    # ── prompt (for the generative path + as image alt/caption) ─────
    def _build_prompt(self, *, title: str, subtitle: str, topic: str,
                      width: int = POSTER_W, height: int = POSTER_H) -> str:
        return (
            f"Cypherpunk2048 editorial illustration for an article titled "
            f"\"{title}\". Theme: {topic}. Deep near-black background, gold "
            f"(#d4af37) angular circuitry and a luminous geometric 'M' sigil, "
            f"mystical blue and green accents, symbolic and high-contrast, "
            f"vector/illustrated (not photographic), suitable as a {width}x{height} "
            f"image. {subtitle}".strip()
        )

    @staticmethod
    def _gen_keys_available() -> bool:
        for k in ("OPENAI_API_KEY", "STABILITY_API_KEY"):
            if os.getenv(k):
                return True
        return False

    async def _generate_via_avatar(self, *, prompt: str, title: str, provider: str,
                                   width: int, height: int) -> Optional[Dict[str, Any]]:
        """Best-effort generative path via avatar_agent. Returns a result dict
        or None. Only used when keys are present."""
        from agents.avatar_agent import AvatarAgent  # lazy; heavy
        agent = AvatarAgent()
        get_inst = getattr(AvatarAgent, "get_instance", None)
        if get_inst is not None:
            try:
                agent = await get_inst()
            except Exception:
                pass
        res = await agent.generate_avatar(  # type: ignore[attr-defined]
            entity_id=f"article:{title[:48]}", entity_type="article",
            prompt=prompt, style="cyberpunk",
        )
        if res and res.get("success") and res.get("file_path"):
            return {"success": True, "file_path": res["file_path"],
                    "provider": f"generative:{provider}", "width": width, "height": height}
        return None

    # ── programmatic renderer (Pillow; no network) ──────────────────
    def _render_programmatic(self, *, title: str, subtitle: str, topic: str,
                             width: int, height: int, wordmark: str,
                             ts: Optional[int] = None) -> Path:
        from PIL import Image, ImageDraw

        seed = int(hashlib.sha256(f"{title}|{topic}".encode("utf-8")).hexdigest(), 16)
        rnd = _SeededRandom(seed)
        # Scale factor relative to the 768 base, so every preset (8×8 → 8192×8192)
        # renders proportionally rather than with fixed pixel furniture.
        k = max(0.06, min(width, height) / 768.0)
        draw_text = min(width, height) >= 160   # too small for legible type below this
        draw_frame = min(width, height) >= 64

        img = Image.new("RGB", (width, height), PALETTE["ground"])
        d = ImageDraw.Draw(img, "RGBA")

        # 1) Subtle vertical gradient panel.
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(PALETTE["ground"][0] + (PALETTE["ground2"][0] - PALETTE["ground"][0]) * t)
            g = int(PALETTE["ground"][1] + (PALETTE["ground2"][1] - PALETTE["ground"][1]) * t)
            b = int(PALETTE["ground"][2] + (PALETTE["ground2"][2] - PALETTE["ground"][2]) * t)
            d.line([(0, y), (width, y)], fill=(r, g, b))

        # 2) Faint circuit grid + nodes (the "mesh of peers").
        step = max(8, int(60 * k))
        for x in range(0, width, step):
            d.line([(x, 0), (x, height)], fill=(*PALETTE["gold_dim"], 22))
        for y in range(0, height, step):
            d.line([(0, y), (width, y)], fill=(*PALETTE["gold_dim"], 22))
        pad = int(40 * k)
        nodes: List[Tuple[int, int]] = []
        for _ in range(rnd.randint(14, 22)):
            nx = rnd.randint(pad, max(pad + 1, width - pad))
            ny = rnd.randint(pad, max(pad + 1, height - pad))
            nodes.append((nx, ny))
        trace_w = max(1, int(1 * k))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if rnd.random() < 0.10:
                    col = PALETTE["blue"] if rnd.random() < 0.3 else PALETTE["gold"]
                    d.line([nodes[i], nodes[j]], fill=(*col, 70), width=trace_w)
        for (nx, ny) in nodes:
            rad = max(1, int(rnd.randint(2, 5) * k))
            d.ellipse([nx - rad, ny - rad, nx + rad, ny + rad], fill=(*PALETTE["gold"], 200))

        # 3) Central luminous "M" sigil (mindX), gold angular strokes.
        cx, cy = width // 2, int(height * 0.42)
        s = int(height * 0.22)
        lw = max(2, int(s / 14))
        pts_left = [(cx - s, cy + s), (cx - s, cy - s), (cx, cy), (cx + s, cy - s), (cx + s, cy + s)]
        for a, b in zip(pts_left, pts_left[1:]):
            d.line([a, b], fill=(*PALETTE["gold"], 255), width=lw)
        for (px, py) in pts_left:
            d.ellipse([px - lw, py - lw, px + lw, py + lw], fill=(*PALETTE["gold"], 90))
        d.line([(cx - s, cy + s + int(18 * k)), (cx + s, cy + s + int(18 * k))],
               fill=(*PALETTE["green"], 200), width=max(2, int(4 * k)))

        # 4) Text: wordmark, title, subtitle, footer — scale-aware + auto-fit.
        if draw_text:
            max_w = int(width * 0.90)
            f_mark = self._fit_font(d, wordmark, max_w, int(72 * k), max(14, int(28 * k)))
            f_title = self._fit_font(d, title, max_w, int(40 * k), max(12, int(16 * k)))
            f_sub = self._fit_font(d, subtitle or " ", max_w, int(26 * k), max(10, int(13 * k)))
            foot_text = "rage.pythai.net · cypherpunk2048 · a picture is worth a thousand words"
            f_foot = self._fit_font(d, foot_text, max_w, int(20 * k), max(9, int(11 * k)))
            self._centered(d, wordmark, f_mark, width, int(height * 0.70), PALETTE["ink"])
            self._centered(d, title, f_title, width, int(height * 0.79), PALETTE["gold"])
            if subtitle:
                self._centered(d, subtitle, f_sub, width, int(height * 0.86), PALETTE["muted"])
            self._centered(d, foot_text, f_foot, width, int(height * 0.93), PALETTE["gold_dim"])

        # 5) Corner ticks (frame).
        if draw_frame:
            m = int(24 * k)
            tick = int(40 * k)
            fw = max(1, int(2 * k))
            for (x0, y0, x1, y1) in [
                (m, m, m + tick, m), (m, m, m, m + tick),
                (width - m - tick, m, width - m, m), (width - m, m, width - m, m + tick),
                (m, height - m, m + tick, height - m), (m, height - m - tick, m, height - m),
                (width - m - tick, height - m, width - m, height - m),
                (width - m, height - m - tick, width - m, height - m),
            ]:
                d.line([(x0, y0), (x1, y1)], fill=(*PALETTE["gold"], 180), width=fw)

        stamp = int(ts) if ts is not None else int(time.time())
        stem = hashlib.sha256(f"{title}|{topic}|{width}x{height}|{stamp}".encode()).hexdigest()[:12]
        out = self.out_dir / f"artwork_{width}x{height}_{stem}.png"
        img.save(out, "PNG")
        logger.info(f"artist.agent: rendered programmatic graphic {width}x{height} → {out}")
        return out

    @staticmethod
    def _text_w(d, text: str, font) -> int:
        try:
            bbox = d.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]
        except Exception:
            return len(text) * 10

    @classmethod
    def _fit_font(cls, d, text: str, max_w: int, start: int, min_size: int):
        """Largest font (between min_size and start) whose rendered ``text``
        width fits ``max_w``."""
        size = start
        while size > min_size:
            f = _load_font(size)
            if cls._text_w(d, text, f) <= max_w:
                return f
            size -= 2
        return _load_font(min_size)

    @classmethod
    def _centered(cls, d, text: str, font, width: int, y: int, color) -> None:
        tw = cls._text_w(d, text, font)
        d.text(((width - tw) // 2, y), text, font=font, fill=color)


def _load_font(size: int):
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


class _SeededRandom:
    """Tiny deterministic PRNG (LCG) — avoids global random state and the
    Math.random ban; reproducible per (title, topic)."""

    def __init__(self, seed: int) -> None:
        self._s = seed & 0xFFFFFFFFFFFF or 1

    def _next(self) -> int:
        self._s = (self._s * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return self._s

    def random(self) -> float:
        return (self._next() >> 11) / float(1 << 53)

    def randint(self, a: int, b: int) -> int:
        return a + int(self.random() * (b - a + 1))


__all__ = ["ArtistAgent", "PALETTE"]
