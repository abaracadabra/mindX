# Changelog

All notable changes to **faicey**. Versions follow [semver](https://semver.org).

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
