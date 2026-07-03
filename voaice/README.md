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
