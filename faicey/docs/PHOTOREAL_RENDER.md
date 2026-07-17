# The photoreal renderer — from wireframe to a real surface

Until now the FACE rendered as a **wireframe** — contour loops through the
landmarks. Recognisable, but a schematic. The photoreal renderer lifts it to a
rendered **surface**, in two honest modes, both built on one mesh
(`src/face_clone/render_surface.js`; the canvas draw is `drawFaceSurface` in
`contours.js`).

| mode | what it draws | fidelity |
|------|---------------|----------|
| **surface** | the mesh shaded as a solid — Lambert lighting on the real 3D normals | a rendered face, still synthetic geometry |
| **photoreal** | the person's **captured frame**, affine-mapped per triangle onto the measured mesh | real texture on real geometry — genuine *photographic* realism of the capture |

Both appear in the `/face` demo's **render** dropdown.

---

## How it works

1. **Mesh.** The landmarks are triangulated once (Bowyer–Watson **Delaunay**,
   `triangulate()`) into a stable triangle topology. The topology is cached from
   the base geometry, so an expression *deforms* the same mesh instead of
   re-triangulating each frame (which would flicker).
2. **Shading (surface mode).** Each triangle's real 3D normal (from the landmark
   `z` relief) is lit by a fixed light — `shade = ambient + (1−ambient)·max(0,
   n·light)` — and the skin base is modulated by it. Triangles are painted
   **back-to-front** (`paintOrder`, by mean depth) so nearer facets win.
3. **Texturing (photoreal mode).** For each triangle, an exact **affine
   transform** (`affineFromTriangle`, solved not approximated) maps the
   triangle's corners in the *captured frame's pixel space* to its corners on the
   *canvas*. The frame is clipped to the triangle and drawn through that
   transform — classic per-triangle texture mapping, no WebGL required. A faint
   shade multiply adds relief.

Because the source UVs are tied to landmark **indices**, when the mesh deforms —
an expression, or the cloned voice driving the mouth — every destination triangle
moves and its texture re-warps with it. **The captured face emotes photoreally.**

The texture source is the captured frame (static, and it expresses), or — with
the webcam live and no capture yet — the live video frame itself, giving live
photoreal reenactment for free.

---

## What this is, and is not

This is real texture on real geometry: the person's own skin and features on the
mesh faicey measured. That is genuine **photographic realism of the capture**.

It is **not** neural view-synthesis. It cannot invent occluded or novel views
(turn the textured face far and the single frame's coverage runs out), and it
makes **no claim** to "hyperrealism indistinguishable from reality." That tier
needs a neural renderer (a Gaussian-splat / NeRF-class model) — an explicitly
labeled future, not something affine warping can assert.

### Fidelity, in aivatar's terms

The renderer raises what the FACE can **present**, not what faicey **measures**.
A photoreal render of an accurately-captured FAICE reaches **realism** — it is
the person, textured on their measured geometry. The *tier* a persona earns still
depends on the measured capture accuracy and signed provenance (basic /
professional / scientific), graded in aivatar. Hyperrealism remains gated on the
neural renderer above.

---

## Verification

```
node src/face_clone/render_surface.test.js   # 8 tests
```

- the Delaunay triangulation is valid (empty-circumcircle) with no degenerate triangles;
- `affineFromTriangle` maps each source corner **exactly** onto its destination, and rejects a colinear source;
- `buildSurface` shades the neutral face with unit normals and shades in `[ambient, 1]`;
- **topology reuse keeps the mesh stable while an expression deforms it** (same triangles, moved vertices, changed shading);
- `shadeColor` clamps and darkens correctly; `paintOrder` sorts back-to-front.

The canvas draw itself is browser-only; the geometry and the math it rests on are
proven headless. See [FACE_CLONE.md](./FACE_CLONE.md) for the capture pipeline
that produces the mesh and the texture.
