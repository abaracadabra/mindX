/**
 * VoiceShaper.js — editing the VOICE, not the clip.
 *
 * `Editor` performs surgery on a timeline: trim, cut, join, fade, level.
 * `VoiceShaper` changes the character of the voice itself — its pitch, its
 * pace, its vocal tract, its tone, its dynamics:
 *
 *   pitchShift      semitones, without changing duration
 *   timeStretch     faster/slower, without changing pitch
 *   formantShift    move the vocal tract (bigger/smaller "head") — this is what
 *                   makes a pitch-shifted voice sound like a PERSON rather than
 *                   a chipmunk, because pitch and timbre move independently
 *   eq              biquad filters: low/high-pass, peaking, shelves
 *   compress        even out the dynamics (broadcast presence)
 *   deEss           tame sibilance
 *   breath          add/remove breathiness (noise mixed at the glottal band)
 *
 * All in-house, zero dependencies: WSOLA-style overlap-add for time/pitch,
 * RBJ biquads for EQ, an envelope-follower compressor. Every method is pure —
 * new samples out — and `VoiceShaper` chains them with an undo history, the
 * same contract as `AudioEditor`.
 *
 *   import { VoiceShaper } from 'voaice/shaper';
 *   const out = new VoiceShaper(clip)
 *     .pitchShift(-2).formantShift(0.95).eq({ type: 'peaking', freq: 3000, gainDb: 3, q: 1 })
 *     .compress({ thresholdDb: -18, ratio: 3 }).deEss().toClip();
 *
 * © Professor Codephreak - rage.pythai.net
 */

const clamp = (v) => (v > 1 ? 1 : v < -1 ? -1 : v);
const mkClip = (samples, sampleRate) => ({ samples, sampleRate });

// ── time / pitch (WSOLA overlap-add) ──────────────────────────────────────
/**
 * Time-stretch by `factor` (2 = twice as long, 0.5 = half) at constant pitch.
 * Synthesis hop is fixed; the analysis hop moves, and each grain is aligned to
 * the previous output by cross-correlation so the waveform stays phase-coherent
 * (that alignment is what separates WSOLA from a clicky naive overlap-add).
 */
export function timeStretch(clip, factor, opts = {}) {
  if (Math.abs(factor - 1) < 1e-6) return mkClip(Float32Array.from(clip.samples), clip.sampleRate);
  const { samples, sampleRate } = clip;
  const N = opts.frameSize || Math.round(0.06 * sampleRate); // 60 ms grains
  const Hs = Math.round(N / 2); // synthesis hop (50% overlap)
  const Ha = Math.round(Hs / factor); // analysis hop
  const seek = opts.seek ?? Math.round(N / 4); // ± search window for alignment

  const win = new Float32Array(N);
  for (let i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1));

  const outLen = Math.max(N, Math.round(samples.length * factor) + N);
  const out = new Float64Array(outLen);
  const wsum = new Float64Array(outLen);

  let outPos = 0;
  let anaPos = 0;
  while (anaPos + N < samples.length && outPos + N < outLen) {
    // align this grain to what we have already written (cross-correlation)
    let best = 0;
    let bestScore = -Infinity;
    if (outPos > 0) {
      const lo = Math.max(0, anaPos - seek);
      const hi = Math.min(samples.length - N, anaPos + seek);
      for (let cand = lo; cand <= hi; cand += 4) {
        let score = 0;
        for (let i = 0; i < Hs; i += 4) {
          const prev = wsum[outPos + i] > 1e-9 ? out[outPos + i] / wsum[outPos + i] : 0;
          score += prev * samples[cand + i];
        }
        if (score > bestScore) { bestScore = score; best = cand - anaPos; }
      }
    }
    const start = Math.max(0, Math.min(samples.length - N, anaPos + best));
    for (let i = 0; i < N; i++) {
      out[outPos + i] += samples[start + i] * win[i];
      wsum[outPos + i] += win[i];
    }
    outPos += Hs;
    anaPos += Ha;
  }

  const res = new Float32Array(Math.max(1, Math.round(samples.length * factor)));
  for (let i = 0; i < res.length && i < outLen; i++) {
    res[i] = wsum[i] > 1e-9 ? clamp(out[i] / wsum[i]) : 0;
  }
  return mkClip(res, sampleRate);
}

