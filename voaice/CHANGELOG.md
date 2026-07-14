# Changelog

All notable changes to **voaice**. Versions follow [semver](https://semver.org).

---

## [3.0.0] — 2026-07-14

**The complete voice stack.** v3 closes the loop: voice comes *in* (speech-to-text,
signal-versus-noise), and voice goes *out* (text-to-speech, shaping), with forensic
measurement, non-destructive editing and quality-tiered export in between. Every
path is modular, every engine loads lazily, and every capability is probed and
reported honestly before it is relied on.

### Added — input

- **`voaice/stt` — Speech to text.** One façade over `whisper.cpp`, `vosk` and
  `sherpa-onnx`, resolved at runtime.
  - **`transcribe()` refuses to invent a transcript** when no recogniser is
    installed: it throws with an install hint. A wrong transcript silently
    poisons everything downstream; no transcript does not.
  - **`segment()` is the zero-dependency floor** — VAD-driven utterance
    segmentation with timings, energy and per-segment SNR. It reports *where*
    the speech is and whether it is clean enough to be worth transcribing, and
    it never claims to be transcription.
- **`voaice/noise` — Signal versus noise.** `snr()` (speech/noise split with a
  graded verdict), `noiseProfile()` (learned from the clearly-quiet frames),
  `denoise()` (spectral subtraction with over-subtraction and a spectral floor),
  `gate()` (click-free noise gate), `spectralFlatness()`.
  - `denoise()` **refuses to invent a noise profile** when a clip contains no
    silence — it returns the input unchanged and says why.

### Added — output

- **`voaice/tts` — Text to speech.** Neural (torch-free ONNX) → native OS engines
  (`espeak-ng`, `festival`, `flite`, `pico2wave`, `say`, `piper`) → the in-house
  formant synthesiser. **There is always a voice**: a host with no speech binaries
  and no model weights still speaks — audibly synthetic, clearly labelled, never
  silently failing. Every result reports which engine produced it.
- **`voaice/shaper` — Voice shaping.** Editing the *voice*, not the timeline:
  `pitchShift` (constant duration), `timeStretch` (constant pitch), `formantShift`
  (vocal-tract size, independent of pitch — the thing that keeps a shifted voice
  human), RBJ-biquad `eq`, `compress`, `deEss`, `breath`. Chainable and undoable
  via `VoiceShaper`, matching the `AudioEditor` contract.

### Fixed — the forensic model

Building the v3 suites surfaced defects serious enough to be worth naming plainly.
A forensic tool that cries wolf on honest evidence is not a conservative tool; it
is a broken one.

- **`Forensic.integrity()` no longer condemns an honest recording for having
  pauses.** Every real capture starts and stops speaking, and each onset is a
  large, abrupt rise in level — a naive amplitude-jump detector calls all of them
  splices. The model is now sound: speech↔silence transitions are *ignored* (that
  is a person talking); a discontinuity is flagged only **inside a run of speech**
  (a cut within a sentence); and a **noise-floor shift** detector catches the real
  signature of stitched material — two different rooms in one file. It also no
  longer reports false splices on near-stationary audio, where the diff standard
  deviation collapses and ordinary numerical wobble scored as tampering.
- **`snr()` returns `null` with `verdict: 'unmeasurable'`** for a clip that
  contains no silence, instead of inventing a floor. Signal-to-noise is measured
  *against* a noise floor, and a clip with no pauses does not contain one. Supply
  `opts.noiseClip` — a few seconds of room tone, which is what a studio records
  first — and it becomes measurable again. Unmeasured is never passed off as zero.
- **`snr()` and `noiseProfile()` detect the floor with a tighter gate (15 dB)**
  than the speech VAD (35 dB). The speech VAD deliberately keeps quiet consonants;
  a floor detector that generous classifies the room itself as speech, then reports
  "unmeasurable" exactly when a clip is noisy enough to need the number.
- **`deEss()` rebuilt as a proper two-band crossover.** Subtracting a highpassed
  copy from the original does not work: the filter phase-shifts the extracted band,
  so the subtraction fails to cancel and can *add* energy at the target frequency.
- `Forensic.voiceprint()` evenly subsamples long clips (`maxFrames`, default 400)
  instead of analysing every frame. A few hundred well-spread frames describe a
  speaker as well as thousands, at a fraction of the cost.

### Changed

- `encodeWav()` takes `{ bitDepth: 16 | 24 | 32 }` (32 = IEEE float). Default
  remains 16-bit — existing callers are unaffected.
- Test suites split: `npm test` runs the fast, offline suites (27 checks, seconds).
  `npm run test:all` adds the neural suite, which loads real model weights when
  present.

### Package

`npm run capability` prints exactly what this host can synthesise and recognise.
15 export paths; zero required dependencies beyond `d3` (oscilloscope only).
Consumed by [aivatar](https://github.com/Professor-Codephreak/aivatar) ≥ 1.1.0, whose
capture-intake stage grades the room a reference was recorded in.

---

## [2.x] — 2026-07-13

- **`voaice/forensic`** — voiceprint identity, speaker comparison with verdict
  bands, tamper/splice screening, hash-linked chain-of-custody.
- **`voaice/editor`** — non-destructive clip operations plus an undoable
  `AudioEditor` session.
- **`voaice/exporter`** — quality-tiered export: `.wav` (16/24/32-float) in-house,
  `.ogg` Vorbis via the system ffmpeg, with an honest `oggAvailable()` gate.

## [0.1.0] — 2026-06

- Initial separation from faicey: in-house DSP (FFT, spectrometer, LUFS, VAD),
  `Scientific` 18-decimal measurement, oscilloscope, OS and neural TTS with
  zero-shot cloning.
