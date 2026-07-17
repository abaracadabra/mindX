/**
 * spectrogram.js — the waterfall: a scrolling time–frequency history of the
 * signal. Each FFT frame becomes a row; older rows flow down. The spatial axis
 * is frequency, the COLOUR axis is intensity in dB — the scientifically correct
 * spectrogram, on a perceptual colormap.
 *
 * The FFT + spectrum come from oscilloscope.js; this module is the display
 * model: dB scaling, a rolling frame buffer, and the perceptual colormaps
 * (inferno is the de-facto spectrogram standard). Pure + headless-tested; the
 * canvas scroll lives in the demo.
 *
 * © Professor Codephreak - rage.pythai.net
 */

/**
 * Magnitude → normalised dB in [0,1] for display.
 * @param {number} mag     linear magnitude (≥ 0)
 * @param {number} ref     reference (the frame/running max) mapped to 0 dB → 1
 * @param {number} floorDb the bottom of the scale (e.g. −90 dB → 0)
 */
export function dbNorm(mag, ref, floorDb = -90) {
  if (!(ref > 0)) return 0;
  const db = 20 * Math.log10((mag > 0 ? mag : 0) / ref + 1e-12); // ≤ 0
  return Math.max(0, Math.min(1, 1 + db / -floorDb));
}

/** Vectorised dbNorm over a magnitude row; ref defaults to the row's own max. */
export function magnitudesToDb(mags, opts = {}) {
  const floorDb = opts.floorDb ?? -90;
  let ref = opts.refMax;
  if (ref == null) { ref = 1e-9; for (let i = 0; i < mags.length; i++) if (mags[i] > ref) ref = mags[i]; }
  const out = new Float32Array(mags.length);
  for (let i = 0; i < mags.length; i++) out[i] = dbNorm(mags[i], ref, floorDb);
  return out;
}

// ── inferno colormap (perceptual; the spectrogram standard) ─────────────────
const INFERNO = [
  [0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99],
  [212, 72, 66], [245, 125, 21], [250, 193, 39], [252, 255, 164],
];
const MAGMA = [
  [0, 0, 4], [40, 15, 96], [109, 31, 119], [181, 54, 122],
  [237, 105, 100], [251, 160, 108], [254, 209, 144], [252, 253, 191],
];
function ramp(stops, t) {
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1);
  const i = Math.floor(x), f = x - i, a = stops[i], b = stops[Math.min(stops.length - 1, i + 1)];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}
/** Perceptual intensity colormap: 0 → near-black, 1 → bright. */
export function inferno(t) { return ramp(INFERNO, t); }
export function magma(t) { return ramp(MAGMA, t); }
export const COLORMAPS = { inferno, magma };

/**
 * Source spectrum bin for a display column, on a LOG-frequency axis
 * (voice reads better log-scaled). x ∈ [0,W) → a bin index.
 */
export function logBinForX(x, W, fmin, fmax, binHz) {
  const t = W > 1 ? x / (W - 1) : 0;
  const f = fmin * Math.pow(fmax / fmin, t);
  return Math.max(0, Math.round(f / binHz));
}
/** Linear-frequency version, to align with a linear spectrum display. */
export function linBinForX(x, W, fmax, binHz) {
  const f = (x / Math.max(1, W)) * fmax;
  return Math.max(0, Math.round(f / binHz));
}

/**
 * A rolling frame buffer — the spectrogram model (for freeze/export and tests).
 * The live demo scrolls the canvas directly, but the model keeps the history.
 */
export class Spectrogram {
  constructor(rows = 128) { this.rows = rows; this.buf = []; }
  push(row) { this.buf.push(row instanceof Float32Array ? row : Float32Array.from(row)); if (this.buf.length > this.rows) this.buf.shift(); return this; }
  frames() { return this.buf; }
  get length() { return this.buf.length; }
  latest() { return this.buf.length ? this.buf[this.buf.length - 1] : null; }
  clear() { this.buf = []; return this; }
}

export default Spectrogram;
