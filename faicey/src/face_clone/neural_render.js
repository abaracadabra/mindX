/**
 * neural_render.js — the neural renderer SEAM + the fidelity gate.
 *
 * The photoreal renderer (2.6) reaches REALISM: real texture on real geometry,
 * affine-mapped. Hyperrealism — a synthesized face indistinguishable from
 * reality, including novel views and disocclusions the single capture never saw
 * — needs a NEURAL renderer (a GFPGAN/CodeFormer-class refinement net, or a
 * NeRF/Gaussian-splat synthesis model). That model is not something affine
 * warping can fake.
 *
 * This module ships the CAPABILITY, not a claim. Two honest halves:
 *
 *   1. NeuralRenderer — a pluggable backend that runs a real ONNX model when a
 *      runtime + weights are provided, and is DORMANT otherwise (honest
 *      passthrough of the affine composite). No weights are shipped — same
 *      doctrine as voaice's ONNX voices and mindXtrain's dormant CPU bridge.
 *
 *   2. gradeFidelity — the doctrine gate. It MEASURES a render (identity
 *      consistency against the captured faceprint + structural similarity +
 *      coverage) and only stamps `hyperreal` when a NEURAL backend's output
 *      actually passes the thresholds. Nothing else can earn it — the affine /
 *      classical path caps at `realism` BY CONSTRUCTION. Measured, not asserted.
 *
 * Pure JS, browser + Node. The ONNX inference is runtime-specific and guarded;
 * the gate + the metrics are fully testable headless (and are the part that
 * keeps faicey honest).
 *
 * © Professor Codephreak - rage.pythai.net
 */

/** Earned-hyperreal thresholds. A render must clear ALL three, AND be neural. */
export const FIDELITY = Object.freeze({
  IDENTITY_MIN: 0.85,   // the render still measures as the same person
  STRUCTURAL_MIN: 0.90, // it matches the reference structurally (SSIM)
  COVERAGE_MIN: 0.80,   // enough of the face is actually synthesized, not holes
});

const num = (v) => (Number.isFinite(v) ? v : 0);

/**
 * Identity consistency between two faceprint measure vectors → [0,1].
 * 1 = identical geometry (same person); drops as the render's measured face
 * drifts from the captured one. Grounded in the same ratio vector faceprint.js
 * hashes, so "does the render still measure as this person" is a real question.
 */
export function identityConsistency(vecA, vecB) {
  if (!Array.isArray(vecA) || !Array.isArray(vecB) || vecA.length === 0 || vecA.length !== vecB.length) return 0;
  let ss = 0, na = 0;
  for (let i = 0; i < vecA.length; i++) {
    const a = num(vecA[i]), b = num(vecB[i]);
    ss += (a - b) ** 2; na += a * a;
  }
  const rms = Math.sqrt(ss / vecA.length);
  const scale = Math.sqrt(na / vecA.length) || 1;   // relative to the print's own magnitude
  return Math.max(0, Math.min(1, 1 - rms / scale));
}

/**
 * Global SSIM between two luminance arrays (values in [0,1]) → [0,1].
 * Compares mean (luminance), variance (contrast) and covariance (structure).
 * The browser computes the arrays from ImageData; here it is a pure function.
 */
export function structuralSimilarity(a, b) {
  const n = Math.min(a?.length || 0, b?.length || 0);
  if (!n) return 0;
  let ma = 0, mb = 0;
  for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; }
  ma /= n; mb /= n;
  let va = 0, vb = 0, cov = 0;
  for (let i = 0; i < n; i++) { const da = a[i] - ma, db = b[i] - mb; va += da * da; vb += db * db; cov += da * db; }
  va /= n; vb /= n; cov /= n;
  const c1 = 1e-4, c2 = 9e-4; // (0.01·L)², (0.03·L)² for L=1
  const ssim = ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2));
  return Math.max(0, Math.min(1, ssim));
}

/**
 * The fidelity gate — the doctrine enforcer.
 * @param {{backend:?string, identity?:number, structural?:number, coverage?:number, hasTexture?:boolean}} m
 * @returns {{verdict:'surface'|'realism'|'hyperreal', hyperreal:boolean,
 *            backend:?string, identity:number, structural:number, coverage:number,
 *            reasons:string[]}}
 *
 * `hyperreal` is reachable ONLY when backend==='neural' AND all thresholds pass.
 * A classical/affine backend, or a neural render that doesn't measure up, falls
 * back honestly: `realism` if there is real texture, else `surface`.
 */
