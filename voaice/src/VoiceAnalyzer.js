/**
 * VoiceAnalyzer — the spectrometer + frequency manipulation core of voaice.
 *
 * In-house, environment-agnostic spectral analysis: feed it a frame of PCM samples
 * (Float32/number[] in [-1,1]) and it returns RMS, peak, dominant frequency, spectral
 * centroid/rolloff/flatness, zero-crossing rate, a pitch estimate (autocorrelation),
 * and the magnitude spectrum. No Web Audio, no microphone, no browser — works in pure
 * Node so it runs anywhere (server, worker, isolated build).
 *
 * Frequency manipulation (shift / band gain / formant warp) is provided via static
 * helpers that operate on spectra or sample frames.
 *
 * Optional accelerators (meyda) are never imported here — this is the dependency floor.
 */

import { magnitudeSpectrum, binToHz, nextPow2 } from './dsp/fft.js';

export class VoiceAnalyzer {
  /**
   * @param {{sampleRate?: number, fftSize?: number, rolloffThreshold?: number}} [options]
   */
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 44100;
    this.fftSize = options.fftSize || 2048;
    this.rolloffThreshold = options.rolloffThreshold ?? 0.85;
  }

  /**
   * Analyse one frame of time-domain samples.
   * @param {Float32Array|number[]} frame samples in [-1, 1]
   * @returns {object} feature bundle
   */
  analyze(frame) {
    const n = frame.length;
    if (!n) return VoiceAnalyzer.emptyFeatures();

    // --- time-domain features ---
    let sumSq = 0;
    let peak = 0;
    let zeroCrossings = 0;
    for (let i = 0; i < n; i++) {
      const s = frame[i];
      sumSq += s * s;
      const a = Math.abs(s);
      if (a > peak) peak = a;
      if (i > 0 && (frame[i - 1] < 0) !== (s < 0)) zeroCrossings++;
    }
    const rms = Math.sqrt(sumSq / n);
    const zcr = zeroCrossings / n;

    // --- spectral features ---
    const mag = magnitudeSpectrum(frame);
    const fftN = nextPow2(n);
    let total = 0;
    let weighted = 0;
    let dominantBin = 0;
    let dominantMag = 0;
    for (let i = 1; i < mag.length; i++) {
      const m = mag[i];
      total += m;
      weighted += m * i;
      if (m > dominantMag) {
        dominantMag = m;
        dominantBin = i;
      }
    }
    const spectralCentroidBin = total > 0 ? weighted / total : 0;
    const spectralCentroid = binToHz(spectralCentroidBin, this.sampleRate, fftN);
    const dominantFrequency = binToHz(dominantBin, this.sampleRate, fftN);

    // rolloff: frequency below which `rolloffThreshold` of energy lies
    let cum = 0;
    let rolloffBin = 0;
    const target = total * this.rolloffThreshold;
    for (let i = 0; i < mag.length; i++) {
      cum += mag[i];
      if (cum >= target) {
        rolloffBin = i;
        break;
      }
    }
    const spectralRolloff = binToHz(rolloffBin, this.sampleRate, fftN);

    // spectral flatness (geometric mean / arithmetic mean) — tonality vs noise
    let logSum = 0;
    let arithSum = 0;
    let count = 0;
    for (let i = 1; i < mag.length; i++) {
      const m = mag[i] + 1e-12;
      logSum += Math.log(m);
      arithSum += m;
      count++;
    }
    const flatness =
      count > 0 && arithSum > 0
        ? Math.exp(logSum / count) / (arithSum / count)
        : 0;

    const pitch = this.estimatePitch(frame);

    return {
      rms,
      peak,
      zcr,
      pitch,
      dominantFrequency,
      spectralCentroid,
      spectralRolloff,
      flatness,
      magnitude: mag,
    };
  }

  /**
   * Autocorrelation pitch estimate (Hz). Returns 0 when no clear period is found.
   * @param {Float32Array|number[]} frame
   * @param {{minHz?: number, maxHz?: number}} [opts]
   */
  estimatePitch(frame, opts = {}) {
    const minHz = opts.minHz || 60;
    const maxHz = opts.maxHz || 1000;
    const n = frame.length;
    const minLag = Math.floor(this.sampleRate / maxHz);
    const maxLag = Math.min(n - 1, Math.floor(this.sampleRate / minHz));

    let bestLag = -1;
    let bestCorr = 0;
    let normAtZero = 0;
    for (let i = 0; i < n; i++) normAtZero += frame[i] * frame[i];
    if (normAtZero < 1e-6) return 0;

    for (let lag = minLag; lag <= maxLag; lag++) {
      let corr = 0;
      for (let i = 0; i < n - lag; i++) corr += frame[i] * frame[i + lag];
      corr /= normAtZero;
      if (corr > bestCorr) {
        bestCorr = corr;
        bestLag = lag;
      }
    }
    if (bestLag <= 0 || bestCorr < 0.3) return 0;
    return this.sampleRate / bestLag;
  }

  static emptyFeatures() {
    return {
      rms: 0,
      peak: 0,
      zcr: 0,
      pitch: 0,
      dominantFrequency: 0,
      spectralCentroid: 0,
      spectralRolloff: 0,
      flatness: 0,
      magnitude: new Float64Array(0),
    };
  }

  // ----------------------------------------------------------------------
  // Frequency manipulation helpers (static, pure)
  // ----------------------------------------------------------------------

  /**
   * Pitch-shift a frame by a semitone amount via linear resampling (granular-free,
   * length-preserving best-effort). Positive = up.
   */
  static pitchShiftSemitones(frame, semitones) {
    const ratio = Math.pow(2, semitones / 12);
    const n = frame.length;
    const out = new Float32Array(n);
    // Raise pitch (ratio > 1) by reading the source faster (src = i * ratio); lower pitch
    // by reading slower. Length is preserved; output past the resampled span is silence.
    for (let i = 0; i < n; i++) {
      const src = i * ratio;
      const i0 = Math.floor(src);
      const i1 = Math.min(n - 1, i0 + 1);
      const f = src - i0;
      out[i] = i0 < n ? frame[i0] * (1 - f) + frame[i1] * f : 0;
    }
    return out;
  }

  /**
   * Apply per-band gain to a magnitude spectrum.
   * @param {Float64Array} mag
   * @param {Array<{from:number,to:number,gain:number}>} bands Hz ranges + linear gain
   * @param {number} sampleRate
   * @param {number} fftSize
   */
  static applyBandGain(mag, bands, sampleRate, fftSize) {
    const out = Float64Array.from(mag);
    for (let i = 0; i < out.length; i++) {
      const hz = binToHz(i, sampleRate, fftSize);
      for (const b of bands) {
        if (hz >= b.from && hz <= b.to) out[i] *= b.gain;
      }
    }
    return out;
  }
}

export default VoiceAnalyzer;