/** Resample without touching duration semantics (helper for pitch shift). */
function resampleRaw(samples, ratio) {
  const n = Math.max(1, Math.round(samples.length / ratio));
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const pos = i * ratio;
    const i0 = Math.floor(pos);
    const i1 = Math.min(samples.length - 1, i0 + 1);
    out[i] = samples[i0] + (samples[i1] - samples[i0]) * (pos - i0);
  }
  return out;
}

/** Shift pitch by `semitones` at constant duration (stretch, then resample back). */
export function pitchShift(clip, semitones, opts = {}) {
  if (!semitones) return mkClip(Float32Array.from(clip.samples), clip.sampleRate);
  const ratio = 2 ** (semitones / 12);
  const stretched = timeStretch(clip, ratio, opts); // longer/shorter, same pitch
  const back = resampleRaw(stretched.samples, ratio); // back to length, pitch moved
  return mkClip(back, clip.sampleRate);
}

/**
 * Shift the FORMANTS (vocal-tract size) without moving pitch. `factor` > 1
 * enlarges the tract (deeper, "bigger head"), < 1 shrinks it. Implemented as a
 * spectral-envelope resample: resample the waveform (which moves both pitch and
 * formants), then pitch-correct back — the residue is a pure formant move.
 */
export function formantShift(clip, factor, opts = {}) {
  if (!factor || Math.abs(factor - 1) < 1e-6) return mkClip(Float32Array.from(clip.samples), clip.sampleRate);
  const resampled = resampleRaw(clip.samples, 1 / factor); // moves pitch AND formants
  const semis = -12 * Math.log2(factor); // undo the pitch component only
  const corrected = pitchShift(mkClip(resampled, clip.sampleRate), semis, opts);
  // restore original length
  const out = new Float32Array(clip.samples.length);
  const src = corrected.samples;
  for (let i = 0; i < out.length; i++) out[i] = i < src.length ? src[i] : 0;
  return mkClip(out, clip.sampleRate);
}

// ── EQ (RBJ biquads) ──────────────────────────────────────────────────────
/**
 * @param {{type:'lowpass'|'highpass'|'peaking'|'lowshelf'|'highshelf',
 *          freq:number, q?:number, gainDb?:number}} p
 */
export function eq(clip, p) {
  const { samples, sampleRate } = clip;
  const A = 10 ** ((p.gainDb ?? 0) / 40);
  const w0 = (2 * Math.PI * p.freq) / sampleRate;
  const cw = Math.cos(w0);
  const sw = Math.sin(w0);
  const q = p.q ?? 0.707;
  const alpha = sw / (2 * q);
  let b0, b1, b2, a0, a1, a2;

  switch (p.type) {
    case 'lowpass':
      b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = (1 - cw) / 2;
      a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
    case 'highpass':
      b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = (1 + cw) / 2;
      a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
    case 'peaking':
      b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A;
      a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A; break;
    case 'lowshelf': {
      const s = 2 * Math.sqrt(A) * alpha;
      b0 = A * ((A + 1) - (A - 1) * cw + s); b1 = 2 * A * ((A - 1) - (A + 1) * cw); b2 = A * ((A + 1) - (A - 1) * cw - s);
      a0 = (A + 1) + (A - 1) * cw + s; a1 = -2 * ((A - 1) + (A + 1) * cw); a2 = (A + 1) + (A - 1) * cw - s; break;
    }
    case 'highshelf': {
      const s = 2 * Math.sqrt(A) * alpha;
      b0 = A * ((A + 1) + (A - 1) * cw + s); b1 = -2 * A * ((A - 1) + (A + 1) * cw); b2 = A * ((A + 1) + (A - 1) * cw - s);
      a0 = (A + 1) - (A - 1) * cw + s; a1 = 2 * ((A - 1) - (A + 1) * cw); a2 = (A + 1) - (A - 1) * cw - s; break;
    }
    default:
      throw new Error(`eq: unknown type "${p.type}"`);
  }

  const out = new Float32Array(samples.length);
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < samples.length; i++) {
    const x0 = samples[i];
    const y0 = (b0 / a0) * x0 + (b1 / a0) * x1 + (b2 / a0) * x2 - (a1 / a0) * y1 - (a2 / a0) * y2;
    out[i] = clamp(y0);
    x2 = x1; x1 = x0; y2 = y1; y1 = y0;
  }
  return mkClip(out, sampleRate);
}

