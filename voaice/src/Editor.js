/**
 * Editor.js — non-destructive audio editing for voice clips.
 *
 * A clip is `{ samples: Float32Array, sampleRate: number }` (mono, [-1,1]) —
 * the same shape the codec, analyzers, and engines already speak. Every
 * operation returns a NEW clip; `AudioEditor` adds a chainable session with
 * undo/redo history on top of the pure functions.
 *
 *   import { AudioEditor, gain, fadeIn, normalize } from 'voaice/editor';
 *   const ed = new AudioEditor(clip)
 *     .trim(0.2, 3.6).fadeIn(0.05).fadeOut(0.1).normalize({ mode: 'lufs' });
 *   const out = ed.toClip();  // ed.undo() steps back
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { normalizeToLufs, peak } from './audio/loudness.js';
import { trimSilence } from './audio/vad.js';

const toIndex = (clip, sec) =>
  Math.max(0, Math.min(clip.samples.length, Math.round(sec * clip.sampleRate)));

const mkClip = (samples, sampleRate) => ({ samples, sampleRate });

/** Keep [startSec, endSec) — trim everything else. */
export function slice(clip, startSec, endSec = clip.samples.length / clip.sampleRate) {
  const a = toIndex(clip, startSec);
  const b = toIndex(clip, endSec);
  return mkClip(clip.samples.slice(a, Math.max(a, b)), clip.sampleRate);
}

/** Remove [startSec, endSec) and join the remainder. */
export function cut(clip, startSec, endSec) {
  const a = toIndex(clip, startSec);
  const b = toIndex(clip, endSec);
  const out = new Float32Array(clip.samples.length - Math.max(0, b - a));
  out.set(clip.samples.subarray(0, a), 0);
  out.set(clip.samples.subarray(b), a);
  return mkClip(out, clip.sampleRate);
}

/** Insert another clip at `atSec` (other is resampled to match if needed). */
export function insert(clip, other, atSec) {
  const o = other.sampleRate === clip.sampleRate ? other : resample(other, clip.sampleRate);
  const at = toIndex(clip, atSec);
  const out = new Float32Array(clip.samples.length + o.samples.length);
  out.set(clip.samples.subarray(0, at), 0);
  out.set(o.samples, at);
  out.set(clip.samples.subarray(at), at + o.samples.length);
  return mkClip(out, clip.sampleRate);
}

/** Concatenate clips (all resampled to the first clip's rate). */
export function concat(clips) {
  if (!clips.length) return mkClip(new Float32Array(0), 24000);
  const rate = clips[0].sampleRate;
  const parts = clips.map((c) => (c.sampleRate === rate ? c : resample(c, rate)));
  const out = new Float32Array(parts.reduce((n, c) => n + c.samples.length, 0));
  let off = 0;
  for (const c of parts) {
    out.set(c.samples, off);
    off += c.samples.length;
  }
  return mkClip(out, rate);
}

/** Apply gain in dB. */
export function gain(clip, db) {
  const g = 10 ** (db / 20);
  const out = new Float32Array(clip.samples.length);
  for (let i = 0; i < out.length; i++) {
    const v = clip.samples[i] * g;
    out[i] = v > 1 ? 1 : v < -1 ? -1 : v;
  }
  return mkClip(out, clip.sampleRate);
}

const CURVES = {
  linear: (t) => t,
  exp: (t) => t * t,
  log: (t) => Math.sqrt(t),
};

/** Fade in over `seconds` with a `linear` | `exp` | `log` curve. */
export function fadeIn(clip, seconds, curve = 'linear') {
  const n = toIndex(clip, seconds);
  const f = CURVES[curve] || CURVES.linear;
  const out = Float32Array.from(clip.samples);
  for (let i = 0; i < n && i < out.length; i++) out[i] *= f(i / n);
  return mkClip(out, clip.sampleRate);
}

