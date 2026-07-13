# voaice

**The voice of an AI service.** Spectrometer · frequency manipulation · oscilloscope · TTS.

voaice is the agnostic **peer** of [`faicey`](../faicey) (the *face*). Where faicey renders
the wireframe FACE of an agent, voaice owns everything about the **voice**: real-time spectral
analysis, frequency manipulation, the d3 oscilloscope, pitch detection, and text-to-speech.
They were one entangled module; they are now two independent concerns — either can run, ship,
and evolve without the other.

> Face and voice are peers. mindX is one consumer, not the only home.

## Design

- **In-house DSP floor, zero required external deps.** `src/dsp/fft.js` is a from-scratch
  radix-2 FFT; `VoiceAnalyzer` computes RMS, peak, dominant frequency, spectral
  centroid/rolloff/flatness, zero-crossing rate and an autocorrelation pitch estimate with
  nothing but Node. An isolated build needs no native modules to analyse audio.
- **d3 for the oscilloscope only.** Served locally — never from a CDN.
- **Optional accelerators.** `meyda` / `audiomotion-analyzer` are `optionalDependencies`; voaice
  works fully without them. External SDKs are added only when an in-house adaptation can't do
  the job.

## Usage

```js
import { VoiceAnalyzer, Oscilloscope } from 'voaice';

const analyzer = new VoiceAnalyzer({ sampleRate: 44100, fftSize: 2048 });
const features = analyzer.analyze(frame);   // frame: Float32Array in [-1,1]
// -> { rms, peak, zcr, pitch, dominantFrequency, spectralCentroid, spectralRolloff, flatness, magnitude }

// Frequency manipulation (pure):
const up = VoiceAnalyzer.pitchShiftSemitones(frame, +5);

// Oscilloscope (server-side path, no d3 needed):
const d = Oscilloscope.waveformPath(frame, 800, 240);
```

Run the standalone demo server (spectrometer + oscilloscope, d3 served locally):

```bash
node server.js          # http://localhost:7350
```

## Module map

| Path | Concern |
|------|---------|
| `src/dsp/fft.js` | in-house FFT + spectral helpers (no deps) |
| `src/VoiceAnalyzer.js` | spectrometer + frequency manipulation |
| `src/Oscilloscope.js` | waveform/spectrum rendering (pure + d3 browser renderer) |
| `src/VoiceCreationEngine.js` | TTS (espeak-ng / festival / flite / pico2wave) |
| `server.js` | standalone voice demo server |

## Lineage

Voice concerns separated out of `faicey` (2026-06). Agnostic homes:
github.com/javascriptit · github.com/interplanetaryfilesystem · github.com/mlodular.

© Professor Codephreak — rage.pythai.net

## Forensic · Editor · Exporter (aivatar voice tools)

The aivatar service needs the voice to be **measurable, editable, and evidentiary** —
these three modules complete that (2026-07-13):

- **`voaice/forensic`** — `Forensic` class: aggregate `voiceprint()` identity (18-dp
  registers, reproducible sha256), `Forensic.compare()` speaker similarity with verdict
  bands (match / probable / inconclusive / different), `integrity()` tamper/splice
  screening (discontinuity z-scores, clipping, DC offset), and `custody()` hash-linked
  chain-of-custody records. Same measurement substrate as `Scientific` — evidence and
  SoundWaveToken registration share one shape.
- **`voaice/editor`** — non-destructive clip editing: `slice/cut/insert/concat/gain/
  fadeIn/fadeOut/normalize (peak | LUFS)/reverse/resample/removeSilence`, plus the
  chainable, undoable `AudioEditor` session.
- **`voaice/exporter`** — quality-tiered export: `.wav` in-house (16/24/32-float) and
  `.ogg` Vorbis via the system ffmpeg (`oggAvailable()` reports honestly). Tiers:
  `low` 22.05k/16 · `medium` 44.1k/16 · `high` 48k/24 · `studio` 48k/32f — or pass
  explicit `settings`. Cloning stays in `voaice/neural`; clone → edit → verify
  (forensic) → export is the full aivatar voice pipeline.

Fast suite: `npm run test:fast` (synthetic signals, no models, sub-second).
