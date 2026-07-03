/**
 * runtime.js — lazy, optional onnxruntime-node loader.
 *
 * voaice's analysis core stays zero-dep; the neural engine is an opt-in accelerator (same
 * philosophy as meyda/audiomotion). `onnxruntime-node` is an optionalDependency: if it is
 * not installed we surface a single, actionable error rather than a raw MODULE_NOT_FOUND.
 * CPU execution provider only — no torch, no CUDA, VPS-safe.
 */

let _ort = null;
let _probed = false;

/**
 * Resolve the onnxruntime-node module, or null if it is not installed.
 * @returns {Promise<object|null>}
 */
export async function tryLoadOrt() {
  if (_probed) return _ort;
  _probed = true;
  try {
    const mod = await import('onnxruntime-node');
    _ort = mod.default || mod;
  } catch {
    _ort = null;
  }
  return _ort;
}

/** Like tryLoadOrt but throws a helpful error when the runtime is missing. */
export async function requireOrt() {
  const ort = await tryLoadOrt();
  if (!ort) {
    throw new Error(
      'voaice neural: onnxruntime-node is not installed. Run `npm i onnxruntime-node` ' +
        'in voaice (CPU, torch-free) to enable the neural voice engine.'
    );
  }
  return ort;
}

/**
 * Create a CPU inference session from a model file path.
 * @param {string} modelPath
 * @returns {Promise<object>} ort.InferenceSession
 */
export async function createSession(modelPath) {
  const ort = await requireOrt();
  return ort.InferenceSession.create(modelPath, {
    executionProviders: ['cpu'],
    graphOptimizationLevel: 'all',
  });
}

/** Build an ort.Tensor (helper so call sites don't import ort directly). */
export async function tensor(type, data, dims) {
  const ort = await requireOrt();
  return new ort.Tensor(type, data, dims);
}
