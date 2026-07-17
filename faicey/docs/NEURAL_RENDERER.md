# The neural renderer — gated hyperrealism

The photoreal renderer ([PHOTOREAL_RENDER.md](./PHOTOREAL_RENDER.md)) reaches
**realism**: real texture on real geometry. *Hyperrealism* — a face synthesized
indistinguishably from reality, including the novel views and disocclusions a
single capture never saw — needs a **neural renderer**: a face-restoration net
(GFPGAN / CodeFormer class) refining the affine composite, or a NeRF /
Gaussian-splat model synthesizing the face outright. Affine warping cannot fake
that, and faicey does not pretend it can.

So this release ships the **capability, gated** — not a hyperrealism claim. Two
honest halves in `src/face_clone/neural_render.js`.

---

## 1. The backend seam — `NeuralRenderer`

A pluggable backend that runs a **real ONNX model** when a runtime + weights are
provided, and is **dormant** otherwise. **No weights are committed to this repo**
— the same doctrine as voaice's ONNX voices (weights never committed) and
mindXtrain's dormant-by-default CPU bridge.

```js
import { NeuralRenderer } from './src/face_clone/neural_render.js';
const nr = new NeuralRenderer();

nr.describe();
// dormant → { available:false, backend:null, reason:'…neural backend dormant (realism via affine)' }

// Activate it — operator-supplied runtime + weights, OR a pre-built session:
await nr.load({ runtime: ort, modelPath: '/path/to/face_refine.onnx', dims: 512 });
// or:  await nr.load({ session })   // any object with an async run()

// Refine the affine photoreal composite (2.6) into a neural render:
const out = await nr.refine({ data, width, height });   // ImageData-shaped
// dormant → { image: <input unchanged>, neural:false }   (honest passthrough)
// active  → { image: <refined frame>,   neural:true  }
```

The inference contract is **NCHW float32 RGB in `[0,1]`, same-shape out** — the
standard image-restoration signature. `_infer` tensorizes, runs the session, and
detensorizes; it executes only when a real session is loaded.

In the demo, `window.faiceyNeural` is the live instance — an operator can activate
it from the console and the **neural** render mode will refine each frame.

## 2. The fidelity gate — `gradeFidelity` (the doctrine)

This is the part that keeps faicey honest. A render is **measured**, and
`hyperreal` is stamped **only** when a neural backend's output clears every bar:

| measure | meaning | floor |
|---------|---------|-------|
| `identity` | the render still measures as the same person (faceprint-vector consistency) | ≥ 0.85 |
| `structural` | it matches the reference structurally (global SSIM) | ≥ 0.90 |
| `coverage` | enough of the face is synthesized, not holes | ≥ 0.80 |

```js
gradeFidelity({ backend:'neural', identity:0.96, structural:0.93, coverage:0.9, hasTexture:true })
//   → { verdict:'hyperreal', hyperreal:true, … }

gradeFidelity({ backend:'affine', identity:1, structural:1, coverage:1, hasTexture:true })
//   → { verdict:'realism', hyperreal:false,
//       reasons:['affine backend cannot earn hyperreal — only a neural render is graded for it'] }
```

**By construction, only a neural render can earn `hyperreal`.** The affine /
classical path caps at `realism`; no texture caps at `surface`. A neural render
that *runs* but doesn't measure up is capped too, with the failing measure named
— it is never stamped on faith. The thresholds are published constants
(`FIDELITY`) and a test asserts there is no silent relaxation (`>=`, to the
line). This is "measured, not asserted" made mechanical.

The metrics are real and testable: `identityConsistency(vecA, vecB)` (grounded in
the faceprint ratio vector), `structuralSimilarity(a, b)` (global SSIM),
`renderCoverage(mask)`.

---

## Status on this host

**Dormant.** No ONNX runtime or weights are deposited here, so the neural mode is
an honest passthrough of the affine composite and every render grades to
**realism**. `GET /api/render/neural/status` reports this plainly, along with the
gate thresholds.

Hyperrealism is therefore **not achieved** in this release — it is made
*reachable and safe*: the seam runs a real model when one is provided, and the
gate guarantees the "hyperreal" label can only ever be **earned by measurement**,
never asserted. Activating it is an operator action (deposit weights + a runtime);
grading it hyperreal is the gate's, on the numbers.

### In aivatar's terms

The tier ladder is now complete in *mechanism*: basic → professional → scientific
(realism) → **scientific (hyperrealism)**, the last gated behind a loaded neural
backend that measures through this gate, plus the same signed provenance every
tier above basic already requires. The rung exists; climbing it needs a model.

---

## Verification

```
node src/face_clone/neural_render.test.js   # 12 tests
```

- a neural render clearing every threshold is stamped hyperreal; one that misses is capped, with the failing measure named;
- **the affine/classical backend can never earn hyperreal, at any score**;
- no-backend → realism (with texture) or surface (without);
- the thresholds are the published constants (no silent relaxation);
- `identityConsistency` / `structuralSimilarity` / `renderCoverage` behave;
- a fresh renderer is dormant and says so; `load` without weights stays dormant; `refine` passes through untouched; an injected session activates inference and the gate can then grade the result hyperreal.
