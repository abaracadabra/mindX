# voaice

**The complete voice stack for AI.** Speech in, speech out, measured throughout.

[![version](https://img.shields.io/badge/version-3.0.0-0a6?style=flat-square)](./CHANGELOG.md)
[![license](https://img.shields.io/badge/license-MIT-0a6?style=flat-square)](./LICENSE)
[![tests](https://img.shields.io/badge/tests-27%20offline-0a6?style=flat-square)](#testing)
[![required deps](https://img.shields.io/badge/required%20deps-0-0a6?style=flat-square)](#design-principles)

voaice is the **VOICE** peer of [faicey](https://github.com/Professor-Codephreak/faicey) (the FACE).
With facerig (the RIG) and the cognitive `.persona` (the MIND) they compose
**[aivatar](https://github.com/Professor-Codephreak/aivatar)** — a person's AI model that
looks, speaks, rigs and thinks.

> Face and voice are peers. Either runs, ships and evolves without the other.

---

## The stack

```
                 ┌──────────────────────────────────────────────┐
  microphone ──▶ │  IN       stt · noise                        │
  audio file     │           transcribe · segment · snr         │
                 │           denoise · gate · flatness          │
                 ├──────────────────────────────────────────────┤
                 │  MEASURE  scientific · forensic              │
                 │           18-dp registers · voiceprint       │
                 │           compare · integrity · custody      │
                 ├──────────────────────────────────────────────┤
                 │  SHAPE    editor · shaper                    │
                 │           trim · fade · normalise (LUFS)     │
                 │           pitch · formant · eq · compress    │
                 ├──────────────────────────────────────────────┤
  .wav .ogg  ◀── │  OUT      tts · exporter                     │
  speakers       │           neural → native → formant floor    │
                 │           16 / 24 / 32-float · quality tiers │
                 └──────────────────────────────────────────────┘
```

| Module | Import | Concern |
|---|---|---|
| **stt** | `voaice/stt` | speech to text — whisper.cpp · vosk · sherpa-onnx; utterance segmentation with zero dependencies |
| **noise** | `voaice/noise` | signal versus noise — SNR, learned noise profile, spectral-subtraction denoise, gate |
| **tts** | `voaice/tts` | text to speech — neural → native OS engines → in-house formant floor |
| **shaper** | `voaice/shaper` | the voice itself — pitch, time, formant, EQ, compression, de-essing |
| **editor** | `voaice/editor` | the timeline — trim, cut, join, fade, normalise (peak / LUFS); undoable |
| **forensic** | `voaice/forensic` | identity — voiceprint, speaker comparison, tamper screening, custody chain |
| **scientific** | `voaice` | measurement — 18-decimal fixed-point registers, reproducible hashes, on-chain ready |
| **exporter** | `voaice/exporter` | delivery — `.wav` 16/24/32-float, `.ogg` Vorbis, quality tiers |
| **oscilloscope** | `voaice/oscilloscope` | visualisation — d3 waveform and spectrum |

---

## Install

```bash
npm install voaice
npm run capability     # what can THIS host actually do?
```

Zero required dependencies. `d3` powers the oscilloscope; native speech engines, ffmpeg and
the ONNX runtime are **optional**, load lazily, and degrade along documented paths.

## Quick start

```js
import { STT, TTS, VoiceShaper, Forensic, exportClip, snr, denoise } from 'voaice';

// IN — is this recording even worth using?
const report = snr(clip.samples, clip.sampleRate);
//   → { snrDb, speechDb, noiseDb, verdict: 'clean' | 'usable' | 'noisy' | 'unusable' }
const cleaned = denoise(clip.samples, clip.sampleRate);
//   → { samples, snrBefore, snrAfter }   (refuses to invent a profile if there is no silence)

// IN — what was said, and where?
const stt = new STT({ model: '/models/ggml-base.en.bin' });
const { any } = await stt.available();
const heard = any
  ? await stt.transcribe(clip)   // { text, engine, segments }
  : stt.segment(clip);           // { segments, speechSec, snr } — never a fabricated transcript

// OUT — speak, in whatever voice this host can produce
const tts = new TTS({ engine: 'auto', voice: 'jaimla' });
const spoken = await tts.speak('the machine speaks for itself');
//   → { samples, sampleRate, engine }   — always tells you which engine produced it

// SHAPE — make it a person, not a preset
const shaped = new VoiceShaper(spoken)
  .pitchShift(-2)                                        // constant duration
  .formantShift(1.05)                                    // vocal tract, independent of pitch
  .eq({ type: 'peaking', freq: 3000, gainDb: 3, q: 1 })  // presence
  .compress({ thresholdDb: -18, ratio: 3 })
  .deEss()
  .toClip();

// MEASURE — prove who it is
const forensic = new Forensic({ sampleRate: shaped.sampleRate });
const print = forensic.voiceprint(shaped.samples);
const match = Forensic.compare(print, referencePrint);
//   → { similarity, verdict: 'match' | 'probable' | 'inconclusive' | 'different' }

// OUT — deliver at a stated quality
await exportClip(shaped, { format: 'ogg', quality: 'studio', path: 'out.ogg' });
```

---

## Design principles

**Honest capability.** Every module probes the host and reports what it can do *before* you
depend on it: `TTS.capability()`, `STT.available()`, `oggAvailable()`. Nothing pretends.

**Honest refusal.** `STT.transcribe()` throws — with an install hint — rather than invent a
transcript when no recogniser exists. `denoise()` returns the input unchanged rather than
invent a noise profile when a clip contains no silence. A wrong answer is worse than no
answer: it propagates silently into everything downstream.

**Honest floor.** Where a floor can exist, it does. TTS always speaks — neural, then the OS
engines, then the in-house formant synthesiser, which needs nothing at all. STT always
segments, even when it cannot transcribe. Degradation is a documented path, never a crash.

**In-house DSP.** FFT, spectrometer, LUFS (ITU-R BS.1770-4), VAD, WSOLA time and pitch,
RBJ biquads, spectral subtraction — written here, dependency-free. No torch, no Python,
no CDN. Optional accelerators are exactly that.

**Measurement, not assertion.** `Scientific` emits 18-decimal fixed-point registers with
reproducible hashes — the same values a contract call takes. `Forensic` turns them into
identity, comparison, tamper screening and a hash-linked chain of custody. Claims about a
voice are backed by numbers, or they are not made.

---

## Neural voices and cloning

```js
const NeuralVoiceEngine = await (await import('voaice')).loadNeuralVoiceEngine();
const engine = new NeuralVoiceEngine({ voiceId: 'jaimla' });
const cloned = await engine.clone({ referenceClip });   // zero-shot, torch-free ONNX, CPU
```

Weights are fetched on demand (`npm run fetch-models`) and **never committed** — they carry
their own upstream licences ([MODELS.md](./MODELS.md)). Absent them, the engine degrades to
the dependency-free path and says so.

## Testing

```bash
npm test          # 27 offline checks, seconds — no models, no network
npm run test:all  # adds the neural suite (loads real weights when present)
```

The suites hold the design principles, not merely the code paths: that STT refuses to
fabricate, that `denoise` refuses to invent a profile, that the formant floor always
produces audible speech, that pitch shifting preserves duration and time stretching
preserves pitch.

## Demo server

```bash
node server.js    # http://localhost:7350 — spectrometer + oscilloscope, d3 served locally
```

---

## Documentation

- **[CHANGELOG.md](./CHANGELOG.md)** — v3.0.0 release notes, including the four DSP bugs the
  v3 suite surfaced and fixed
- **[MODELS.md](./MODELS.md)** — neural weights, provenance, licences
- **[aivatar](https://github.com/Professor-Codephreak/aivatar)** — where the voice becomes a
  being: earned fidelity tiers (basic · professional · scientific → realism · hyperrealism),
  consent, custody chain, signed provenance

## Lineage

Voice concerns separated out of [faicey](https://github.com/Professor-Codephreak/faicey)
(2026-06); the complete stack cut as v3 (2026-07).

---

**© Professor Codephreak** — [rage.pythai.net](https://rage.pythai.net) · MIT
