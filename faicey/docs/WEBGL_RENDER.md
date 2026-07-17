# WebGL rendering — real 3D depth, on the DeltaVerse substrate

The 2D path (contours.js / render_surface.js) paints triangles with the CPU and
an affine per-triangle texture warp — recognisable, but flat, with faint seams
where triangles meet. WebGL draws the **same mesh on the GPU**: a perspective
camera with real depth, and perspective-correct texture interpolation (no seams).

## Built on the existing DeltaVerse substrate — not three.js

Before writing this, the existing DeltaVerse rendering substrate was reviewed
(`dapp/deltaverse.js`, the participant field used by the realm doorway). That
substrate is deliberately **raw WebGL** — `getContext('webgl')`, inline
vertex/fragment shaders, and a **2D-canvas fallback so it always shows** — *not*
three.js. The faicey WebGL face renderer follows the same doctrine, rather than
pulling in three.js's ~2 MB:

- raw `WebGLRenderingContext`, inline GLSL (a lit + optionally textured mesh);
- `.ok === false` when WebGL is unavailable → the caller falls back to the 2D
  shaded surface — the same always-shows contract as the DeltaVerse field;
- the same conventions (constructor-per-renderer, `resize` / `render` / `dispose`,
  the shared HSL/colour approach).

This keeps faicey's rendering aligned with the DeltaVerse substrate: a face is
drawn with the same lightweight WebGL technology that draws its participants.

## The two halves

- **`src/face_clone/webgl_face.js`** — the pure, headless-tested core:
  - `buildFaceGeometry(landmarks, { topology, uvSource })` → the four buffers the
    GPU needs: `positions` (centred, unit-scaled, **Y-flipped** image→GL, nose
    toward the viewer), `indices` (from the Delaunay topology), `uvs` (from the
    capture frame, flipped for the GL texture origin), and smooth per-vertex
    `normals`.
  - a tiny **mat4** (`m4perspective`, `m4rotationY`, `m4translation`,
    `m4multiply`) — the MVP transform, tested.
  - `WebGLFaceRenderer` — the raw-GL renderer (browser-only): `setGeometry`,
    `setTexture`, `setMode('surface'|'photoreal')`, `render({ rotY })`. 16-bit
    indices when the mesh fits (< 65536 verts) so no `OES_element_index_uint` is
    needed on WebGL1.

- **The demo** — a **webgl** render mode. It builds the geometry each frame from
  the current (expressed) landmarks + cached topology, textures it with the
  captured frame (or the live video), and draws it with a gentle head-turn so the
  real depth reads. If WebGL is unavailable it falls back to the 2D shaded
  surface and says so.

## What it earns

WebGL is a better *rendering* of the same measured mesh — real depth,
perspective, seam-free GPU texturing. A GPU-textured render of a captured FAICE
still grades to **realism** (real texture on real geometry); it is not neural
synthesis and makes no hyperrealism claim. The fidelity gate
([NEURAL_RENDERER.md](./NEURAL_RENDERER.md)) treats the `webgl-gpu` backend the
same way it treats the affine one — hyperreal stays reserved for a measured
neural render.

## Verification

```
node src/face_clone/webgl_face.test.js   # 10 tests
```

- the four buffers are the right sizes; positions are centred and Y-flipped; UVs
  come from the capture source, flipped, in `[0,1]`; normals are unit length; a
  null landmark makes no NaNs;
- the mat4 helpers are correct (identity multiply, `rotationY(0)=I`,
  `rotationY(π/2)` sends +X→−Z, the perspective diagonal + w-clip term,
  translation column).

The GL draw itself (and texture orientation) is browser-only — the geometry and
the transforms it rests on are proven headless, and the module + demo are
verified to serve `200`. See [PHOTOREAL_RENDER.md](./PHOTOREAL_RENDER.md) for the
2D pipeline that is also the WebGL fallback.
