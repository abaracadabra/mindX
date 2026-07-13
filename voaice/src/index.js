/**
 * voaice — the VOICE of an AI service.
 *
 * Spectrometer, frequency manipulation, oscilloscope and TTS as an agnostic, in-house
 * Node.js + d3 module. This is the peer of `faicey` (the FACE): face and voice are
 * separate concerns, each independently runnable. mindX is one consumer, not the home.
 *
 *   import { VoiceAnalyzer, Oscilloscope, fft } from 'voaice';
 *
 * Core DSP (FFT, spectral features, frequency manipulation) is dependency-free; d3
 * powers the oscilloscope; meyda/audiomotion are optional accelerators only.
 */

export { VoiceAnalyzer } from './VoiceAnalyzer.js';
export { Scientific, toFixed18, fromFixed18 } from './Scientific.js';
export {
  Oscilloscope,
  waveformPath,
  spectrumBars,
  browserRenderer,
} from './Oscilloscope.js';
export {
  fft,
  hann,
  magnitudeSpectrum,
  binToHz,
  nextPow2,
} from './dsp/fft.js';

// WAV codec — zero-dep PCM encode/decode (output + reference-clip decode).
// encodeWav takes { bitDepth: 16|24|32 } for quality-tiered output.
export { encodeWav, decodeWav, frames } from './audio/wav.js';

// Forensic voice analysis — voiceprint identity, speaker comparison,
// tamper/splice screening, hash-linked chain-of-custody. Same 18-dp
// substrate as Scientific, so evidence and measurement share one shape.
export { Forensic } from './Forensic.js';

// Non-destructive editing — pure clip operations + an undoable session.
export {
  AudioEditor,
  slice,
  cut,
  insert,
  concat,
  gain,
  fadeIn,
  fadeOut,
  normalize,
  reverse,
  resample,
  removeSilence,
} from './Editor.js';

// Quality-tiered export — .wav in-house (16/24/32f), .ogg via system ffmpeg.
export { exportClip, toWav, toOgg, QUALITY, resolveQuality, oggAvailable } from './Exporter.js';

// Loudness (ITU-R BS.1770-4 LUFS) + VAD silence-trim — torch-free in-house DSP, used to
// level output and clean reference clips before cloning.
export { integratedLoudness, normalizeToLufs, kWeight, peak } from './audio/loudness.js';
export { trimSilence, voicedFrames, voicedRatio } from './audio/vad.js';

// TTS / voice synthesis loads lazily — it spawns OS TTS engines and is not needed for
// pure analysis. Import directly from 'voaice/voice' when you need it.
export async function loadVoiceCreationEngine() {
  const mod = await import('./VoiceCreationEngine.js');
  return mod.VoiceCreationEngine;
}

// Emotion model — Chatterbox-shaped emotion control fanned out to voice params + faicey FACE.
export {
  EMOTIONS,
  EMOTION_LABELS,
  PARALINGUISTIC_TAGS,
  resolveEmotion,
  toVoiceParams,
  toFace,
  fanOut,
  extractTags,
} from './emotion.js';

// Neural TTS + zero-shot voice cloning (torch-free ONNX, CPU). Loads lazily — pulls in the
// optional onnxruntime-node only when actually used; degrades to a dependency-free fallback
// source when the runtime or model weights are absent. Import from 'voaice/neural' directly,
// or via this loader to keep the analysis core import-light.
export async function loadNeuralVoiceEngine() {
  const mod = await import('./NeuralVoiceEngine.js');
  return mod.NeuralVoiceEngine;
}

export const VERSION = '0.1.0';
export const DESCRIPTION =
  'voaice — voice (spectrometer, frequency, oscilloscope, TTS), separated from faicey (face).';
