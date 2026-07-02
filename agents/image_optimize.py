# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""image_optimize — artist.agent's permaweb image toolchain.

Wraps the installed CLI optimizers behind the permaweb image-format doctrine
(docs/PERMAWEB_IMAGE_FORMATS.md): space = money / time, so pick the format per
role. Every function detects its binary and falls back gracefully to ImageMagick,
so it never hard-fails on a host missing a tool.

  mozcjpeg   JPEG delivery (trellis quant, 4:2:0, progressive) → 66-99KB standard
  cwebp      WebP — the permaweb-optimal raster (~25-30% < JPEG)
  avifenc    AVIF (bonus, where present)
  pngquant   PNG palette quant  ┐ the "enhancement" PNG needs
  oxipng     PNG lossless recompress ┘
  (magick)   TIFF masters + universal decode/resize + fallback encoder

SVGs are not compressed here — they EMERGE from THOT: svg_sigil_from_thot()
deterministically renders a sigil from a THOT canonical root, so the permaweb
stores the seed, not the pixels.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

JPEG_MAX_KB = 99   # the optimized standard band (66=first visual loss, 99=no degradation)
JPEG_MIN_KB = 66


def _bin(*names: str) -> Optional[str]:
    """First of `names` found on PATH (also checks ~/.local/bin, /opt/mozjpeg/bin)."""
    extra = [os.path.expanduser("~/.local/bin"), "/usr/local/bin", "/opt/mozjpeg/bin"]
    for n in names:
        p = shutil.which(n)
        if p:
            return p
        for d in extra:
            cand = os.path.join(d, n)
            if os.path.exists(cand) and os.access(cand, os.X_OK):
                return cand
    return None


def available() -> Dict[str, Optional[str]]:
    """Which optimizers are installed on this host (paths or None)."""
    return {
        "mozcjpeg": _bin("mozcjpeg", "cjpeg"),
        "cwebp": _bin("cwebp"),
        "avifenc": _bin("avifenc"),
        "pngquant": _bin("pngquant"),
        "oxipng": _bin("oxipng"),
        "magick": _bin("magick", "convert"),
    }