/** Fade out over the final `seconds`. */
export function fadeOut(clip, seconds, curve = 'linear') {
  const n = toIndex(clip, seconds);
  const f = CURVES[curve] || CURVES.linear;
  const out = Float32Array.from(clip.samples);
  const start = Math.max(0, out.length - n);
  for (let i = start; i < out.length; i++) out[i] *= f((out.length - 1 - i) / n);
  return mkClip(out, clip.sampleRate);
}

/**
 * Normalize — `{ mode: 'peak', peakDb: -1 }` scales to a target peak;
 * `{ mode: 'lufs', targetLufs: -16, maxPeak: 0.97 }` levels to broadcast
 * loudness via the in-house BS.1770 implementation.
 */
export function normalize(clip, opts = {}) {
  if (opts.mode === 'lufs') {
    const leveled = normalizeToLufs(
      clip.samples,
      clip.sampleRate,
      opts.targetLufs ?? -16,
      opts.maxPeak ?? 0.97
    );
    return mkClip(Float32Array.from(leveled), clip.sampleRate);
  }
  const target = 10 ** ((opts.peakDb ?? -1) / 20);
  const p = peak(clip.samples) || 1e-9;
  return gain(clip, 20 * Math.log10(target / p));
}

/** Reverse the clip. */
export function reverse(clip) {
  return mkClip(Float32Array.from(clip.samples).reverse(), clip.sampleRate);
}

/** Linear-interpolation resample to a new rate. */
export function resample(clip, targetRate) {
  if (targetRate === clip.sampleRate) return mkClip(Float32Array.from(clip.samples), targetRate);
  const ratio = clip.sampleRate / targetRate;
  const n = Math.max(1, Math.round(clip.samples.length / ratio));
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const pos = i * ratio;
    const i0 = Math.floor(pos);
    const i1 = Math.min(clip.samples.length - 1, i0 + 1);
    out[i] = clip.samples[i0] + (clip.samples[i1] - clip.samples[i0]) * (pos - i0);
  }
  return mkClip(out, targetRate);
}

/** Strip leading/trailing silence via the in-house VAD. */
export function removeSilence(clip, opts = {}) {
  const trimmed = trimSilence(clip.samples, clip.sampleRate, opts);
  const samples = trimmed?.samples || trimmed; // tolerate either return shape
  return mkClip(Float32Array.from(samples), clip.sampleRate);
}

/** Chainable, undoable editing session over the pure operations. */
export class AudioEditor {
  constructor(clip) {
    this._history = [mkClip(Float32Array.from(clip.samples), clip.sampleRate)];
    this._cursor = 0;
  }

  get clip() {
    return this._history[this._cursor];
  }

  _push(next) {
    this._history = this._history.slice(0, this._cursor + 1);
    this._history.push(next);
    this._cursor++;
    return this;
  }

  trim(a, b) { return this._push(slice(this.clip, a, b)); }
  cut(a, b) { return this._push(cut(this.clip, a, b)); }
  insert(other, at) { return this._push(insert(this.clip, other, at)); }
  append(other) { return this._push(concat([this.clip, other])); }
  gain(db) { return this._push(gain(this.clip, db)); }
  fadeIn(s, curve) { return this._push(fadeIn(this.clip, s, curve)); }
  fadeOut(s, curve) { return this._push(fadeOut(this.clip, s, curve)); }
  normalize(opts) { return this._push(normalize(this.clip, opts)); }
  reverse() { return this._push(reverse(this.clip)); }
  resample(rate) { return this._push(resample(this.clip, rate)); }
  removeSilence(opts) { return this._push(removeSilence(this.clip, opts)); }

  undo() { if (this._cursor > 0) this._cursor--; return this; }
  redo() { if (this._cursor < this._history.length - 1) this._cursor++; return this; }
  get canUndo() { return this._cursor > 0; }
  get canRedo() { return this._cursor < this._history.length - 1; }

  toClip() {
    const c = this.clip;
    return mkClip(Float32Array.from(c.samples), c.sampleRate);
  }
}

export default AudioEditor;
