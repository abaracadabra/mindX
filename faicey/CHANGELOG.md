# Changelog

All notable changes to **faicey**. Versions follow [semver](https://semver.org).

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
