/**
 * classical_enhance.js — the classical enhancement fallback.
 *
 * When no neural model is loaded, the affine photoreal composite (2.6) still has
 * two honest defects: triangle SEAMS from the per-triangle warp, and softness
 * where the texture was stretched. Classical DSP can fix both — no weights, no
 * ONNX, no GPU, fully deterministic and headless-testable:
 *
 *   feather the seams (edge-softening blend) → restore detail (unsharp mask)
 *   → gentle tone (contrast curve).
 *
 * This is a REAL improvement over the raw composite, and it is honestly labeled
 * `classical` — so the fidelity gate (neural_render.js) caps it at `realism` BY
 * CONSTRUCTION. It can never earn `hyperreal`; only a neural render can. This is
 * the middle rung: better than raw affine, still not synthesis.
 *
 * All functions take and return an ImageData-shaped { data, width, height }
 * (RGBA), leave alpha untouched, and never mutate the input.
 *
 * © Professor Codephreak - rage.pythai.net
 */

const clampByte = (v) => (v < 0 ? 0 : v > 255 ? 255 : v);
const clampIdx = (v, hi) => (v < 0 ? 0 : v > hi ? hi : v);

/** Separable box blur over the RGB channels (alpha copied). radius in pixels. */
export function boxBlur(img, radius = 1) {
  const { width: w, height: h, data: src } = img;
  const k = Math.max(0, radius | 0);
  if (k === 0) return { data: new Uint8ClampedArray(src), width: w, height: h };
  const tmp = new Float32Array(src.length);
  const out = new Uint8ClampedArray(src.length);
  // horizontal pass → tmp
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = (y * w + x) * 4;
    for (let c = 0; c < 3; c++) {
      let s = 0, n = 0;
      for (let dx = -k; dx <= k; dx++) { s += src[(y * w + clampIdx(x + dx, w - 1)) * 4 + c]; n++; }
      tmp[o + c] = s / n;
    }
    tmp[o + 3] = src[o + 3];
  }
  // vertical pass → out
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = (y * w + x) * 4;
    for (let c = 0; c < 3; c++) {
      let s = 0, n = 0;
      for (let dy = -k; dy <= k; dy++) { s += tmp[(clampIdx(y + dy, h - 1) * w + x) * 4 + c]; n++; }
      out[o + c] = Math.round(s / n);
    }
    out[o + 3] = src[o + 3];
  }
  return { data: out, width: w, height: h };
}

/** Blend a blurred copy in to soften affine triangle seams. blend ∈ [0,1]. */
export function featherSeams(img, { radius = 1, blend = 0.3 } = {}) {
  const b = boxBlur(img, radius);
  const src = img.data, bl = b.data;
  const out = new Uint8ClampedArray(src.length);
  const t = Math.max(0, Math.min(1, blend));
  for (let i = 0; i < src.length; i += 4) {
    for (let c = 0; c < 3; c++) out[i + c] = clampByte(Math.round(src[i + c] * (1 - t) + bl[i + c] * t));
    out[i + 3] = src[i + 3];
  }
  return { data: out, width: img.width, height: img.height };
}

/** Unsharp mask: out = in + amount·(in − blur(in)). Restores perceived detail. */
export function unsharpMask(img, { amount = 0.5, radius = 1 } = {}) {
  const b = boxBlur(img, radius);
  const src = img.data, bl = b.data;
  const out = new Uint8ClampedArray(src.length);
  for (let i = 0; i < src.length; i += 4) {
    for (let c = 0; c < 3; c++) out[i + c] = clampByte(Math.round(src[i + c] + amount * (src[i + c] - bl[i + c])));
    out[i + 3] = src[i + 3];
  }
  return { data: out, width: img.width, height: img.height };
}

/** Gentle tone: push values away from mid-grey by `contrast`, optional gamma. */
export function toneCurve(img, { contrast = 1.05, gamma = 1 } = {}) {
  const src = img.data;
  const out = new Uint8ClampedArray(src.length);
  const g = 1 / (gamma || 1);
  for (let i = 0; i < src.length; i += 4) {
    for (let c = 0; c < 3; c++) {
      let v = src[i + c] / 255;
      v = (v - 0.5) * contrast + 0.5;
      v = v <= 0 ? 0 : Math.pow(v, g);
      out[i + c] = clampByte(Math.round(v * 255));
    }
    out[i + 3] = src[i + 3];
  }
  return { data: out, width: img.width, height: img.height };
}

/**
 * The classical enhancement pipeline: soften seams → restore detail → tone.
 * A real improvement over the raw affine composite; caps at realism.
 */
export function enhanceClassical(img, opts = {}) {
  const seam = opts.seam ?? { radius: 1, blend: 0.3 };
  const sharp = opts.sharp ?? { amount: 0.5, radius: 1 };
  const tone = opts.tone ?? { contrast: 1.05 };
  let x = featherSeams(img, seam);
  x = unsharpMask(x, sharp);
  x = toneCurve(x, tone);
  return x;
}

/**
 * A backend with the same shape as NeuralRenderer, but classical — always
 * available (no weights), and honestly labeled so the gate caps it at realism.
 */
export class ClassicalEnhancer {
  constructor(opts = {}) { this.opts = opts; }
  describe() {
    return { available: true, backend: 'classical',
      note: 'seam-feather + unsharp + tone — a real fix for affine seams/softness; caps at realism (only a neural render earns hyperreal)' };
  }
  async refine(frame) {
    return { image: enhanceClassical(frame, this.opts), backend: 'classical', neural: false };
  }
}

export default ClassicalEnhancer;
