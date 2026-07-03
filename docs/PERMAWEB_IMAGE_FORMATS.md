# Permaweb Image-Format Doctrine

On the permaweb **space is money / time** — a byte stored is paid for once and kept
forever. So the format is a deliberate choice per role, not a default. Measured on
the realm doorway backdrop (`gfx/doorway1.webp`, a texture-heavy photo).

## The tiers

### SVG — posters, moon projections, sigils
Vector: infinitely scalable, bytes-tiny, resolution-free. The format for posters and
moon projections. **SVGs naturally emerge from THOT** — a THOT canonical root
(Keccak / RFC-6962 `thot_root`) deterministically generates its own SVG sigil, so the
permaweb stores the **seed, not the pixels**: the art is re-derivable from the canon
itself. Cheapest permanence there is — a hash reconstitutes the image.

### WebP — the permaweb-optimal raster
~25–30% smaller than JPEG at equal quality. Measured: q75 WebP = **89KB** (≈ JPEG-q60
quality, same size); q55 WebP = **69KB**. `cwebp` is available. Where a photo must be
stored as pixels and license permits, WebP is the default raster for permaweb.

### JPEG — normal optimized delivery (the 66–99KB standard)
The delivery workhorse where WebP isn't wanted. **Standard: 66–99KB**, ~1024px,
**4:2:0** subsampling, progressive, stripped. Measured frontier: q55 ≈ **84KB**,
q60 ≈ 91KB, q68 ≈ 105KB — PSNR climbs ~0.4dB per step (no sharp knee on texture).
**4:2:0 beats 4:4:4** decisively (91KB vs 109KB for +0.6dB — a free 18%). Below q50
artifacts creep into smooth/gradient areas. Under a dark veil, 1024px q55 shows no
visible loss. `mozjpeg`/`cjpeg` (a further ~10–20%) is **not installed** here — worth
installing on the box that mints permaweb payloads.

### PNG — best licensing, needs enhancement
PNG has the **best licensing** — royalty-free, patent-unencumbered, universally open —
so it is the safe choice where license certainty and losslessness both matter. But as
a format it **needs enhancement**: truecolor PNG is heavy (~1.1MB for our 1024px
frame). Enhance before permaweb — palette-quantize to png8 and re-compress
(`pngquant` / `oxipng` / `zopflipng`, none installed here; IM `-colors 256 -define
png:compression-level=9` is the fallback). Enhanced, it stays open-license and lossless-
enough.

### TIFF — monster masters, permanent templates
For **monster images**, **templates**, and **permanent templates**: the lossless
archival master, the source of truth from which every delivery derivative (WebP / JPEG /
SVG) is generated. Big and permanent by design — the template you keep, not the one you
ship.

## Method

Master in **TIFF** → derive delivery in **WebP** (or **JPEG** in the 66–99KB standard,
4:2:0) → posters & sigils in **SVG** (emergent from THOT — store the seed) → **PNG**
(enhanced) where open-license losslessness is required. Install `mozjpeg`, `pngquant`/
`oxipng`, and `avifenc` on the permaweb-minting host to push payloads smaller still.
