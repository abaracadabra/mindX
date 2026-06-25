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
    "ground": (8, 9, 14),        # #08090e deeper near-black (more contrast)
    "ground2": (18, 20, 32),     # subtle panel
    "ground3": (26, 30, 46),     # raised panel / brand bar
    "gold": (212, 175, 55),      # #d4af37 authority
    "gold_bright": (240, 208, 110),  # specular highlight on the mark
    "gold_dim": (120, 99, 34),
    "blue": (64, 120, 200),      # mystical secondary
    "blue_dim": (40, 70, 120),
    "green": (54, 150, 110),     # growth/training
    "ink": (232, 233, 240),      # near-white text
    "muted": (158, 160, 178),
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
            f"Corporate cypherpunk2048 brand poster for an article titled "
            f"\"{title}\". Theme: {topic}. A premium, editorial tech-brand "
            f"identity — NOT busy fan art. Deep near-black ground with a soft "
            f"diagonal gold spotlight and a subtle radial vignette for depth. "
            f"Centerpiece: a polished gold (#d4af37) hexagonal logomark housing a "
            f"luminous geometric 'M' sigil with a fine specular highlight, set on "
            f"an orderly Manhattan-routed circuit lattice (right-angle gold traces, "
            f"glowing nodes), restrained mystical blue and green accents. Strong "
            f"typographic hierarchy: a letter-spaced uppercase eyebrow label, a "
            f"bold near-white headline, a muted subtitle, and a corporate brand bar "
            f"along the bottom with the 'mindX' wordmark (gold X) and "
            f"'rage.pythai.net · cypherpunk2048'. Clean grid, generous negative "
            f"space, high contrast, flat vector/illustrated (not photographic), "
            f"corner bracket frame. Suitable as a {width}x{height} image. "
            f"{subtitle}".strip()
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
        from PIL import Image, ImageDraw, ImageFilter

        seed = int(hashlib.sha256(f"{title}|{topic}".encode("utf-8")).hexdigest(), 16)
        rnd = _SeededRandom(seed)
        # Scale factor relative to the 768 base, so every preset (8×8 → 8192×8192)
        # renders proportionally rather than with fixed pixel furniture.
        k = max(0.06, min(width, height) / 768.0)
        draw_text = min(width, height) >= 160   # too small for legible type below this
        draw_frame = min(width, height) >= 64

        img = Image.new("RGB", (width, height), PALETTE["ground"])
        d = ImageDraw.Draw(img, "RGBA")

        # 1) Ground: vertical gradient + a diagonal gold "beam" duotone wash for
        #    depth, then a radial vignette darkening the edges to focus the mark.
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(PALETTE["ground"][0] + (PALETTE["ground2"][0] - PALETTE["ground"][0]) * t)
            g = int(PALETTE["ground"][1] + (PALETTE["ground2"][1] - PALETTE["ground"][1]) * t)
            b = int(PALETTE["ground"][2] + (PALETTE["ground2"][2] - PALETTE["ground"][2]) * t)
            d.line([(0, y), (width, y)], fill=(r, g, b))
        self._beam_wash(img, width, height)
        self._vignette(img, width, height)
        self._scanlines(img, width, height, k)   # subtle printed/CRT texture
        d = ImageDraw.Draw(img, "RGBA")  # re-bind after composite

        # 2) Engineering grid + Manhattan-routed circuitry (orderly, corporate
        #    tech — right-angle traces, not a random web), nodes with halos.
        step = max(8, int(64 * k))
        for x in range(0, width, step):
            d.line([(x, 0), (x, height)], fill=(*PALETTE["gold_dim"], 16))
        for y in range(0, height, step):
            d.line([(0, y), (width, y)], fill=(*PALETTE["gold_dim"], 16))
        pad = int(44 * k)
        nodes: List[Tuple[int, int]] = []
        for _ in range(rnd.randint(16, 24)):
            nx = rnd.randint(pad, max(pad + 1, width - pad))
            ny = rnd.randint(pad, max(pad + 1, height - pad))
            nodes.append((nx, ny))
        trace_w = max(1, int(1.4 * k))
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if rnd.random() < 0.085:
                    col = PALETTE["blue"] if rnd.random() < 0.35 else PALETTE["gold"]
                    self._route_manhattan(d, nodes[i], nodes[j], col, trace_w, rnd)
        for (nx, ny) in nodes:
            rad = max(1, int(rnd.randint(2, 4) * k))
            d.ellipse([nx - rad * 3, ny - rad * 3, nx + rad * 3, ny + rad * 3],
                      fill=(*PALETTE["gold"], 26))  # halo
            d.ellipse([nx - rad, ny - rad, nx + rad, ny + rad], fill=(*PALETTE["gold"], 210))

        # 3) Brand emblem: a gold hexagon housing a refined, glowing "M" sigil —
        #    a corporate logomark rather than a bare polyline.
        cx, cy = width // 2, int(height * 0.35)
        self._emblem(img, d, cx, cy, int(height * 0.165), k)

        # 3b) Top masthead rail — a tiny wordmark + topic chip on a hairline,
        #     framing the poster like a publication masthead.
        if draw_text:
            self._masthead(d, width, height, wordmark, topic, k)

        # 4) Type system: badge kicker → title (wrapped, shadowed) → subtitle,
        #    all on a centered baseline grid. Corporate brand bar pinned bottom.
        if draw_text:
            max_w = int(width * 0.84)
            kicker = (topic or "mindX").upper()
            f_kick = self._fit_font(d, kicker, max_w, int(20 * k), max(9, int(12 * k)))
            ky = int(height * 0.605)
            # Badge kicker: tracked label flanked by two short gold rules.
            self._tracked(d, kicker, f_kick, width, ky, PALETTE["gold"], int(4 * k))
            kw = self._tracked_w(d, kicker, f_kick, int(4 * k))
            kc = ky + self._line_h(d, f_kick) // 3
            seg = int(46 * k)
            gap = int(18 * k)
            lx0 = (width - kw) // 2 - gap - seg
            d.line([(lx0, kc), (lx0 + seg, kc)], fill=(*PALETTE["gold"], 210), width=max(1, int(1.5 * k)))
            rx0 = (width + kw) // 2 + gap
            d.line([(rx0, kc), (rx0 + seg, kc)], fill=(*PALETTE["gold"], 210), width=max(1, int(1.5 * k)))

            f_title = self._fit_font(d, title, max_w, int(46 * k), max(12, int(18 * k)))
            lines = self._wrap(d, title, f_title, max_w)[:3]
            lh = self._line_h(d, f_title)
            ty = int(height * 0.66)
            sh = max(1, int(2 * k))
            for ln in lines:
                # Drop shadow for depth + legibility over the lattice.
                tw = self._text_w(d, ln, f_title)
                d.text(((width - tw) // 2 + sh, ty + sh), ln, font=f_title, fill=(0, 0, 0, 150))
                self._centered(d, ln, f_title, width, ty, PALETTE["ink"])
                ty += lh
            if subtitle:
                f_sub = self._fit_font(d, subtitle, max_w, int(24 * k), max(10, int(12 * k)))
                sub_lines = self._wrap(d, subtitle, f_sub, max_w)[:2]
                slh = self._line_h(d, f_sub)
                ty += int(8 * k)
                for ln in sub_lines:
                    self._centered(d, ln, f_sub, width, ty, PALETTE["muted"])
                    ty += slh

            # Corporate brand bar (bottom): solid band, wordmark left, URL right.
            self._brand_bar(d, width, height, wordmark, k)

        # 5) Bracket frame (refined corner brackets).
        if draw_frame:
            m = int(26 * k)
            tick = int(46 * k)
            fw = max(1, int(2.2 * k))
            for (x0, y0, x1, y1) in [
                (m, m, m + tick, m), (m, m, m, m + tick),
                (width - m - tick, m, width - m, m), (width - m, m, width - m, m + tick),
                (m, height - m, m + tick, height - m), (m, height - m - tick, m, height - m),
                (width - m - tick, height - m, width - m, height - m),
                (width - m, height - m - tick, width - m, height - m),
            ]:
                d.line([(x0, y0), (x1, y1)], fill=(*PALETTE["gold"], 190), width=fw)

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

    # ── brand-system drawing helpers (corporate cypherpunk2048) ─────
    @staticmethod
    def _beam_wash(img, width: int, height: int) -> None:
        """Composite a soft diagonal gold beam from the upper-left for depth —
        a corporate 'spotlight on the mark' wash. Cheap: a blurred polygon."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.polygon(
                [(0, 0), (int(width * 0.62), 0), (int(width * 0.18), height), (0, height)],
                fill=(*PALETTE["gold"], 20),
            )
            layer = layer.filter(ImageFilter.GaussianBlur(max(8, min(width, height) // 12)))
            img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))
        except Exception:
            pass

    @staticmethod
    def _scanlines(img, width: int, height: int, k: float) -> None:
        """Very subtle horizontal scanlines — a printed/CRT cypherpunk texture
        that adds tactility without distracting from the mark."""
        try:
            from PIL import Image, ImageDraw
            layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            step = max(3, int(4 * k))
            for y in range(0, height, step):
                ld.line([(0, y), (width, y)], fill=(0, 0, 0, 26))
            img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"), (0, 0))
        except Exception:
            pass

    def _masthead(self, d, width: int, height: int, wordmark: str, topic: str, k: float) -> None:
        """A publication masthead rail near the top: small wordmark on the left,
        a topic chip on the right, a hairline rule between."""
        try:
            m = int(40 * k)
            y = int(36 * k)
            f = _load_font(max(9, int(13 * k)))
            head, tail = (wordmark[:-1], wordmark[-1]) if wordmark else ("mind", "X")
            d.text((m, y), head, font=f, fill=PALETTE["muted"])
            hx = m + self._text_w(d, head, f)
            d.text((hx, y), tail, font=f, fill=PALETTE["gold"])
            chip = (topic or "dispatch").upper()
            cw = self._tracked_w(d, chip, f, int(3 * k))
            self._tracked(d, chip, f, 2 * (width - m) - cw, y, PALETTE["gold_dim"], int(3 * k))
            ry = y + int(22 * k)
            d.line([(m, ry), (width - m, ry)], fill=(*PALETTE["gold_dim"], 90), width=max(1, int(1 * k)))
        except Exception:
            pass

    @staticmethod
    def _vignette(img, width: int, height: int) -> None:
        """Darken the edges (radial vignette) to focus the centre — depth + a
        premium, less-flat ground."""
        try:
            from PIL import Image, ImageDraw, ImageFilter
            mask = Image.new("L", (width, height), 0)
            md = ImageDraw.Draw(mask)
            inset = int(min(width, height) * 0.10)
            md.ellipse([-inset, -inset, width + inset, height + inset], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(max(12, min(width, height) // 8)))
            dark = Image.new("RGB", (width, height), PALETTE["ground"])
            base = img.copy()
            img.paste(Image.composite(base, dark, mask), (0, 0))
        except Exception:
            pass

    @staticmethod
    def _route_manhattan(d, a, b, color, w: int, rnd) -> None:
        """Right-angle (Manhattan) trace between two nodes — the orderly
        circuit-routing look, with a small node pad at the bend."""
        ax, ay = a
        bx, by = b
        if rnd.random() < 0.5:
            mid = (bx, ay)
        else:
            mid = (ax, by)
        d.line([a, mid], fill=(*color, 64), width=w)
        d.line([mid, b], fill=(*color, 64), width=w)
        r = max(1, w)
        d.ellipse([mid[0] - r, mid[1] - r, mid[0] + r, mid[1] + r], fill=(*color, 110))

    def _emblem(self, img, d, cx: int, cy: int, s: int, k: float) -> None:
        """Gold hexagon shield housing a glowing 'M' sigil — the mindX logomark."""
        from PIL import Image, ImageDraw, ImageFilter
        # Hexagon (flat-top) vertices.
        hexr = int(s * 1.18)
        hexpts = []
        for i in range(6):
            ang = math.radians(60 * i - 30)
            hexpts.append((cx + int(hexr * math.cos(ang)), cy + int(hexr * math.sin(ang))))
        # Accent bloom — a soft radial glow behind the mark, for focus + depth.
        try:
            bloom = Image.new("RGBA", img.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(bloom)
            br = int(hexr * 1.9)
            bd.ellipse([cx - br, cy - br, cx + br, cy + br], fill=(*PALETTE["gold"], 30))
            bloom = bloom.filter(ImageFilter.GaussianBlur(max(6, int(hexr * 0.6))))
            img.paste(Image.alpha_composite(img.convert("RGBA"), bloom).convert("RGB"), (0, 0))
            d = ImageDraw.Draw(img, "RGBA")
        except Exception:
            pass
        # Outer ring — a thin concentric hexagon framing the shield.
        outer = []
        ohexr = int(hexr * 1.16)
        for i in range(6):
            ang = math.radians(60 * i - 30)
            outer.append((cx + int(ohexr * math.cos(ang)), cy + int(ohexr * math.sin(ang))))
        d.polygon(outer, outline=(*PALETTE["gold_dim"], 200))
        # Glow pass (blurred emblem strokes) for luminosity.
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.polygon(hexpts, outline=(*PALETTE["gold"], 150))
        gw = max(2, int(s / 12))
        mpts = [(cx - s, cy + s), (cx - s, cy - s), (cx, cy + int(s * 0.18)),
                (cx + s, cy - s), (cx + s, cy + s)]
        for p, q in zip(mpts, mpts[1:]):
            gd.line([p, q], fill=(*PALETTE["gold_bright"], 220), width=gw)
        glow = glow.filter(ImageFilter.GaussianBlur(max(3, int(6 * k))))
        img.paste(Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB"), (0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        # Inner panel fill for the shield (subtle raised surface).
        d.polygon(hexpts, fill=(*PALETTE["ground3"], 130), outline=(*PALETTE["gold_dim"], 220))
        d.polygon(hexpts, outline=(*PALETTE["gold"], 230))
        # Crisp M on top of the glow.
        for p, q in zip(mpts, mpts[1:]):
            d.line([p, q], fill=(*PALETTE["gold"], 255), width=gw)
        for (px, py) in mpts:
            d.ellipse([px - gw, py - gw, px + gw, py + gw], fill=(*PALETTE["gold_bright"], 150))
        # Baseline accent (the 'X'/ground line under the mark).
        d.line([(cx - s, cy + s + int(16 * k)), (cx + s, cy + s + int(16 * k))],
               fill=(*PALETTE["green"], 210), width=max(2, int(4 * k)))

    def _brand_bar(self, d, width: int, height: int, wordmark: str, k: float) -> None:
        """Corporate footer band: a raised bar with the wordmark (logotype, gold
        'X') on the left and the rage.pythai.net / cypherpunk2048 lockup right."""
        bar_h = int(58 * k)
        y0 = height - bar_h
        d.rectangle([0, y0, width, height], fill=(*PALETTE["ground3"], 235))
        d.line([(0, y0), (width, y0)], fill=(*PALETTE["gold"], 200), width=max(1, int(2 * k)))
        pad = int(36 * k)
        ty = y0 + (bar_h - int(26 * k)) // 2
        # Wordmark logotype: split so the trailing 'X' renders in gold.
        f_mark = _load_font(max(12, int(26 * k)))
        head, tail = (wordmark[:-1], wordmark[-1]) if wordmark else ("mind", "X")
        d.text((pad, ty), head, font=f_mark, fill=PALETTE["ink"])
        hx = pad + self._text_w(d, head, f_mark)
        d.text((hx, ty), tail, font=f_mark, fill=PALETTE["gold"])
        # Right lockup.
        right = "rage.pythai.net · cypherpunk2048"
        f_r = _load_font(max(9, int(14 * k)))
        rw = self._text_w(d, right, f_r)
        d.text((width - pad - rw, y0 + (bar_h - int(14 * k)) // 2), right,
               font=f_r, fill=PALETTE["muted"])

    @classmethod
    def _tracked(cls, d, text: str, font, width: int, y: int, color, tracking: int) -> None:
        """Draw letter-spaced (tracked) text centered — the eyebrow/kicker look."""
        total = cls._tracked_w(d, text, font, tracking)
        x = (width - total) // 2
        for ch in text:
            d.text((x, y), ch, font=font, fill=color)
            x += cls._text_w(d, ch, font) + tracking

    @classmethod
    def _tracked_w(cls, d, text: str, font, tracking: int) -> int:
        if not text:
            return 0
        return sum(cls._text_w(d, ch, font) + tracking for ch in text) - tracking

    @classmethod
    def _line_h(cls, d, font) -> int:
        try:
            bbox = d.textbbox((0, 0), "Ag", font=font)
            return int((bbox[3] - bbox[1]) * 1.32)
        except Exception:
            return 18

    @classmethod
    def _wrap(cls, d, text: str, font, max_w: int) -> List[str]:
        """Greedy word-wrap to ``max_w`` pixels."""
        words = (text or "").split()
        if not words:
            return []
        lines: List[str] = []
        cur = words[0]
        for w in words[1:]:
            trial = cur + " " + w
            if cls._text_w(d, trial, font) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        return lines


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
