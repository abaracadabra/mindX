/**
 * Forensic.js — forensic voice analysis: voiceprint identity, speaker
 * comparison, tamper/splice detection, and hash-linked chain-of-custody.
 *
 * Builds on Scientific.js (18-decimal fixed-point measures, sha256 print
 * hashes) so a forensic voiceprint is the SAME object a SoundWaveToken
 * registration consumes — measurement and evidence share one substrate.
 * Zero external dependencies; pure Node DSP.
 *
 *   import { Forensic } from 'voaice/forensic';
 *   const f = new Forensic({ sampleRate });
 *   const print = f.voiceprint(samples);          // aggregate identity print
 *   const cmp   = Forensic.compare(printA, printB); // similarity + verdict
 *   const rep   = f.integrity(samples);           // splice/clipping report
 *   const rec   = f.custody(samples, { prev });   // hash-linked evidence record
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { createHash } from 'node:crypto';
import { Scientific, toFixed18 } from './Scientific.js';
import { frames, encodeWav } from './audio/wav.js';
import { voicedFrames } from './audio/vad.js';

const FEATURE_KEYS = [
  'dominantFrequency',
  'amplitude',
  'spectralCentroid',
  'spectralRolloff',
  'zeroCrossingRate',
  'harmonicNoiseRatio',
];

// Per-feature scales for normalised distance (rough dynamic ranges; a
// difference of one full scale counts as maximally different on that axis).
const FEATURE_SCALE = {
  dominantFrequency: 220, // Hz — octave-ish band around speech F0
  amplitude: 0.25,
  spectralCentroid: 1500, // Hz
  spectralRolloff: 3000, // Hz
  zeroCrossingRate: 0.15,
  harmonicNoiseRatio: 12, // dB-ish ratio units from Scientific
};

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const stdev = (xs) => {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  return Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1));
};

export class Forensic {
  constructor(opts = {}) {
    this.sampleRate = opts.sampleRate || 24000;
    this.frameSize = opts.frameSize || 2048;
    this.hop = opts.hop || this.frameSize / 2;
    // A voiceprint is an AGGREGATE — a few hundred well-spread frames describe a
    // speaker as well as every frame of a 10-minute clip, at a fraction of the
    // cost. Frames are subsampled EVENLY (never truncated to the head), so the
    // print stays representative of the whole clip. Set 0 to analyse every frame.
    this.maxFrames = opts.maxFrames ?? 400;
    this.scientific = new Scientific({ sampleRate: this.sampleRate, frameSize: this.frameSize });
  }

  /** Evenly subsample a frame list down to `maxFrames` (identity if under). */
  _subsample(list) {
    if (!this.maxFrames || list.length <= this.maxFrames) return list;
    const step = list.length / this.maxFrames;
    const out = [];
    for (let i = 0; i < this.maxFrames; i++) out.push(list[Math.floor(i * step)]);
    return out;
  }

  /**
   * Aggregate voiceprint over the VOICED frames of a clip — per-feature mean,
   * spread, an 18-dp register vector, and a reproducible sha256 print id.
   * @param {Float32Array} samples mono [-1,1]
   * @returns {{features, spread, measures, measuresStr, framesUsed, framesTotal, precision, hash}}
   */
  voiceprint(samples) {
    // voicedFrames returns frame METADATA ({start, voiced}); extract the actual
    // sample windows for the voiced ones, falling back to all frames on thin input.
    const { frames: vmeta } = voicedFrames(samples, this.sampleRate);
    const voicedStarts = this._subsample((vmeta || []).filter((f) => f.voiced).map((f) => f.start));
    let source;
    if (voicedStarts.length >= 4) {
      source = voicedStarts.map((start) => {
        const w = new Float32Array(this.frameSize);
        const end = Math.min(samples.length, start + this.frameSize);
        for (let i = start; i < end; i++) w[i - start] = samples[i];
        return w;
      });
    } else {
      source = this._subsample(frames(samples, this.frameSize, this.hop));
    }
    const series = Object.fromEntries(FEATURE_KEYS.map((k) => [k, []]));
    const precisions = [];
    for (const frame of source) {
      const m = this.scientific.measure(frame);
      for (const k of FEATURE_KEYS) series[k].push(m.features[k] || 0);
      precisions.push(Number(m.precisionScore) / 1e18);
    }
    const features = {};
    const spread = {};
    for (const k of FEATURE_KEYS) {
      features[k] = mean(series[k]);
      spread[k] = stdev(series[k]);
    }
    const measures = FEATURE_KEYS.map((k) => toFixed18(features[k]));
    const payload = {
      v: 1,
      kind: 'forensic-voiceprint',
      sampleRate: this.sampleRate,
      framesUsed: source.length,
      measures: measures.map((x) => x.toString()),
    };
    return {
      sampleRate: this.sampleRate,
      features,
      spread,
      measures,
      measuresStr: measures.map((x) => x.toString()),
      framesUsed: source.length,
      framesTotal: Math.ceil(samples.length / this.hop),
      precision: mean(precisions),
      hash: '0x' + createHash('sha256').update(JSON.stringify(payload)).digest('hex'),
    };
  }

  /**
   * Compare two voiceprints → similarity in [0,1] + a verdict band.
   * Distance is the mean per-feature normalised absolute difference, with the
   * spread of each print widening tolerance on unstable axes.
   */
  static compare(a, b) {
    const contributions = {};
    let total = 0;
    for (const k of FEATURE_KEYS) {
      const scale = FEATURE_SCALE[k] + ((a.spread?.[k] || 0) + (b.spread?.[k] || 0)) / 2;
      const d = Math.min(1, Math.abs((a.features[k] || 0) - (b.features[k] || 0)) / scale);
      contributions[k] = 1 - d;
      total += d;
    }
    const similarity = 1 - total / FEATURE_KEYS.length;
    const verdict =
      similarity >= 0.9 ? 'match'
      : similarity >= 0.75 ? 'probable'
      : similarity >= 0.55 ? 'inconclusive'
      : 'different';
    return { similarity, verdict, contributions };
  }

  /**
   * Tamper/splice screening — flags frame-boundary discontinuities (splices),
   * hard clipping, DC offset, and dead-air gaps. Heuristic screening, not
   * proof: events are leads for a human examiner, scored by z-score.
   * @returns {{events, clippingRatio, dcOffset, silenceRatio, verdict}}
   */
  integrity(samples) {
    const fs = 1024;
    const hop = 512;
    const rmsSeries = [];
    for (let s = 0; s + fs <= samples.length; s += hop) {
      let acc = 0;
      for (let i = s; i < s + fs; i++) acc += samples[i] * samples[i];
      rmsSeries.push(Math.sqrt(acc / fs));
    }
    // First-difference z-scores → splice candidates. A splice must be BOTH a
    // statistical outlier AND a materially large jump: in a near-stationary
    // signal the diff stdev collapses toward zero, so a z-score alone would
    // flag ordinary numerical wobble as tampering. The absolute floor (a jump
    // worth ≥25% of the clip's mean level) is what keeps a clean recording clean.
    const diffs = rmsSeries.slice(1).map((v, i) => Math.abs(v - rmsSeries[i]));
    const dm = mean(diffs);
    const ds = stdev(diffs);
    const levelMean = mean(rmsSeries);
    const absFloor = Math.max(1e-4, 0.25 * levelMean);
    const events = [];
    diffs.forEach((d, i) => {
      if (d < absFloor) return; // too small to be a splice, whatever its z-score
      const z = ds > 1e-9 ? (d - dm) / ds : Infinity;
      if (z >= 4) {
        events.push({
          type: 'discontinuity',
          atSec: ((i + 1) * hop) / this.sampleRate,
          zScore: Number.isFinite(z) ? Number(z.toFixed(2)) : null,
          jump: Number(d.toFixed(5)),
        });
      }
    });
    let clipped = 0;
    let dc = 0;
    for (let i = 0; i < samples.length; i++) {
      if (Math.abs(samples[i]) >= 0.999) clipped++;
      dc += samples[i];
    }
    const clippingRatio = clipped / (samples.length || 1);
    const dcOffset = dc / (samples.length || 1);
    const silenceRatio = rmsSeries.filter((r) => r < 1e-4).length / (rmsSeries.length || 1);
    const suspicious = events.length > 0 || clippingRatio > 0.001 || Math.abs(dcOffset) > 0.02;
    return {
      events,
      clippingRatio,
      dcOffset,
      silenceRatio,
      verdict: suspicious ? 'review' : 'clean',
    };
  }

  /**
   * Chain-of-custody record: sha256 over the canonical 16-bit PCM rendering,
   * hash-linked to a previous record (ephermaleth-style evidence chain).
   * @param {Float32Array} samples
   * @param {{prev?: string, note?: string, at?: string}} [meta]
   */
  custody(samples, meta = {}) {
    const canonical = encodeWav(samples, this.sampleRate); // 16-bit canonical form
    const contentHash = '0x' + createHash('sha256').update(canonical).digest('hex');
    const record = {
      v: 1,
      kind: 'voice-custody',
      contentHash,
      sampleRate: this.sampleRate,
      durationSec: samples.length / this.sampleRate,
      at: meta.at || new Date().toISOString(),
      note: meta.note || null,
      prev: meta.prev || null,
    };
    record.recordHash = '0x' + createHash('sha256').update(JSON.stringify(record)).digest('hex');
    return record;
  }
}

export default Forensic;
