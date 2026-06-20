# voaice neural models (CPU / ONNX, torch-free)

The neural voice engine (`voaice/neural`, `src/NeuralVoiceEngine.js`) runs small ONNX models on
CPU. **No torch, no transformers, no Python.** The engine code is in-house/clean-room; the **model
weights are third-party** (their own licenses) and are *not* committed — fetch them on demand.

## Backends (preference order)

The engine resolves the best available backend at `init()` and reports it as `capability.backend`:

1. **`sherpa`** — **the real production path.** Wraps `sherpa-onnx-node` (k2-fsa/sherpa-onnx,
   **Apache-2.0**), a C++ binding over ONNX Runtime. Gives genuine CPU TTS + zero-shot cloning and
   **bundles espeak-ng-data**, so no system `espeak-ng` is required.
   - **Kokoro** bundle → preset multi-speaker voices (24 kHz).
   - **ZipVoice** bundle → zero-shot voice cloning from a reference clip **+ its transcript**.
2. **`onnx`** — hand-rolled `onnxruntime-node` wrappers (`src/onnx/{kokoro,tone_color}.js`). The
   Kokoro path is solid; the OpenVoice tone-color path is **experimental** (see note below). Kept as
   a fallback that avoids the sherpa native dep.
3. **`formant`** — **model-free REAL speech** (`src/tts/formant.js`): a clean-room Klatt-style
   source-filter synthesizer (voiced glottal pulse + noise → cascade formant resonators) with a
   Peterson–Barney vowel/consonant table, a compact English letter-to-sound reciter, F0 contour, and
   coarticulation. Intelligible (retro/robotic) speech with **zero model download**, node + browser.
   This is the default when no neural weights are present — it speaks for real, not a tone.
   *Clean-room provenance:* built only from public-domain Klatt 1980 + Peterson–Barney references; no
   GPL espeak/gnuspeech and no abandonware SAM code was copied.
4. **`fallback`** — dependency-free persona-tinted tone (**not speech**); the ultimate guard, reached
   only if formant is explicitly disabled (`{ formant: false }`).

**Browser premium:** the `/studio` "native voice" toggle uses the **Web Speech API** (`speechSynthesis`)
for real OS voices — highest quality, zero download, browser-only (plays directly, so it bypasses the
oscilloscope visualizer). Emotion still maps to its `rate`/`pitch` and drives the face.

Every result carries `.backend` (e.g. `sherpa:kokoro`, `sherpa:zipvoice-clone`, `fallback(...)`);
`capability = { sherpa, ort, base, clone, backend }`.

## Install (CPU, torch-free)

```bash
cd voaice
npm i                  # onnxruntime-node + sherpa-onnx-node (optional deps, CPU)
npm run fetch-models   # downloads + extracts the sherpa Kokoro + ZipVoice bundles into ./models
```

`fetch-models` uses a built-in default manifest (sherpa-onnx GitHub releases) or your
`models/manifest.json`; archives are extracted with system `tar`. Override host with
`VOAICE_MODELS_BASE`. Fetch one group: `npm run fetch-models -- kokoro`.

## Layout (`./models/`)

