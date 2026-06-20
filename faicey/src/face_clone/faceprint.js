/**
 * faceprint.js — the SCIENTIFIC forensic FACE measuring tool.
 *
 * The visual sibling of voaice's Scientific.js voiceprint. Turns a person's facial geometry
 * (a set of scale/pose-invariant inter-landmark RATIOS) into a reproducible, forensic-grade
 * faceprint measured to 18 decimals of precision, ready for on-chain registration — mirroring
 * `SoundWaveToken.registerVoicePrint(...)` with a `registerFacePrint(hash, uint256[N], precision)`.
 *
 * Pure JS, zero model (sha256 via node:crypto in Node, SubtleCrypto in the browser). The ratios
 * are anchored to the inter-ocular distance, so the print is invariant to face size, position and
 * (after pose-normalisation upstream) head rotation: same face → same measures → same hash.
 *
 * The ordered measure set IS the identity vector — same-person test = L2/cosine on the ratios.
 */

const ONE = 10n ** 18n; // 18-decimal fixed-point scale (matches Scientific.js / SoundWaveToken.ONE)

/** Real number → 18-decimal fixed-point BigInt (real × 1e18), 9 real decimals kept then padded. */
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

// Canonical ordered measure set — interpretable, scale/pose-invariant facial ratios. The ORDER is
// part of the contract (the on-chain uint256[] layout); never reorder, only append.
export const FACEPRINT_MEASURES = [
  'faceAspect',       // faceHeight / faceWidth
  'jawRatio',         // jawWidth / faceWidth
  'cheekRatio',       // cheekboneWidth / faceWidth
  'interocularRatio', // inter-ocular distance / faceWidth
  'eyeWidthRatio',    // mean eye width / faceWidth
  'noseLengthRatio',  // nose length / faceHeight
  'noseWidthRatio',   // nose (alar) width / faceWidth
  'mouthWidthRatio',  // mouth width / faceWidth
  'lipHeightRatio',   // lip height / faceHeight
  'philtrumRatio',    // subnasale→upper-lip / faceHeight
  'browEyeRatio',     // brow→eye gap / faceHeight
  'chinRatio',        // lower-lip→chin / faceHeight
];

/** sha256 hex, in Node or the browser. */
async function sha256Hex(str) {
  if (typeof process !== 'undefined' && process.versions && process.versions.node) {
    const { createHash } = await import('node:crypto');
    return createHash('sha256').update(str).digest('hex');
  }
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Measure a faceprint from a `FacialProportions` ratio object (see geometry.js).
 * @param {Record<string, number>} proportions  ratio measures (extra keys ignored)
 * @param {{ confidence?: number, symmetry?: number, frontality?: number }} [quality]
 * @returns {Promise<{
 *   measures: bigint[], measuresStr: string[], measureNames: string[],
 *   precisionScore: bigint, hash: string, payload: object, vector: number[]
 * }>}
 */
export async function measureFaceprint(proportions, quality = {}) {
  const vector = FACEPRINT_MEASURES.map((k) => Number(proportions[k]) || 0);
  const measures = vector.map(toFixed18);

  // composite precision/confidence in [0,1]: detection confidence × symmetry × frontality
  const confidence = clamp01(quality.confidence ?? 1);
  const symmetry = clamp01(quality.symmetry ?? 1);
  const frontality = clamp01(quality.frontality ?? 1);
  const precision = clamp01(0.5 * confidence + 0.3 * symmetry + 0.2 * frontality);
  const precisionScore = toFixed18(precision);

  // canonical payload → sha256 (reproducible: same measures ⇒ same hash ⇒ uniqueness)
  const payload = {
    v: 1,
    kind: 'faceprint',
    measureNames: FACEPRINT_MEASURES,
    measures: measures.map((x) => x.toString()),
    precisionScore: precisionScore.toString(),
  };
  const hash = '0x' + (await sha256Hex(JSON.stringify(payload)));

  return {
    measures,
    measuresStr: measures.map((x) => x.toString()),
    measureNames: FACEPRINT_MEASURES,
    precisionScore,
    hash,
    payload,
    vector,
  };
}

/**
 * Shape a faceprint into registerFacePrint arguments (parallels Scientific.toRegisterArgs).
 * @returns {{ hash:string, m:string[], precisionScore:string }}
 */
export function toRegisterArgs(faceprint) {
  return {
    hash: faceprint.hash,
    m: faceprint.measuresStr,
    precisionScore: faceprint.precisionScore.toString(),
  };
}

/** Identity distance between two faceprints' ratio vectors (L2). Lower = more similar. */
export function faceprintDistance(a, b) {
  const va = a.vector || a, vb = b.vector || b;
  let s = 0;
  for (let i = 0; i < Math.min(va.length, vb.length); i++) s += (va[i] - vb[i]) ** 2;
  return Math.sqrt(s);
}

function clamp01(v) {
  return v < 0 ? 0 : v > 1 ? 1 : v;
}