export function gradeFidelity(m = {}) {
  const identity = num(m.identity), structural = num(m.structural), coverage = num(m.coverage);
  const backend = m.backend || null;
  const hasTexture = !!m.hasTexture;
  const reasons = [];

  if (backend === 'neural') {
    const okId = identity >= FIDELITY.IDENTITY_MIN;
    const okSt = structural >= FIDELITY.STRUCTURAL_MIN;
    const okCov = coverage >= FIDELITY.COVERAGE_MIN;
    if (okId && okSt && okCov) {
      return { verdict: 'hyperreal', hyperreal: true, backend, identity, structural, coverage,
        reasons: ['neural render measured through the gate'] };
    }
    if (!okId) reasons.push(`identity ${identity.toFixed(3)} < ${FIDELITY.IDENTITY_MIN}`);
    if (!okSt) reasons.push(`structural ${structural.toFixed(3)} < ${FIDELITY.STRUCTURAL_MIN}`);
    if (!okCov) reasons.push(`coverage ${coverage.toFixed(3)} < ${FIDELITY.COVERAGE_MIN}`);
    reasons.unshift('neural backend ran but did not measure up — not stamped hyperreal');
  } else if (backend) {
    reasons.push(`${backend} backend cannot earn hyperreal — only a neural render is graded for it`);
  } else {
    reasons.push('no neural backend loaded — hyperreal is not on the table');
  }

  return { verdict: hasTexture ? 'realism' : 'surface', hyperreal: false, backend,
    identity, structural, coverage, reasons };
}

/**
 * A pluggable neural render backend. Dormant until an ONNX runtime + weights are
 * provided — no weights are committed to this repo. When dormant, `refine` is an
 * honest passthrough of the affine composite (and the gate will never call the
 * result hyperreal).
 */
export class NeuralRenderer {
  constructor(opts = {}) {
    this.backend = null;   // null | 'neural'
    this.session = null;   // the loaded ONNX session (or an injected stand-in)
    this.meta = { reason: 'not loaded' };
    this._runtime = opts.runtime || null;
  }

  /** Honest capability report — what a UI/endpoint should surface. */
  describe() {
    return { available: !!this.session, backend: this.backend, ...this.meta };
  }

  /**
   * Load a neural backend. Provide either an already-created `session` (any
   * object exposing async `run`), or a `runtime` (onnxruntime-web/-node) + a
   * `modelPath` to the weights. With neither, the renderer stays dormant.
   * @returns {Promise<object>} describe()
   */
  async load({ runtime, modelPath, session, dims } = {}) {
    if (session && typeof session.run === 'function') {
      this.session = session; this.backend = 'neural';
      this.meta = { modelPath: modelPath || '(injected session)', dims: dims || null };
      return this.describe();
    }
    const rt = runtime || this._runtime || (typeof globalThis !== 'undefined' ? globalThis.ort : null);
    if (!rt || !modelPath) {
      this.session = null; this.backend = null;
      this.meta = { reason: 'no ONNX runtime or weights — neural backend dormant (realism via affine)' };
      return this.describe();
    }
    try {
      this.session = await rt.InferenceSession.create(modelPath);
      this.backend = 'neural';
      this.meta = { modelPath, dims: dims || null };
    } catch (e) {
      this.session = null; this.backend = null;
      this.meta = { reason: `failed to load neural weights: ${e.message}` };
    }
    return this.describe();
  }

  /**
   * Refine an affine-composited frame into a neural render.
   * @param {{data:Uint8ClampedArray|Uint8Array, width:number, height:number}} frame
   *   the 2.6 affine photoreal composite (ImageData-shaped)
   * @param {{mask?:Uint8Array}} [ctx]
   * @returns {Promise<{image:object, backend:?string, neural:boolean}>}
   */
  async refine(frame, ctx = {}) {
    if (!this.session) return { image: frame, backend: null, neural: false }; // dormant → passthrough
    const image = await this._infer(frame, ctx);
    return { image, backend: 'neural', neural: true };
  }

  /**
   * Run the ONNX model. Contract: NCHW float32 RGB in [0,1] in, same-shape out.
   * Runtime-specific (guarded); executes only when a real session is loaded.
   */
  async _infer(frame, _ctx) {
    const { data, width: W, height: H } = frame;
    const chw = new Float32Array(3 * W * H);
    const plane = W * H;
    for (let i = 0, p = 0; i < data.length; i += 4, p++) {
      chw[p] = data[i] / 255; chw[plane + p] = data[i + 1] / 255; chw[2 * plane + p] = data[i + 2] / 255;
    }
    const inName = this.session.inputNames?.[0] || 'input';
    const outName = this.session.outputNames?.[0] || 'output';
    const out = await this.session.run({ [inName]: { data: chw, dims: [1, 3, H, W], type: 'float32' } });
    const y = (out[outName] && out[outName].data) || out.data || chw;
    const image = { data: new Uint8ClampedArray(data.length), width: W, height: H };
    for (let p = 0; p < plane; p++) {
      const i = p * 4;
      image.data[i] = clampByte(y[p]); image.data[i + 1] = clampByte(y[plane + p]);
      image.data[i + 2] = clampByte(y[2 * plane + p]); image.data[i + 3] = 255;
    }
    return image;
  }
}

function clampByte(v) { const x = Math.round((v || 0) * 255); return x < 0 ? 0 : x > 255 ? 255 : x; }

/** Coverage: fraction of face-region pixels the render actually filled (non-hole). */
export function renderCoverage(mask) {
  if (!mask || !mask.length) return 0;
  let filled = 0;
  for (let i = 0; i < mask.length; i++) if (mask[i]) filled++;
  return filled / mask.length;
}

export default NeuralRenderer;