| Backend / bundle | Files | Capability |
| ---------------- | ----- | ---------- |
| sherpa **kokoro/** | `model.onnx`, `voices.bin`, `tokens.txt`, `espeak-ng-data/` | preset voices (talk) |
| sherpa **zipvoice/** | `encoder.onnx`, `decoder.onnx`, `vocoder.onnx`, `tokens.txt`, `espeak-ng-data/`, `lexicon.txt` | zero-shot clone |
| onnx (alt) | `kokoro.onnx`, `voices.bin`, `kokoro.json` | preset voices |
| onnx (experimental) | `tone_encoder.onnx`, `tone_converter.onnx`, `tone_color.json` | tone-color clone |

## Model candidates & LICENSES — audit before redistribution

The engine is MIT (voaice). **The weights are not voaice's** — verify each before shipping audio:

- **Kokoro-82M** (preset TTS) — **Apache-2.0** weights; ONNX at `onnx-community/Kokoro-82M-ONNX`,
  `NeuML/kokoro-int8-onnx`. CPU-excellent (~80 MB int8), 24 kHz. Preset voices only.
- **ZipVoice** (zero-shot clone) — **Apache-2.0** (k2-fsa/ZipVoice). 123M, flow-matching, int8
  encoder/decoder + vocos vocoder. Reference WAV **+ transcript** + `numSteps` (4 ≈ fast). This is the
  genuinely deployable torch-free CPU cloning path.
- **Piper / VITS** — MIT engine; loads via sherpa as a `vits` model. Preset voices, fastest on edge CPU.

**Avoid for this engine:** XTTS-v2 (Coqui **CPML**, commercial-restricted; 30–50× slower than realtime
on CPU) and F5-TTS (**CC-BY-NC** weights; not CPU-realtime). Neither is torch-free in practice.

> **Experimental — OpenVoice v2 tone-color (`onnx` backend):** a *fully* torch-free CPU OpenVoice
> pipeline is currently DIY (community ONNX converter + a separate ONNX MeloTTS base), with no Node
> binding and quality left to the integrator. The `src/onnx/tone_color.js` wrapper is scaffolding for
> that path; **prefer the sherpa/ZipVoice clone path**, which actually ships.

## Emotion control (Chatterbox-shaped) → voice + faicey FACE

voaice **owns** emotion as `{ label, intensity }` and fans it out (`src/emotion.js`):

- **→ voice params** (`toVoiceParams`): Chatterbox's `exaggeration` (0..1, 0.5 = neutral, scaled by
  intensity), `cfg_weight`, `temperature`, plus a `prosody` nudge (pitch/speed) for non-emotive backends.
- **→ faicey FACE** (`toFace`): a faicey expression name + weight + hue, consumed directly by
  `faicey.setExpression(expression, weight)` / `FaiceyCore.targetExpression`.
- **paralinguistic tags** `[laugh]`/`[chuckle]`/`[cough]` (`extractTags`) → timed face triggers.

Because the FACE is driven from the SAME owned emotion, **the face emotes even when the audio backend
cannot** (Kokoro/ZipVoice have no emotion dial). Only the **Chatterbox** backend actuates the voice
params. Labels: `neutral, happy, excited, calm, sad, angry, surprised, confused, thinking`.

- **Chatterbox** (`onnx-community/chatterbox-ONNX`, **MIT**, ~350MB Q4) is the emotive voice backend —
  the `exaggeration` dial survives the ONNX export. **Honest:** it's a 0.5B autoregressive LM TTS,
  **slow on CPU (offline/batch, not live)**, so it is opt-in (used only when an emotion is requested and
  the bundle is present) and `src/onnx/chatterbox.js` requires a merged-graph export — the multi-graph
  AR port needs an external decode loop (run it as a sidecar). Emotion CONTROL + FACE display work
  regardless of whether Chatterbox is installed.

Endpoints: `GET /emotions` (labels + table; `?label=&intensity=` → fan-out), `POST /speak` accepts
`emotion`, and replies with an `X-Voaice-Emotion` header carrying the FACE descriptor + tags. The Studio
(`/studio`) has an emotion selector, the **exaggeration/intensity** knob, `[laugh]`/`[chuckle]`/`[cough]`
buttons, and a Persona that morphs (brows / eyes / mouth-curve / hue) to the emotion in sync with playback.
`faicey/src/integrations/VoiceyBridge.js` drives the 3D FACE from the same `speechGenerated` emotion.

## Honest risk

Zero-shot clone quality on a single CPU is the real unknown. The capability ladder contains it: with
no clone weights the engine still **talks** (Kokoro preset) and still measures a forensic voiceprint;
`needsText`/`backend` never overstate what ran.

## HTTP sidecar

`npm run serve` exposes the engine for voicey2 / faicey:

- `GET  /studio` → in-house **voaice Studio** (vanilla JS, no CDN): voice console (knobs/buttons),
  a wireframe **Persona whose mouth IS the live oscilloscope** (voice output → mouth motion),
  a **KITT mode** voice modulator, and the **scientific 18-decimal voiceprint** readout.
- `GET  /voices` → `{ voices, capability }` (capability includes the resolved `backend`)
- `POST /speak`  → `{ text, voiceId?, embeddingId?, speed?, numSteps? }` ⇒ `audio/wav` (+ `X-Voaice-Backend`)
- `POST /clone`  → raw `audio/wav` (+ `X-Reference-Text` header) **or** `{ wavBase64|wavPath, referenceText }`
  ⇒ `{ embeddingId, backend, needsText, voiceprint, registerArgs }`

Output is loudness-normalised (ITU-R BS.1770-4, target −20 LUFS); reference clips are VAD-trimmed and
normalised before cloning. `registerArgs` maps 1:1 to
`SoundWaveToken.registerVoicePrint(hash, sampleRate, uint256[6], precision)`.
