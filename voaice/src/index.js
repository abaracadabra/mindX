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

// TTS / voice synthesis loads lazily — it spawns OS TTS engines and is not needed for
// pure analysis. Import directly from 'voaice/voice' when you need it.
export async function loadVoiceCreationEngine() {
  const mod = await import('./VoiceCreationEngine.js');
  return mod.VoiceCreationEngine;
}

export const VERSION = '0.1.0';
export const DESCRIPTION =
  'voaice — voice (spectrometer, frequency, oscilloscope, TTS), separated from faicey (face).';
