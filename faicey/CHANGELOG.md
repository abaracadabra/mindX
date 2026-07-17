# Changelog

All notable changes to **faicey**. Versions follow [semver](https://semver.org).

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
