# Changelog

All notable changes to **faicey**. Versions follow [semver](https://semver.org).

---

## [2.16.1] — 2026-07-17

### Changed — the ears show a frequency response when they pulse

The ear-speakers no longer just pulse with the level — each now blooms a **live
frequency response**: the spectrum is binned into 12 log-spaced bands (smoothed),
drawn as radial bars fanning around the speaker cone, **coloured by frequency**
(low→red, high→violet) and as long as that band is loud, with a bright tip on hot
bands. Reuses the already-tested `oscilloscope.spectrum()` — no new dependency.

---

## [2.16.0] — 2026-07-17

### Changed — **cyborgi**: the endoskeleton, polished and reflective, in high detail

The human↔machine morph is now named **cyborgi**, and its endoskeleton was
rebuilt to be genuinely high-quality — polished, reflective, and detailed:

- **layered chrome plates** (brow/temple, cheek, jaw) with diagonal metal
  gradients (dark→bright→dark), **bevel edges + dark seams**, and **rivets with
  specular dots**;
- a detailed **red optical sensor** — chrome housing ring, concentric iris rings,
  a hot core, a lens-flare cross, and a red bloom;
- **hydraulic pistons** at the jaw hinge (chrome cylinder + piston rod +
  highlight streak), exposed **segmented metal teeth**;
- **cool/warm environment-reflection rims** and specular streaks for the polished
  look.

Still a generic cyborg — procedural, landmark-tracked, no specific copyrighted
character. Palette extended in `mech.js` (chrome/edge/seam/spec/rim tones). Suite
green: 152.

---

## [2.15.0] — 2026-07-17

### Added — the full anatomical control surface + morph modes

The face became a complete instrument. On top of eye/ear/mouth (2.14):

- 👃 **the nose is networking diagnostics** — click it to ping (latency, jitter,
  connection); 🩸 **right nostril → blockchain scan** (the connected wallet's
  balance at **18-dp**, nonce, chain — read-only); 🔎 **left nostril → RAGE
  search** (the rage.pythai.net index, proxied with a link fallback).
  (`src/face_clone/nose_tools.js` — ping stats, JSON-RPC, wei→ETH 18-dp,
  address validation, search ranking; 8 tests.)
- 🧠 **left brain → analytical/math tools, right brain → creativity/expression.**
- 👁 **third eye → the deep diagnostic matrix** — a semi-hidden easter egg that
  **isn't always there** (it fades in intermittently); it aggregates every tool.
- 👂 **the ears pulse like speakers** with the live audio level.
- **Morph modes** (`morph.js`, `mech.js`): **human ↔ machine** slides one side
  into a tough, detailed **endoskeleton** (a generic cyborg — not any one film's
  character); plus **vampire / elf / dragon / pleiadian** archetypes, all
  procedural and landmark-tracked, at a slider's intensity. 5 + 6 tests.
- **Age slider** child → elder (recorded in the `.persona`), and **image upload**
  as the morph basis (MediaPipe IMAGE-mode detection → geometry + texture).
- Server: `/api/net/ping` + `/api/rage/search` (best-effort proxy). The persona
  payload records `morph` + `age`.
- Suite green: **152**.

Detail: [docs/FACE_CONTROLS.md](./docs/FACE_CONTROLS.md).

---

## [2.14.0] — 2026-07-17

### Added — the face is the control surface + a webcam range finder

Each sense organ now drives the hardware it represents
(`src/face_clone/face_controls.js`, `distance.js`):

- 👁 **the eye is a camera** — clicking an eye toggles the webcam; over each iris
  the demo draws a **lens aperture** (ring + six aperture blades) that glows and
  shows a red recording dot when the camera is live. A camera has an eye.
- 👂 **the ear is the microphone** — clicking an ear controls mic input.
- 👄 **the mouth is the output** — clicking the mouth opens a volume/mute panel
  that drives a Web Audio gain on the avatar's speech.
- **Range finder** — because the eye is a camera it can range-find: a pinhole
  model (`D = f·S/s`) turns the measured inter-pupillary distance into a live
  **⟠ N cm** distance to the subject, from the iris landmarks + the webcam FOV.
  Returns `null` without the iris — it never guesses.
- Hit-testing maps a canvas click to the feature under it (feature discs in the
  renderer's own fit transform, nearest-hit); `CONTROL_MAP` names the wiring.
- **8 tests** (eye→camera, ear→mic, mouth→output, nearest-hit, empty-space miss;
  the range finder exact against the pinhole model, inverse in IPD px, ~1 m at the
  calibrated IPD, null without the iris). Suite green: 130.

Detail: [docs/FACE_CONTROLS.md](./docs/FACE_CONTROLS.md).

---

## [2.13.0] — 2026-07-17

### Added — quant-finance accuracy, a shared sci-fi substrate, waterfall interaction

**Accuracy from a scientific-finance toolset** (`src/face_clone/finmeasure.js`).
A voice signal is a time series, and quant finance measures noisy series with a
stated uncertainty better than anything — so those tools sharpen the scope:

- **Kalman filter** stabilises the per-frame YIN pitch into an optimal estimate;
  the readout shows **ƒ₀ ± 95% confidence interval** (Hz). The smoothed track is
  provably tighter than the raw estimates.
- **Jitter / shimmer** — EWMA volatility (RiskMetrics σ) of the pitch track *is*
  jitter, of the amplitude track *is* shimmer — real forensic voice measures.
- moments (skew/kurtosis), Bollinger bands, z-score outliers (splice detection).
- **Everything carried at conventional EVM 18-decimal precision** (`toFixed18Str`,
  signed + carry-safe — the faceprint/voiceprint fixed-point scale). 14 tests.

**The sci-fi HUD substrate (◈)** (`src/face_clone/scifi_substrate.js`) — **evolved
from the DeltaVerse participant field** (`dapp/deltaverse.js`, the drifting "stars
are people") fused with instrument chrome (corner brackets, reticle, grid, sweep).
A **◈ HUD** toggle themes the measurement panel as a sci-fi instrument (cyan
telemetry, glow) and mounts the live HUD. **Vendored into voaice too**
(`voaice/src/scifi_substrate.js`) — faicey and voicey share one visual language.
Dependency-free; layout geometry + drifting field pure + tested (4 tests).

**Waterfall interaction** — hover to read the **frequency**, **time-ago**, and
**intensity (dB)** at any point (from the `Spectrogram` model's history), with a
cyan guide mirrored onto the spectrum; **click to freeze** for inspection; a
0–8 kHz frequency axis.

Suite green: **126** (14 finmeasure + 4 substrate + the rest). The shared modules
also pass in the voaice tree (18 tests). Detail: [docs/OSCILLOSCOPE.md](./docs/OSCILLOSCOPE.md).

---

## [2.12.0] — 2026-07-17

### Added — the spectrogram waterfall

A scrolling time–frequency history under the spectrum (`src/face_clone/spectrogram.js`).

- **Waterfall (🌊)** — each FFT frame becomes the top row and the history flows
  **downward**; the spatial axis is frequency, the **colour axis is intensity in
  dB** on a perceptual **inferno** colormap (the spectrogram standard). Speech
  harmonics draw bright rails that move with pitch; formants show as steady bands.
- **dB scaling** (`dbNorm` / `magnitudesToDb`) against a smoothed running
  reference (a gentle AGC) so quiet and loud passages both read; rendered by
  scrolling the canvas one row and painting the newest spectrum on top — one FFT
  per frame, shared with the spectrum bars.
- Perceptual **`inferno` / `magma`** colormaps, log/linear axis mappers, and a
  `Spectrogram` rolling frame buffer for the model — all pure + headless-tested.
- **8 spectrogram tests** (dB mapping to the reference/floor, inferno dark→bright
  monotone, axis monotonicity, the rolling buffer drops the oldest + copies).
  Suite green: 108.

Detail: [docs/OSCILLOSCOPE.md](./docs/OSCILLOSCOPE.md).

---

## [2.11.0] — 2026-07-17

### Added — the scientific oscilloscope

The scope became a real measurement instrument, built on the canonical
open-source DSP after reviewing how scopes and pitch trackers actually work
(`src/face_clone/oscilloscope.js`, pure + headless-tested).

- **Accurate frequency measurement — YIN** (de Cheveigné & Kawahara, 2002): the
  difference function → cumulative-mean normalisation → absolute threshold →
  **parabolic interpolation** for sub-Hz accuracy (measures a 200 Hz tone within
  1 Hz), with a clarity score. Returns `hz = 0` on noise/silence — never invents
  a pitch. Readout: ƒ₀ (Hz), nearest **note + cents** (A4=440), period (ms), clarity.
- **Colour-coded frequency view** — a Hann-windowed radix-2 FFT spectrum drawn
  with **each column's hue = its frequency** (low→red, high→violet, log-scaled);
  perceptual (√) bar height; the measured fundamental marked in its own colour.
- **Edge triggering** (sigrok/PulseView-style) starts the trace at a rising
  zero-crossing so the waveform stands still; a calibrated 10 × 8 division grid.
- **Zoom** 1×–32× (＋/－ buttons or mouse-wheel over the trace) to inspect a
  single glottal period.
- **Forensic tools (🔬)** computed in-browser (standalone, no voaice peer needed):
  spectral **centroid**, **rolloff**, **HNR** (Boersma/Praat autocorrelation, with
  a voiced/mixed/noise reading), Vpp, Vrms, ZCR.
- **12 oscilloscope tests** against synthetic signals with known answers (FFT bin,
  YIN across the vocal range + noise rejection, trigger, Vpp/Vrms, centroid/rolloff,
  HNR, notes, colour map). Suite green: 100.

Detail: [docs/OSCILLOSCOPE.md](./docs/OSCILLOSCOPE.md).

---

## [2.10.0] — 2026-07-17

### Added — WebGL rendering, on the DeltaVerse substrate

The 2D path paints triangles on the CPU with an affine texture warp — flat, with
faint seams. WebGL draws the same mesh on the **GPU**: a perspective camera with
real depth, and perspective-correct texture interpolation (seam-free).

- **Aligned to the existing DeltaVerse substrate, reviewed first.** `dapp/deltaverse.js`
  (the participant field the realm doorway uses) is deliberately **raw WebGL** —
  inline shaders + a 2D-canvas fallback so it always shows, *not* three.js. The
  faicey face renderer follows the same doctrine rather than pulling in three.js's
  ~2 MB: a face is drawn with the same lightweight WebGL technology that draws its
  participants.
- **`src/face_clone/webgl_face.js`**:
  - `buildFaceGeometry(landmarks, { topology, uvSource })` → the four GPU buffers
    (positions centred/unit-scaled/**Y-flipped**/nose-forward, indices from the
    Delaunay topology, uvs from the capture frame flipped for GL, smooth normals).
  - a tiny tested **mat4** (`m4perspective` / `m4rotationY` / `m4translation` /
    `m4multiply`) for the MVP.
  - `WebGLFaceRenderer` — raw `getContext('webgl')`, inline GLSL (lit + optionally
    textured mesh), `.ok=false` → the caller falls back to the 2D shaded surface.
    16-bit indices when the mesh fits, so no `OES_element_index_uint` on WebGL1.
- **`webgl` render mode** in the demo, on its own `#face3d` canvas: builds the
  geometry each frame from the expressed landmarks + cached topology, textures it
  with the captured frame (or the live video), and turns the head gently so the
  depth reads. Falls back to the 2D shaded surface when WebGL is unavailable, and
  says so. Persona payload records the `webgl-gpu` backend.
- **10 webgl_face tests** (buffer sizes; centred + Y-flipped positions; UVs from
  the source, flipped, in [0,1]; unit normals; null-landmark safe; the mat4
  helpers). Suite green: 88.

### What it earns

WebGL is a better *rendering* of the same measured mesh — not neural synthesis. A
GPU-textured capture still grades to **realism**; the fidelity gate treats
`webgl-gpu` like the affine backend, and hyperreal stays reserved for a measured
neural render. Detail: [docs/WEBGL_RENDER.md](./docs/WEBGL_RENDER.md).

---

## [2.9.0] — 2026-07-17

### Changed — solid hardware handling: every camera + mic, and live facial recognition

The demo's device and recogniser wiring was fragile — the landmarker was rebuilt
on every toggle, errors were swallowed, there was no way to pick a device, and no
feedback on whether a face was actually being tracked. Rebuilt end to end.

- **Every camera and microphone is recognised.** `enumerateDevices()` lists all
  video + audio inputs into two selectors, with a live count ("N cameras · M mics
  recognised"). Labels populate after the first grant; the list re-scans on
  `devicechange` (plug/unplug). Picking a device passes `deviceId: { exact }`, and
  changing it while live restarts cleanly on the new device.
- **Facial recognition is built once, warmed at startup, and reused** (it was
  recreated on every camera-on). A status line reports its real state:
  *warming up → loading the 478-landmark model → ready*, or *unavailable* with the
  reason. The model + WASM are vendored and served locally (no CDN).
- **Live tracking indicator** — a dot that goes green *"● face tracked · 478
  landmarks"* when the recogniser has a face, amber *"○ no face — centre in frame"*
  when it doesn't. `detectForVideo` is guarded on the video actually having a
  frame, and a persistent tracking error surfaces instead of being swallowed.
- **Honest, specific errors** — permission denied vs device-in-use vs unavailable
  vs insecure context (cameras/mics need HTTPS or localhost), and the AudioContext
  is resumed if the browser suspended it. Secure-context + no-media-API are
  detected up front.
- Docs: [docs/HARDWARE.md](./docs/HARDWARE.md).

Served end-to-end at `/face`; the demo, the modules, the MediaPipe bundle, the
model and the WASM all verified `200`. Suite unchanged and green: 78.

---

## [2.8.0] — 2026-07-17

### Added — the classical enhancement fallback

The gap between "neural dormant" (raw affine composite) and "neural loaded"
(hyperreal-capable) had an honest, weight-free filler: classical DSP that fixes
the affine composite's two real defects — triangle **seams** and **softness**.
(`src/face_clone/classical_enhance.js`.)

- **`enhanceClassical`** — `featherSeams` (edge-softening blend) → `unsharpMask`
  (restore detail) → `toneCurve` (gentle contrast). All built on a separable
  `boxBlur`; pure, deterministic, no weights / ONNX / GPU.
- **`ClassicalEnhancer`** — the same shape as `NeuralRenderer` (`describe` /
  `refine`), **always available**, honestly labeled `classical`. A **real
  improvement** over the raw composite — and the fidelity gate caps it at
  `realism` **by construction** (`classical` is not `neural`, so it can never
  earn `hyperreal`). The middle rung: better than raw affine, still not synthesis.
- In the demo's **neural** mode the fallback runs whenever no model is loaded,
  with a checkbox to compare raw affine vs enhanced; the badge states the verdict.
  The persona payload records `backend: 'classical'` accordingly.
- **`GET /api/render/neural/status`** now reports both the dormant neural backend
  and the available classical fallback.
- **7 classical_enhance tests** — each DSP op proven (constant image unchanged,
  impulse spread, edge overshoot, tone off-mid, seam softened) plus the doctrine
  lock: the gate refuses `hyperreal` to the classical backend at any score. Suite
  green: 78.

---

## [2.7.0] — 2026-07-17

### Added — the neural renderer, gated

The photoreal renderer reaches *realism*. Hyperrealism needs a neural renderer,
and this ships that **capability behind a gate** — not a hyperrealism claim.
(`src/face_clone/neural_render.js`.)

- **`NeuralRenderer`** — a pluggable backend that runs a **real ONNX model** when
  an operator provides a runtime + weights, and is **dormant** otherwise (an
  honest passthrough of the affine composite). **No weights are committed** — the
  same doctrine as voaice's ONNX voices and mindXtrain's dormant CPU bridge.
  Inference contract: NCHW float32 RGB `[0,1]` in, same-shape out. Activatable
  live via `window.faiceyNeural`.
- **`gradeFidelity` — the fidelity gate (the doctrine, made mechanical).** A
  render is **measured** — identity consistency (faceprint-vector), structural
  similarity (SSIM), coverage — and `hyperreal` is stamped **only** when a
  *neural* backend clears all three published thresholds (`FIDELITY`
  0.85 / 0.90 / 0.80). By construction the affine/classical path caps at
  `realism`, no-texture at `surface`, and a neural render that doesn't measure up
  is capped too, with the failing measure named. Hyperrealism is **earned, never
  asserted**.
- Metrics: `identityConsistency`, `structuralSimilarity`, `renderCoverage` — real
  and testable.
- **`neural`** render mode in the demo: draws the affine composite (realism) and,
  *only if a model is loaded*, refines it — with an honest badge ("neural renderer
  dormant — realism via affine · load weights to earn hyperreal"). The persona
  payload records the measured render verdict, not an asserted tier.
- **`GET /api/render/neural/status`** — honest capability report + gate thresholds.
- **12 neural_render tests**, incl. the boundary that *only* a neural render can
  earn hyperreal and that the thresholds don't silently relax. Suite green: 71.

### Honest status

Hyperrealism is **not achieved** on this host — it is made *reachable and safe*:
the seam runs a real model when one is provided, and the gate guarantees the
"hyperreal" label can only ever be earned by measurement. The aivatar tier ladder
is now complete in *mechanism* (basic → professional → scientific realism →
scientific hyperrealism); the top rung exists but climbing it needs a loaded
neural model + signed provenance. Full detail:
[docs/NEURAL_RENDERER.md](./docs/NEURAL_RENDERER.md).

---

## [2.6.0] — 2026-07-17

### Added

- **The photoreal renderer — the FACE is no longer only a wireframe**
  (`src/face_clone/render_surface.js` + `drawFaceSurface` in `contours.js`). Two
  honest render modes, both on one mesh:
  - **surface** — the mesh shaded as a solid. Each triangle's real 3D normal (from
    the landmark `z` relief) is lit (Lambert + ambient) and modulates the skin
    base; triangles paint back-to-front. A rendered face, still synthetic geometry.
  - **photoreal** — the person's **captured frame**, affine-mapped per triangle
    onto the measured mesh. Real texture on real geometry, so it is genuine
    *photographic* realism of the capture — and because the UVs are tied to
    landmark indices, it **re-warps as the face expresses** (an emotion, or the
    cloned voice driving the mouth): the cloned face emotes photoreally. With the
    webcam live and no capture yet, the live frame textures itself — live
    reenactment for free.
- **`surface` / `photoreal`** in the demo's **render** dropdown, plus a live
  photoreal hint. `◉ capture my face` now snapshots the frame as the photoreal
  texture; the persona payload records the actual `render` mode + `photoreal` flag.
- The mesh is a stable **Delaunay** topology (`triangulate`), cached from the base
  geometry so expressions deform it instead of re-triangulating (no flicker).
- **8 render_surface tests** — the Delaunay mesh is valid (empty-circumcircle, no
  degenerate triangles); `affineFromTriangle` maps every source corner **exactly**
  onto its destination and rejects a colinear source; shading normals are unit and
  shades stay in `[ambient, 1]`; topology reuse keeps the mesh stable while an
  expression deforms it; `shadeColor`/`paintOrder` behave. Suite green: 59 tests.

### Honest boundary

This is **not** neural view-synthesis. It cannot invent occluded or novel views,
and it makes **no claim** to "hyperrealism indistinguishable from reality" — that
tier needs a neural renderer (a labeled future). The renderer raises what the FACE
can *present* (a captured FAICE reaches **realism**), not what faicey *measures*;
the earned aivatar tier still rests on capture accuracy + signed provenance. Full
detail: [docs/PHOTOREAL_RENDER.md](./docs/PHOTOREAL_RENDER.md).

---

## [2.5.1] — 2026-07-17

### Docs

- **The iNFT minting path is documented end to end** — [docs/INFT_MINTING.md](./docs/INFT_MINTING.md):
  the artifact → payload (`inft.js`) → transaction (`minter.js`) → wallet flow,
  the two function selectors, the viem-verified ABI encoder, the `attachThotRoot`
  lineage follow-up, and the doctrine boundary (faicey builds the transaction;
  the wallet owner signs and broadcasts it). Deployment status noted: local anvil
  only, mainnet awaits the OVERLORD ceremony.
- **README changelog pointer refreshed** — it had frozen at v2.1.0; it now names
  the arc through 2.5 (webcam→FAICE capture, the cloned face speaking in the
  cloned voice, the ERC-7857 payload wired to a submittable mint) and links the
  new iNFT doc.
- **`docs/FACE_CLONE.md`** — the print pipeline now points at the on-chain path,
  so the persona doc and the mint doc cross-reference.

---

## [2.5.0] — 2026-07-17

### Added

- **The mint payload is wired to the DeltaVerse minter** (`src/face_clone/minter.js`).
  `toMintTx()` turns an iNFT payload into a ready-to-broadcast transaction — the
  `to` (the deployed iNFT_7857 address), the ABI-encoded `data`, and the chain —
  exactly what a wallet's `eth_sendTransaction` or viem's `sendTransaction` takes.
  A minimal, self-contained ABI encoder handles the two calls (`mintAgent`,
  `attachThotRoot`) with the selectors read from the compiled artifact, so no
  keccak is needed in the browser. **The encoder was cross-checked byte-for-byte
  against viem**, and an in-repo round-trip decode test locks it. A `thotRoot`
  becomes a second `attachThotRoot(tokenId, …)` transaction to link mindX's
  memory lineage after the mint.
- **`⛓ mint`** in the demo — after `⬡ iNFT payload`, this connects the browser
  wallet, builds the transaction, and submits it for the owner to **sign and
  approve in their own wallet**. No keys are held and nothing is auto-submitted:
  the tool builds the transaction, the mint is the wallet owner's action. The
  deployed iNFT_7857 address is editable (defaults to the recognised contract).
- **5 minter tests** — the calldata decodes back to the payload (a real, valid
  transaction), the THOT root becomes a tokenId-parameterised follow-up, and the
  owner defaults to the sender.

---

## [2.4.0] — 2026-07-17

### Added

- **DeltaVerse iNFT (ERC-7857) integration.** The NFT export was OpenSea metadata
  and the `export:nft` script pointed at a file that didn't exist. `src/face_clone/inft.js`
  now binds a faicey artifact — a faceprint, a voiceprint, or a bound persona — to
  the DeltaVerse Intelligent-NFT contract (`daio/contracts/inft/iNFT_7857.sol`):
  the print's reproducible hash IS the iNFT's `contentRoot`, and the exact
  `mintAgent(to, contentRoot, storageURI, metadataRoot, dimensions, parallelUnits,
  sealedKeyHash, tokenURI_)` argument set falls straight out — with a valid
  ERC-7857 embedding dimension, an optional `attachThotRoot` for mindX's memory
  lineage, and the measurement vector travelling in the tokenURI metadata.
- **`⬡ iNFT payload`** in the demo (next to `⭳ .persona`) — binds the persona as
  an ERC-7857 mint payload, client-side, and downloads it ready for the DeltaVerse
  minter (set the owner + storage URI).
- **`/api/inft/mint-payload`** on the faicey server — build the payload from a
  posted print/persona (for the blockchain agent factory).
- **`scripts/export-nft-metadata.js`** rebuilt — `npm run export:nft` now works:
  reads a `.persona` (or a print) and writes the iNFT-7857 payload. 6 iNFT tests.

---

## [2.3.0] — 2026-07-17

### Added

- **The avatar speaks — the cloned face expresses from the cloned voice.** A new
  `/api/speak` endpoint synthesises text (voaice Python TTS), shapes the voice
  toward the captured voiceprint's F0 (VoiceShaper pitch — so the avatar speaks
  in ~its own voice, guarded to plausible speech fundamentals so a harmonic
  misread can't over-shift), and returns the samples plus the utterance's
  **emotion→FACE params** (voaice's `toFace` fan-out — the emotion vocabulary is
  identical on both sides, so it maps cleanly).
- **`🗣 speak`** in the live demo: the avatar synthesises the text, plays it
  through a Web Audio analyser, and drives **lip-sync + expression from the
  playing speech** — the mouth opens on the speech's inflection (the same
  fast-attack envelope the mic uses), the face wears the utterance's emotion, and
  the mouth oscilloscope shows the spoken waveform between the lips. The captured
  face (from `◉ capture my face`) is the speaker: it looks like the person and
  now speaks and emotes in the cloned voice. Falls back to the browser's
  SpeechSynthesis when the voaice TTS peer is offline.

This closes the aivatar next-release spec: accurate webcam→FAICE (2.2.0) + Python
TTS/STT (voaice 3.1–3.2) + the cloned face expressing from the cloned voice.

---

## [2.2.0] — 2026-07-17

### Added

- **Accurate webcam → FAICE mapping** (`src/face_clone/capture.js`). A single
  webcam frame is noisy — the landmarks jitter, the head is rarely dead-on.
  `FaceCapture` accumulates a window of frames, drops the ones too turned to
  trust, and folds the rest into ONE stable, pose-normalised face (the person's
  actual geometry) via frontality-weighted per-vertex averaging. Then it
  **measures** how accurate that capture is — per-vertex spread across frames
  (jitter), mean frontality, coverage → one 0..1 score with a verdict
  (accurate / good / rough / insufficient). The accuracy becomes the faceprint's
  precision, so a jittery capture grades to a lower tier in aivatar rather than
  claiming a fidelity it doesn't have.
- **`◉ capture my face → FAICE`** in the live demo. Holds a 3-second capture,
  binds the aggregated face as the avatar (the FACE becomes the person), reports
  the accuracy score, and drives the same expression + mouth-oscilloscope
  pipeline — the captured face then emotes and lip-syncs. The persona *clone*
  flow now binds this accurate aggregated print instead of re-measuring a single
  live frame; the demo requests MediaPipe's transformation matrix (needed for
  pose normalisation).
- 6 capture tests: a stable/frontal capture measures accurate, a jittery/turned
  one measures rough, accuracy rises with cleaner frames, and averaging is
  provably tighter than any lone frame.

---

## [2.1.2] — 2026-07-16

### Added

- **Richer facial features on the procedural face.** The neutral face gained
  detail: almond eyes with a taller upper lid, **iris rings** (a visible iris,
  not a dot), **angled brows** that peak inner and taper down the outer tail, a
  nose with **alar wings**, an **inner lip line** (the mouth opening, so the lips
  read as two lips), and **ears** — synthetic helices above the MediaPipe range,
  present on the procedural face and silently absent on a real clone (which has
  no ear mesh). Placed at the canonical topology, so expressions and webcam
  clones drive them unchanged.
- **The mouth is its own oscilloscope.** When the mic is on, the live voice
  waveform is drawn **between the lips**, clipped to the outer lip contour
  (`drawMouthScope`), using the same fit transform as the face — so it lands
  exactly on the rendered mouth.
- **Inflection-driven mouth.** The mouth opens on level but *pops* on a syllable
  onset (a sudden rise in energy) and eases shut — fast attack, slow release —
  so it expands with vocal inflection rather than tracking raw amplitude.

### Fixed / hardened

- **`/api/voice/measure` input validation.** The samples payload is now bounded
  (≤ 30 s) and sanitised (non-finite values → 0, clamped to [-1, 1]), and the
  sample rate is range-checked (8000–96000). A large or malformed body can no
  longer allocate an unbounded buffer or measure garbage.
- Persona download filenames are sanitised (already noted in 2.1.1; the code
  landed here).

---

## [2.1.1] — 2026-07-16

### Fixed

- **Consent integrity in the persona create flow.** `Create` resolved its face
  as `live || base` — so with the webcam on, inventing a "synthetic" persona
  would bind your **real** face while stamping consent `synthetic` ("no real
  subject") and `source: 'procedural'`. That is a provenance lie. Create now
  binds the procedural face **only**; cloning a real face is what the clone path
  (consent `self`) is for. The UI also says so when the webcam is on during a
  create.

### Added

- **Scientific voiceprint measurement in the demo.** A recording is now measured
  through the real **voaice** `Forensic.voiceprint` — the six SoundWave measures
  (dominant frequency, amplitude, spectral centroid, spectral rolloff,
  zero-crossing rate, harmonic-to-noise ratio) at 18 dp, plus an integrity
  verdict — via `POST /api/voice/measure`. When the voaice peer isn't present
  (e.g. a standalone clone) it degrades to the labelled browser estimate.
- **Oscilloscope matching.** Set one voiceprint as a reference, record another,
  and `≈ match` compares them with voaice's `Forensic.compare` (`POST
  /api/voice/match`) — a match / probable / inconclusive / different verdict with
  a similarity score — while both waveforms are overlaid on the oscilloscope.
- Download filenames are sanitised.

---

## [2.1.0] — 2026-07-16

**The demo face became an actual face, and it can make a persona.** This release
turns the demo from a schematic into a real, driveable FACE — with live hardware
and an in-browser `.persona` create/clone flow — and hardens the engine that
serves it.

### Added

- **A real procedural face** (`src/face_clone/neutral_face.js`). The demo used to
  render a ~30-point schematic blob. It now synthesises an anatomical neutral
  face — almond eyes, brow arcs, a nose with bridge, tip and nostrils, cupid's-bow
  lips, iris accents — placed at the **canonical MediaPipe indices**. Because it
  lives at the same topology a cloned face carries, the existing renderers and the
  nine-emotion expression system drive it unchanged.
- **The live FACE demo** at `/face` (`face-demo.html`):
  - the real face, rendered through the contour loops (visible features);
  - nine real expressions with auto-cycle (FACS-shaped deltas);
  - **🎥 webcam ON/OFF** — live MediaPipe reenactment when vendored, neutral otherwise;
  - **🎙️ mic ON/OFF** — drives the mouth and the oscilloscope;
  - **a voiceprint oscilloscope** — live waveform, and `⏺ record 3s` → an 18-dp
    signature (pitch / rms / centroid / zcr, sha256).
- **Persona create / clone, in the browser.** `✦ Create` invents a synthetic
  persona from the procedural face; `⎘ Clone` binds a captured webcam face and
  recorded voice under an explicit consent affirmation. `proportions → faceprint`,
  the voiceprint shaped alike, and `personaPrint()` unites them into one persona
  hash + ERC-7857 register args — deterministic, and emitted as a v2-shaped,
  [aivatar](https://github.com/Professor-Codephreak/aivatar)-compatible `.persona`
  (downloadable; print POSTed to `/api/persona`). Stamped tier `basic` with a note
  to re-grade in aivatar for the earned tier + signed provenance.

### Fixed

- **The neutral face produced a degenerate faceprint.** The zygomatic cheekbone
  indices (116 / 345) sit in no contour loop and were never placed, so
  `cheekRatio` measured **0** — one dead axis in every faceprint derived from the
  neutral face. Now placed; a new test asserts every proportion is finite and
  positive, and that the neutral face binds into a valid persona.
- **The demo server crashed under Node.** `FaiceyCore`'s constructor
  fire-and-forgot `init()`, which touched `window`; the unhandled rejection killed
  the process a beat after it bound the port. The constructor now carries its own
  `catch`, and `init()` skips the browser subsystems when there is no DOM,
  reporting headless rather than hiding it.
- Voiceprint `precisionScore` now uses the exact BigInt `toFixed18` idiom (matching
  faceprint / Scientific) so the two prints combine without precision drift.
- Removed an unused import; made the engine test runner await async cases.

### Changed

- `npm test` now also runs the neutral-face suite (9 tests) alongside the smoke
  and autocapture suites.

---

## [2.0.0] — 2026-07-13

- Standalone publish and audit hardening: `node_modules` untracked (it had been
  committed before `.gitignore` existed), the `pitch-detector` import corrected
  (it crashed the module under Node), hardcoded host paths made portable, LICENSE
  added, and a real smoke test where `npm test` had pointed at a nonexistent file.
- Guided **AUTO webcam capture** (`src/face_clone/autocapture.js`): a pose-tracked
  state machine that snaps front / left / right hands-free, then clones.

## [2.0.0-prior]

- The face-clone engine: clone from image, perspectives, video, or webcam →
  wireframe + 18-dp faceprint; the Faice facet→FACE service; the canonical
  wireframe engine consumed from `facerig`.
