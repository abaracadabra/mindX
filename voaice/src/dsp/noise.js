/**
 * noise.js — signal versus noise.
 *
 * Everything upstream of a good clone depends on knowing how much of an input
 * is voice and how much is room. This module measures that split and, when
 * asked, removes the room: noise profiling from the silent frames, SNR in dB,
 * spectral subtraction, a noise gate, and a spectral noise floor.
 *
 * Zero dependencies — in-house FFT + VAD. Non-destructive: every function
 * returns new samples and a report of what it found.
 *
 *   import { snr, noiseProfile, denoise, gate } from 'voaice/noise';
 *   const report = snr(samples, sampleRate);       // { snrDb, speechDb, noiseDb, verdict }
 *   const clean  = denoise(samples, sampleRate);   // spectral subtraction
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { fft, hann, nextPow2 } from './fft.js';
import { voicedFrames } from '../audio/vad.js';

const EPS = 1e-12;
const db = (x) => 20 * Math.log10(Math.max(EPS, x));
const rms = (a, from = 0, to = a.length) => {
  let s = 0;
  for (let i = from; i < to; i++) s += a[i] * a[i];
  return Math.sqrt(s / Math.max(1, to - from));
};

/**
 * Split a clip into speech and noise by VAD, and report the ratio.
 * @returns {{snrDb:number, speechDb:number, noiseDb:number, speechRatio:number,
 *            noiseFloor:number, verdict:'clean'|'usable'|'noisy'|'unusable'}}
 */
export function snr(samples, sampleRate, opts = {}) {
  const { frames, frameLen, hop } = voicedFrames(samples, sampleRate, opts);
  if (!frames.length) {
    return { snrDb: 0, speechDb: -Infinity, noiseDb: -Infinity, speechRatio: 0, noiseFloor: 0, verdict: 'unusable' };
  }
  let sp = 0;
  let spN = 0;
  let no = 0;
  let noN = 0;
  for (const f of frames) {
    const r = rms(samples, f.start, Math.min(samples.length, f.start + frameLen));
    if (f.voiced) { sp += r * r; spN++; } else { no += r * r; noN++; }
  }
  const speech = spN ? Math.sqrt(sp / spN) : 0;
  // No silent frame at all → the noise floor is unmeasurable from this clip;
  // fall back to the quietest frame rather than pretending the floor is zero.
  let noise;
  if (noN) {
    noise = Math.sqrt(no / noN);
  } else {
    let quietest = Infinity;
    for (const f of frames) {
      quietest = Math.min(quietest, rms(samples, f.start, Math.min(samples.length, f.start + frameLen)));
    }
    noise = Number.isFinite(quietest) ? quietest : EPS;
  }
  const snrDb = db(speech) - db(noise);
  const speechRatio = spN / frames.length;
  const verdict =
    snrDb >= 30 ? 'clean'
    : snrDb >= 20 ? 'usable'
    : snrDb >= 10 ? 'noisy'
    : 'unusable';
  return {
    snrDb,
    speechDb: db(speech),
    noiseDb: db(noise),
    speechRatio,
    noiseFloor: noise,
    verdict,
    frames: { total: frames.length, voiced: spN, silent: noN },
    hop,
  };
}

/**
 * Learn the noise magnitude spectrum from the clip's SILENT frames (or from a
 * supplied noise-only clip). This is the profile spectral subtraction removes.
 * @returns {{spectrum:Float64Array, fftSize:number, frames:number}|null}
 */
export function noiseProfile(samples, sampleRate, opts = {}) {
  const fftSize = opts.fftSize || 1024;
  // A TIGHTER gate than the speech VAD on purpose. The speech VAD keeps frames
  // within 35 dB of the peak (so quiet consonants survive); a noise profile must
  // learn from the CLEARLY-quiet frames only, or it will train on speech and
  // subtract the voice away. 15 dB is the band where the room lives.
  const { frames, frameLen } = voicedFrames(samples, sampleRate, {
    ...opts,
    topDb: opts.topDb ?? 15,
  });
  const silent = frames.filter((f) => !f.voiced);
  const source = opts.noiseOnly
    ? [{ start: 0 }] // caller handed us pure noise
    : silent;
  if (!source.length) return null; // nothing silent to learn from — say so

  const spec = new Float64Array(fftSize / 2);
  let n = 0;
  const take = opts.noiseOnly ? Math.floor(samples.length / fftSize) : source.length;
  for (let k = 0; k < take; k++) {
    const start = opts.noiseOnly ? k * fftSize : source[k].start;
    const win = new Float32Array(fftSize);
    const end = Math.min(samples.length, start + Math.min(fftSize, frameLen || fftSize));
    for (let i = start; i < end; i++) win[i - start] = samples[i];
    const re = Float64Array.from(hann(win));
    const im = new Float64Array(fftSize);
    fft(re, im);
    for (let i = 0; i < spec.length; i++) spec[i] += Math.hypot(re[i], im[i]);
    n++;
  }
  if (!n) return null;
  for (let i = 0; i < spec.length; i++) spec[i] /= n;
  return { spectrum: spec, fftSize, frames: n };
}