def _run(cmd: List[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=kw.get("timeout", 120))


def _kb(path: str) -> float:
    try:
        return os.path.getsize(path) / 1024.0
    except OSError:
        return 0.0


def optimize_jpeg(src: str, dst: str, *, width: int = 1024,
                  max_kb: float = JPEG_MAX_KB, min_kb: float = JPEG_MIN_KB) -> Dict[str, Any]:
    """Encode a delivery JPEG in the 66-99KB standard: 4:2:0, progressive, mozjpeg
    trellis when available (else magick). Quality-searches to land in the band."""
    tools = available()
    magick = tools["magick"]
    if not magick:
        return {"success": False, "error": "ImageMagick required to decode/resize"}
    moz = tools["mozcjpeg"]
    best = None
    for q in (78, 72, 66, 60, 55, 50, 45):
        if moz:
            ppm = _run([magick, src, "-resize", f"{width}x", "-strip", "ppm:-"])
            enc = subprocess.run([moz, "-quality", str(q), "-sample", "2x2", "-optimize",
                                  "-progressive", "-outfile", dst], input=ppm.stdout,
                                 capture_output=True, timeout=120)
            ok = enc.returncode == 0
        else:
            enc = _run([magick, src, "-resize", f"{width}x", "-quality", str(q), "-strip",
                        "-interlace", "Plane", "-sampling-factor", "4:2:0", dst])
            ok = enc.returncode == 0
        if not ok:
            continue
        kb = _kb(dst)
        best = {"quality": q, "kb": round(kb, 1)}
        if kb <= max_kb:                       # first q at/under the ceiling wins
            in_band = kb >= min_kb
            return {"success": True, "path": dst, "encoder": "mozjpeg" if moz else "magick",
                    "quality": q, "kb": round(kb, 1), "in_standard": in_band, "width": width,
                    "sampling": "4:2:0", "progressive": True}
    return {"success": bool(best), "path": dst, "encoder": "mozjpeg" if moz else "magick",
            **(best or {}), "in_standard": False, "width": width}


def to_webp(src: str, dst: str, *, width: int = 1024, q: int = 75) -> Dict[str, Any]:
    """WebP — the permaweb-optimal raster."""
    cwebp = available()["cwebp"]
    if not cwebp:
        return {"success": False, "error": "cwebp not installed"}
    r = _run([cwebp, "-quiet", "-q", str(q), "-resize", str(width), "0", src, "-o", dst])
    return {"success": r.returncode == 0, "path": dst, "encoder": "cwebp", "q": q,
            "kb": round(_kb(dst), 1), "width": width}


def to_avif(src: str, dst: str, *, width: int = 1024, q: int = 60) -> Dict[str, Any]:
    """AVIF (bonus). avifenc quality is 0(worst)-100(best); maps ~q."""
    tools = available()
    if not tools["avifenc"]:
        return {"success": False, "error": "avifenc not installed (apt: libavif-bin)"}
    magick = tools["magick"]
    tmp = dst + ".png"
    if magick:
        _run([magick, src, "-resize", f"{width}x", "-strip", tmp]); ip = tmp
    else:
        ip = src
    r = _run([tools["avifenc"], "-q", str(q), ip, dst])
    try:
        if os.path.exists(tmp): os.remove(tmp)
    except OSError:
        pass
    return {"success": r.returncode == 0, "path": dst, "encoder": "avifenc", "q": q,
            "kb": round(_kb(dst), 1), "width": width}


def optimize_png(src: str, dst: str, *, colors: int = 256, width: Optional[int] = None) -> Dict[str, Any]:
    """PNG enhancement: palette-quantize (pngquant) then lossless recompress (oxipng).
    PNG has the best licensing but needs this to be permaweb-worthy."""
    tools = available()
    magick, pq, ox = tools["magick"], tools["pngquant"], tools["oxipng"]
    stage = src
    if width and magick:
        stage = dst + ".resized.png"
        _run([magick, src, "-resize", f"{width}x", stage])
    steps: List[str] = []
    if pq:
        r = _run([pq, "--force", str(colors), "--output", dst, "--", stage])
        if r.returncode in (0, 98, 99):  # 98/99 = quality-below-limit but still wrote
            steps.append("pngquant")
        else:
            shutil.copyfile(stage, dst)
    else:
        (shutil.copyfile(stage, dst) if stage != dst else None)
    if ox:
        if _run([ox, "-o", "4", "--strip", "safe", "-q", dst]).returncode == 0:
            steps.append("oxipng")
    if width and magick and os.path.exists(dst + ".resized.png"):
        try: os.remove(dst + ".resized.png")
        except OSError: pass
    return {"success": os.path.exists(dst), "path": dst, "steps": steps,
            "kb": round(_kb(dst), 1), "license": "open (royalty-free, patent-free)"}


def master_tiff(src: str, dst: str) -> Dict[str, Any]:
    """Lossless TIFF master — the permanent template / source of derivatives."""
    magick = available()["magick"]
    if not magick:
        return {"success": False, "error": "ImageMagick required"}
    r = _run([magick, src, "-compress", "LZW", dst])
    return {"success": r.returncode == 0, "path": dst, "encoder": "magick",
            "kb": round(_kb(dst), 1), "role": "master/permanent-template"}


def svg_sigil_from_thot(thot_root: str, *, size: int = 512, rings: int = 5) -> str:
    """Deterministically render an SVG sigil from a THOT canonical root — the art
    emerges from the canon (store the seed, not pixels). Golden-ratio mandala whose
    geometry + palette derive entirely from the root hash. Returns SVG text."""
    h = hashlib.sha256((thot_root or "").encode()).digest()
    PHI = 1.6180339887
    cx = cy = size / 2.0
    hue = h[0] / 255.0 * 360.0
    def col(i: int, l: int) -> str:
        return f"hsl({(hue + i * 137.508) % 360:.0f} {60 + h[(i+3) % 32] % 30}% {l}%)"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
             f'role="img" aria-label="THOT sigil {thot_root[:12]}">',
             f'<rect width="{size}" height="{size}" fill="#04060b"/>']
    for r in range(rings, 0, -1):
        n = 3 + (h[r % 32] % 9)                       # 3..11 points per ring
        rad = (size * 0.44) * (r / rings) / PHI * PHI  # φ-spaced radii
        pts = []
        for k in range(n):
            a = (2 * math.pi * k / n) + (h[(r + k) % 32] / 255.0) * math.pi
            pts.append(f"{cx + rad*math.cos(a):.1f},{cy + rad*math.sin(a):.1f}")
        parts.append(f'<polygon points="{" ".join(pts)}" fill="none" '
                     f'stroke="{col(r, 55)}" stroke-width="{0.5 + (h[r%32]%3)}" '
                     f'opacity="{0.35 + 0.5*(r/rings):.2f}"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{size*0.03:.1f}" fill="{col(0, 62)}"/>')
    parts.append('</svg>')
    return "".join(parts)


def permaweb_derivatives(src: str, out_base: str, *, width: int = 1024) -> Dict[str, Any]:
    """Produce the doctrine derivative set from one source: TIFF master + WebP + JPEG
    (66-99KB) + enhanced PNG. Returns each result (skips formats whose tool is absent)."""
    return {
        "tiff": master_tiff(src, out_base + ".tiff"),
        "webp": to_webp(src, out_base + ".webp", width=width),
        "jpeg": optimize_jpeg(src, out_base + ".jpg", width=width),
        "png": optimize_png(src, out_base + ".png", width=width),
        "avif": to_avif(src, out_base + ".avif", width=width),
        "available": available(),
    }