// ── dynamics ──────────────────────────────────────────────────────────────
/** Compressor with an envelope follower + soft makeup — broadcast presence. */
export function compress(clip, opts = {}) {
  const { samples, sampleRate } = clip;
  const thr = 10 ** ((opts.thresholdDb ?? -18) / 20);
  const ratio = opts.ratio ?? 3;
  const atk = Math.exp(-1 / (((opts.attackMs ?? 8) / 1000) * sampleRate));
  const rel = Math.exp(-1 / (((opts.releaseMs ?? 120) / 1000) * sampleRate));
  const makeup = 10 ** ((opts.makeupDb ?? 0) / 20);

  const out = new Float32Array(samples.length);
  let env = 0;
  for (let i = 0; i < samples.length; i++) {
    const x = Math.abs(samples[i]);
    env = x > env ? atk * env + (1 - atk) * x : rel * env + (1 - rel) * x;
    let g = 1;
    if (env > thr && env > 0) {
      const over = env / thr;
      g = (thr * over ** (1 / ratio)) / env;
    }
    out[i] = clamp(samples[i] * g * makeup);
  }
  return mkClip(out, sampleRate);
}

/**
 * De-esser — a frequency-selective compressor on the sibilance band.
 *
 * Implemented as a proper two-band CROSSOVER: split the signal into low and
 * high with complementary Butterworth filters, compress only the high band, and
 * sum. The naive approach (subtracting a highpassed copy from the original)
 * does NOT work: the filter phase-shifts the band it extracts, so the
 * subtraction fails to cancel and can even ADD energy at the target frequency.
 * Split-and-sum keeps the phase relationship intact.
 */
export function deEss(clip, opts = {}) {
  const freq = opts.freq ?? 6500;
  const amount = Math.max(0, Math.min(1, opts.amount ?? 0.6));
  const high = eq(clip, { type: 'highpass', freq, q: 0.707 });
  const low = eq(clip, { type: 'lowpass', freq, q: 0.707 });
  const tamedHigh = compress(high, {
    thresholdDb: opts.thresholdDb ?? -30,
    ratio: opts.ratio ?? 6,
    attackMs: 1,
    releaseMs: 40,
  });
  const out = new Float32Array(clip.samples.length);
  for (let i = 0; i < out.length; i++) {
    // low band untouched + the high band blended toward its compressed self
    const h = (1 - amount) * high.samples[i] + amount * tamedHigh.samples[i];
    out[i] = clamp(low.samples[i] + h);
  }
  return mkClip(out, clip.sampleRate);
}

/** Add (or, with a negative amount, suppress) breathiness. */
export function breath(clip, amount = 0.05) {
  const out = new Float32Array(clip.samples.length);
  if (amount >= 0) {
    // shaped noise, gated by the signal's own envelope so it breathes WITH the voice
    let env = 0;
    for (let i = 0; i < out.length; i++) {
      const x = Math.abs(clip.samples[i]);
      env = x > env ? 0.9 * env + 0.1 * x : 0.999 * env;
      out[i] = clamp(clip.samples[i] + amount * env * (Math.sin(i * 12.9898) * 43758.5453 % 1) * 2 - amount * env);
    }
    return mkClip(out, clip.sampleRate);
  }
  // negative → high-shelf cut where breath lives
  return eq(clip, { type: 'highshelf', freq: 5000, gainDb: amount * 40, q: 0.707 });
}

/** Chainable, undoable voice-character session. */
export class VoiceShaper {
  constructor(clip) {
    this._h = [mkClip(Float32Array.from(clip.samples), clip.sampleRate)];
    this._i = 0;
  }
  get clip() { return this._h[this._i]; }
  _push(next) {
    this._h = this._h.slice(0, this._i + 1);
    this._h.push(next);
    this._i++;
    return this;
  }
  pitchShift(semis, o) { return this._push(pitchShift(this.clip, semis, o)); }
  timeStretch(f, o) { return this._push(timeStretch(this.clip, f, o)); }
  formantShift(f, o) { return this._push(formantShift(this.clip, f, o)); }
  eq(p) { return this._push(eq(this.clip, p)); }
  compress(o) { return this._push(compress(this.clip, o)); }
  deEss(o) { return this._push(deEss(this.clip, o)); }
  breath(a) { return this._push(breath(this.clip, a)); }
  undo() { if (this._i > 0) this._i--; return this; }
  redo() { if (this._i < this._h.length - 1) this._i++; return this; }
  get canUndo() { return this._i > 0; }
  get canRedo() { return this._i < this._h.length - 1; }
  toClip() { const c = this.clip; return mkClip(Float32Array.from(c.samples), c.sampleRate); }
}

export default VoiceShaper;
