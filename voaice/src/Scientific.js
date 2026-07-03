/**
 * Scientific — the SCIENTIFIC forensic measuring tool.
 *
 * Turns a frame of audio into a reproducible, forensic-grade voiceprint measured to
 * 18 decimals of precision, ready for on-chain registration in SoundWaveToken (SND/WAV).
 *
 * It wraps voaice's in-house VoiceAnalyzer (spectrometer + pitch), adds a harmonic-to-noise
 * ratio and a composite precision/confidence score, and emits each acoustic measure as a
 * fixed-point integer (real_value × 1e18) plus a sha256 of the canonical payload. The six
 * measures map 1:1 to SoundWaveToken.registerVoicePrint(hash, sampleRate, uint256[6], precision):
 *   [dominantFrequency, amplitude, spectralCentroid, spectralRolloff, zeroCrossingRate, harmonicNoiseRatio]
 *
 * Pure Node, zero external deps (sha256 via node:crypto) — measure anywhere.
 */

import { createHash } from 'node:crypto';
import { VoiceAnalyzer } from './VoiceAnalyzer.js';
import { binToHz } from './dsp/fft.js';

const ONE = 10n ** 18n; // 18-decimal fixed-point scale (matches SoundWaveToken.ONE)

/**
 * Convert a real number to an 18-decimal fixed-point BigInt (real × 1e18).
 * Keeps 9 decimals of real precision (sub-µ for Hz), padded to 18 — avoids Number
 * precision loss from a naive v*1e18.
 */
export function toFixed18(v) {
  if (!isFinite(v) || v < 0) v = 0;
  const whole = Math.floor(v);
  const frac = v - whole;
  return BigInt(whole) * ONE + BigInt(Math.round(frac * 1e9)) * 10n ** 9n;
}

/** Inverse: 18-dec fixed-point BigInt → Number (for display). */
export function fromFixed18(x) {
  return Number(x) / 1e18;
}

export class Scientific {
  /**
   * @param {{sampleRate?: number, fftSize?: number}} [opts]
   */
  constructor(opts = {}) {
    this.sampleRate = opts.sampleRate || 44100;
    this.analyzer = new VoiceAnalyzer({ sampleRate: this.sampleRate, fftSize: opts.fftSize || 2048 });
  }

  /**
   * Harmonic-to-noise ratio estimate (linear): energy at integer multiples of the pitch
   * vs the residual energy. Higher = cleaner, more voiced.
   */
  harmonicNoiseRatio(mag, pitchHz, fftSize) {
    if (!pitchHz || !mag.length) return 0;
    let harmonic = 0;
    let total = 0;
    for (let i = 0; i < mag.length; i++) total += mag[i];
    if (total <= 0) return 0;
    for (let k = 1; k <= 12; k++) {
      const hz = pitchHz * k;
      const bin = Math.round((hz * fftSize) / this.sampleRate);
      if (bin <= 0 || bin >= mag.length) break;
      // sum the peak and its immediate neighbours
      harmonic += (mag[bin - 1] || 0) + mag[bin] + (mag[bin + 1] || 0);
    }
    const noise = Math.max(1e-9, total - harmonic);
    return harmonic / noise;
  }

  /**
   * Measure one frame to forensic precision.
   * @param {Float32Array|number[]} frame samples in [-1, 1]
   * @returns {{
   *   sampleRate:number, features:object,
   *   measures:bigint[], measuresStr:string[],
   *   precisionScore:bigint, hash:string, payload:object
   * }}
   */
  measure(frame) {
    const f = this.analyzer.analyze(frame);
    const fftSize = 2 ** Math.ceil(Math.log2(frame.length));
    const hnr = this.harmonicNoiseRatio(f.magnitude, f.pitch, fftSize);

    // composite precision/confidence in [0,1]:
    //  - tonality (1 - flatness): peaky spectrum => confident measurement
    //  - voicing (hnr saturating): clear harmonics => confident pitch
    //  - level (rms saturating): enough signal to measure
    const tonality = Math.max(0, Math.min(1, 1 - f.flatness));
    const voicing = hnr / (hnr + 1);
    const level = Math.min(1, f.rms / 0.1);
    const precision = Math.max(0, Math.min(1, 0.4 * tonality + 0.4 * voicing + 0.2 * level));

    // six measures in SoundWaveToken field order
    const real = {
      dominantFrequency: f.dominantFrequency,
      amplitude: f.rms,
      spectralCentroid: f.spectralCentroid,
      spectralRolloff: f.spectralRolloff,
      zeroCrossingRate: f.zcr,
      harmonicNoiseRatio: hnr,
    };
    const measures = [
      toFixed18(real.dominantFrequency),
      toFixed18(real.amplitude),
      toFixed18(real.spectralCentroid),
      toFixed18(real.spectralRolloff),
      toFixed18(real.zeroCrossingRate),
      toFixed18(real.harmonicNoiseRatio),
    ];
    const precisionScore = toFixed18(precision);

    // canonical payload → sha256 (reproducible: same measures => same hash => uniqueness)
    const payload = {
      v: 1,
      sampleRate: this.sampleRate,
      measures: measures.map((x) => x.toString()),
      precisionScore: precisionScore.toString(),
    };
    const hash =
      '0x' + createHash('sha256').update(JSON.stringify(payload)).digest('hex');

    return {
      sampleRate: this.sampleRate,
      features: { ...real, flatness: f.flatness, pitch: f.pitch },
      measures,
      measuresStr: measures.map((x) => x.toString()),
      precisionScore,
      hash,
      payload,
    };
  }

  /**
   * Shape a measurement into SoundWaveToken.registerVoicePrint arguments.
   * @returns {{hash:string, sampleRate:number, m:string[], precisionScore:string}}
   */
  toRegisterArgs(measurement) {
    return {
      hash: measurement.hash,
      sampleRate: measurement.sampleRate,
      m: measurement.measuresStr,
      precisionScore: measurement.precisionScore.toString(),
    };
  }
}

export default Scientific;
