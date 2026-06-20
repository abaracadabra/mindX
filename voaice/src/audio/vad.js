/**
 * vad.js — lightweight energy/ZCR voice-activity detection + silence trimming.
 *
 * Dependency-free. A reference clip for cloning is much cleaner with leading/trailing silence
 * (and dead air) removed — the speaker model then conditions only on real speech. This is the
 * portable, well-specified core of what webrtcvad/librosa.effects.trim do: frame the signal,
 * mark frames whose RMS clears a noise-relative threshold as voiced, and trim to the voiced span.
 *
 *   import { trimSilence, voicedFrames } from 'voaice/wav'  // re-exported via index
 */

const EPS = 1e-9;

function frameRmsDb(samples, frameLen, hop) {
  const out = [];
  for (let start = 0; start + frameLen <= samples.length; start += hop) {
    let sum = 0;
    for (let i = start; i < start + frameLen; i++) sum += samples[i] * samples[i];
    const rms = Math.sqrt(sum / frameLen);
    out.push({ start, db: 20 * Math.log10(rms + EPS) });
  }
  return out;
}

/**
 * Mark voiced frames. A frame is voiced when its RMS is within `topDb` of the clip's loudest
 * frame (relative gating — robust to absolute level), above an absolute noise floor.
 * @returns {{ frames: Array<{start:number, db:number, voiced:boolean}>, frameLen:number, hop:number }}
 */
export function voicedFrames(samples, sampleRate, opts = {}) {
  const frameLen = opts.frameLen || Math.round(0.025 * sampleRate); // 25 ms
  const hop = opts.hop || Math.round(0.010 * sampleRate); // 10 ms
  const topDb = opts.topDb ?? 35; // frames within 35 dB of peak are speech
  const floorDb = opts.floorDb ?? -60; // absolute silence floor

  const raw = frameRmsDb(samples, frameLen, hop);
  if (!raw.length) return { frames: [], frameLen, hop };
  const maxDb = raw.reduce((m, f) => Math.max(m, f.db), -Infinity);
  const thresh = Math.max(floorDb, maxDb - topDb);
  return {
    frames: raw.map((f) => ({ ...f, voiced: f.db >= thresh })),
    frameLen,
    hop,
  };
}

/**
 * Trim leading/trailing silence, keeping a short margin of context around speech.
 * @param {Float32Array|number[]} samples
 * @param {number} sampleRate
 * @param {{ topDb?:number, marginMs?:number, frameLen?:number, hop?:number, floorDb?:number }} [opts]
 * @returns {{ samples: Float32Array, startSample:number, endSample:number, trimmed:boolean }}
 */
export function trimSilence(samples, sampleRate, opts = {}) {
  const { frames, frameLen } = voicedFrames(samples, sampleRate, opts);
  const margin = Math.round(((opts.marginMs ?? 50) / 1000) * sampleRate);
  const voiced = frames.filter((f) => f.voiced);
  if (!voiced.length) {
    return { samples: Float32Array.from(samples), startSample: 0, endSample: samples.length, trimmed: false };
  }
  const first = voiced[0].start;
  const last = voiced[voiced.length - 1].start + frameLen;
  const startSample = Math.max(0, first - margin);
  const endSample = Math.min(samples.length, last + margin);
  return {
    samples: Float32Array.from(samples.subarray(startSample, endSample)),
    startSample,
    endSample,
    trimmed: startSample > 0 || endSample < samples.length,
  };
}

/** Fraction of the clip that is voiced (0..1) — a quick "is there speech here?" signal. */
export function voicedRatio(samples, sampleRate, opts = {}) {
  const { frames } = voicedFrames(samples, sampleRate, opts);
  if (!frames.length) return 0;
  return frames.filter((f) => f.voiced).length / frames.length;
}
