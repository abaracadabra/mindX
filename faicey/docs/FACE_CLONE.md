# faicey face clone — single image · perspective images · video

Face cloning is the visual sibling of voaice's voice cloning: where voaice clones a VOICE from a
reference clip and yields a forensic 18-dp **voiceprint** (`Scientific.js` → `registerVoicePrint`),
faicey clones a FACE from reference image(s)/video and yields a forensic 18-dp **faceprint**
(`faceprint.js` → `registerFacePrint`) plus cloned facial proportions that reshape the wireframe.

All in-house, **torch-free**, no-CDN. The model dependency is optional and lazy.

## Pipeline

```
 SINGLE image  ─┐
 PERSPECTIVES ──┤→ MediaPipe Face Landmarker (WASM/TFLite, Apache-2.0, torch-free)
 VIDEO clip   ─┘   → 478 3D landmarks + 4×4 pose matrix + 52 blendshapes per frame
                       │
        pose-normalise (inverse 4×4) → aggregate (most-frontal + per-vertex average)
                       │
        ┌──────────────┴───────────────┐
        ▼                              ▼
  CLONE GEOMETRY                 FORENSIC FACEPRINT
  - 478-landmark wireframe       - ordered inter-landmark ratios
    (contours.js)                - 18-dp fixed-point + sha256
  - morphological proportions    - registerFacePrint(hash, uint256[12], precision)
    → reshape the branded face   - L2 distance = same-person test
```

## Modules (`src/face_clone/`)

| File | Role |
| ---- | ---- |
| `landmarks.js` | lazy `@mediapipe/tasks-vision` FaceLandmarker (optional dep; vendored WASM + `face_landmarker.task` under `static/vendor/mediapipe/`, no CDN). Absent → graceful fallback. |
| `geometry.js` | landmark index map → scale-invariant `FacialProportions`; `poseNormalize`; `aggregate` (multi/video denoise + most-frontal pick); `symmetry`/`frontality`. |
| `faceprint.js` | the **Scientific** sibling: 12 ordered ratio measures → `toFixed18` + sha256 → forensic faceprint; `toRegisterArgs`; `faceprintDistance`. |
| `contours.js` | MediaPipe contour loops + `drawFaceWireframe(ctx, landmarks)` — draws the cloned face from the person's landmarks. |
| `face_clone_engine.js` | orchestrator: `cloneFromImage` / `cloneFromPerspectives` / `cloneFromVideo` → `FaceProfile{ proportions, landmarks, faceprint, quality }`; `FaceCloneEngine.match(a,b)`. |

Detection is **pluggable**: pass image/video elements (browser → MediaPipe) OR pre-detected frames
`{ landmarks, matrix?, confidence? }` (Node/tests). Either way it aggregates + measures.

## Studio + server

- `GET /clone-face` — in-house studio (`face-clone.html`): upload a single image, perspective images,
  or a video clip → cloned wireframe + the 18-dp faceprint. A **DEMO** button synthesises a face so the
  pipeline is demonstrable before MediaPipe is vendored.
- `POST /api/clone-face` — persist a faceprint record (parallel to voaice `POST /clone`).
- `GET /api/clone-face/recent` — recent faceprints.

## Canonical 3D engine integration (facerig)

A cloned face reshapes the branded wireframe: `faceFromFacets(facets)` accepts a `clone.proportions`
facet → `FaceRendererOptions.cloneProportions` → `FaceGeometry.createFaceGeometry(proportions)` scales
the base mesh (face height, eye spread, jaw/nose/mouth width). Additive + backward-compatible; rebuild
with `npm run build:lib` in facerig, then `node scripts/sync-engine.mjs` in faicey (already done).
The high-fidelity clone is the 478-landmark wireframe; the canonical 38-vertex face is a brand mark, so
its clone is a stylised parametric approximation.

## Model install (torch-free, no CDN)

```bash
cd faicey
npm i @mediapipe/tasks-vision
# vendor the WASM fileset + model locally (no CDN):
#   static/vendor/mediapipe/vision_bundle.mjs  (+ wasm/)
#   static/vendor/mediapipe/face_landmarker.task   (~3.7 MB, Apache-2.0)
```

`face_landmarker.task` is third-party (Google, Apache-2.0) — fetched, not committed (like the voice
model weights). Without it, the studio's DEMO mode + the faceprint-from-landmarks path still work.

## The cloned face emotes (lockstep with the voice)

`expressions.js` — `applyExpression(landmarks, emotion, intensity)` displaces the cloned landmarks
(mouth corners/lips, brows, eyelids) per emotion, scaled by inter-ocular distance. The 9-emotion
vocabulary matches the voice side (`neutral, happy, excited, calm, sad, angry, surprised, confused,
thinking`), so a persona's face and voice emote together. The studio has emotion buttons; showcase:
`face-clone-emotes-showcase.png` (one cloned person across all emotions).

## Rendering — wireframe, shaded surface, or photoreal

The FACE renders three ways (`render_surface.js` + `drawFaceSurface`): the
**wireframe** (contour loops), a **shaded surface** (the mesh lit as a solid),
and **photoreal** — the person's captured frame affine-mapped per triangle onto
the measured mesh. Because the texture is tied to landmark indices, the photoreal
face re-warps as it expresses (the emotions above, and the mouth on the cloned
voice) — real texture on real geometry. It is *not* neural view-synthesis and
does not claim hyperrealism. Full detail + the honest fidelity boundary:
[PHOTOREAL_RENDER.md](./PHOTOREAL_RENDER.md).

## Unified persona = FACE + VOICE

`persona.js` — `personaPrint({ face, voice })` binds a faceprint and/or a voaice voiceprint into one
deterministic forensic identity → `registerPersona(hash, faceHash, voiceHash, uint256[], precision)`,
the union of `registerFacePrint` + `registerVoicePrint`. Either modality alone is a valid persona;
together they bind one identity. `POST /api/persona` persists. This is the culmination of the
FACE/VOICE duality — a person cloned across both modalities, emoting in sync.

## On-chain — the persona becomes an Intelligent NFT

The bound persona (or either print alone) mints as an ERC-7857 iNFT on the
DeltaVerse `iNFT_7857` contract: the print's reproducible hash *is* the token's
`contentRoot`. `inft.js` builds the mint payload; `minter.js` turns it into a
ready-to-broadcast transaction — **faicey builds the tx, the wallet owner signs
it**. The full path (payload → transaction → wallet flow, the two selectors, the
viem-verified encoder) is documented in [INFT_MINTING.md](./INFT_MINTING.md).

## Verification

`node src/face_clone/face_clone.test.js` — **8/8**: scale-invariant proportions, 18-dp deterministic
faceprint + registerArgs, multi-frame aggregation denoise, single/perspective/video cloning, identity
match (same-person vs different), symmetry, **expressions (smile up / frown down, originals intact)**,
**persona print (binds face+voice, deterministic, registerable)**. Showcases: `face-clone-showcase.png`
(distinct people) + `face-clone-emotes-showcase.png` (one person emoting). Live MediaPipe detection +
the 3D render need a browser.