/**
 * Spectral-subtraction denoise. Subtracts the learned noise spectrum from every
 * frame's magnitude, keeping the phase, with an over-subtraction factor and a
 * spectral floor that trade residual noise against musical artifacts.
 *
 * @param {{profile?:object, over?:number, floor?:number, fftSize?:number}} [opts]
 *   over  — over-subtraction factor (1 = exact, 1.5–2.5 = aggressive)
 *   floor — spectral floor as a fraction of the noise estimate (0.02–0.1);
 *           never subtract to zero, or you get "musical noise" (chirping)
 * @returns {{samples:Float32Array, profileUsed:boolean, snrBefore:object, snrAfter:object}}
 */
export function denoise(samples, sampleRate, opts = {}) {
  const before = snr(samples, sampleRate);
  const profile = opts.profile || noiseProfile(samples, sampleRate, opts);
  if (!profile) {
    // No silence anywhere → we cannot learn a noise floor. Return the input
    // unchanged and say why, rather than inventing a profile.
    return { samples: Float32Array.from(samples), profileUsed: false, snrBefore: before, snrAfter: before,
      note: 'no silent frames to learn a noise profile from — supply one via opts.profile' };
  }
  const N = profile.fftSize;
  const hop = N / 4; // 75% overlap — smooth reconstruction
  const over = opts.over ?? 1.6;
  const floor = opts.floor ?? 0.05;

  const out = new Float64Array(samples.length + N);
  const wsum = new Float64Array(samples.length + N);
  const window = new Float32Array(N);
  for (let i = 0; i < N; i++) window[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1));

  for (let start = 0; start < samples.length; start += hop) {
    const re = new Float64Array(N);
    const im = new Float64Array(N);
    const end = Math.min(samples.length, start + N);
    for (let i = start; i < end; i++) re[i - start] = samples[i] * window[i - start];
    fft(re, im);

    for (let k = 0; k < N; k++) {
      const bin = k <= N / 2 ? k : N - k; // mirror for the negative half
      const mag = Math.hypot(re[k], im[k]);
      if (mag < EPS) continue;
      const noiseMag = profile.spectrum[Math.min(profile.spectrum.length - 1, bin)] || 0;
      const cleaned = Math.max(mag - over * noiseMag, floor * noiseMag);
      const g = cleaned / mag;
      re[k] *= g;
      im[k] *= g;
    }
    // inverse FFT via conjugation trick
    for (let k = 0; k < N; k++) im[k] = -im[k];
    fft(re, im);
    for (let i = 0; i < N; i++) {
      const v = re[i] / N;
      out[start + i] += v * window[i];
      wsum[start + i] += window[i] * window[i];
    }
  }

  const clean = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    clean[i] = wsum[i] > 1e-8 ? out[i] / wsum[i] : 0;
  }
  return {
    samples: clean,
    profileUsed: true,
    snrBefore: before,
    snrAfter: snr(clean, sampleRate),
  };
}

/**
 * Noise gate — silence anything below a threshold, with attack/release so the
 * gate never clicks. The blunt instrument; `denoise` is the surgical one.
 */
export function gate(samples, sampleRate, opts = {}) {
  const thresholdDb = opts.thresholdDb ?? -45;
  const attackMs = opts.attackMs ?? 5;
  const releaseMs = opts.releaseMs ?? 60;
  const thr = 10 ** (thresholdDb / 20);
  const atk = Math.exp(-1 / ((attackMs / 1000) * sampleRate));
  const rel = Math.exp(-1 / ((releaseMs / 1000) * sampleRate));

  const out = new Float32Array(samples.length);
  let env = 0;
  let g = 0;
  for (let i = 0; i < samples.length; i++) {
    const x = Math.abs(samples[i]);
    env = x > env ? atk * env + (1 - atk) * x : rel * env + (1 - rel) * x;
    const target = env >= thr ? 1 : 0;
    g = target > g ? atk * g + (1 - atk) * target : rel * g + (1 - rel) * target;
    out[i] = samples[i] * g;
  }
  return out;
}

/** Spectral flatness (0 = tonal, 1 = white noise) — a quick "is this noise?" number. */
export function spectralFlatness(samples) {
  const N = nextPow2(Math.min(samples.length, 2048));
  const re = new Float64Array(N);
  const im = new Float64Array(N);
  for (let i = 0; i < Math.min(N, samples.length); i++) re[i] = samples[i];
  fft(re, im);
  let logSum = 0;
  let sum = 0;
  const half = N / 2;
  for (let i = 1; i < half; i++) {
    const m = Math.hypot(re[i], im[i]) + EPS;
    logSum += Math.log(m);
    sum += m;
  }
  const geo = Math.exp(logSum / (half - 1));
  const arith = sum / (half - 1);
  return arith > EPS ? geo / arith : 0;
}

export default { snr, noiseProfile, denoise, gate, spectralFlatness };
