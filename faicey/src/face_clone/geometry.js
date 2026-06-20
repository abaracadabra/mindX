/**
 * geometry.js — MediaPipe landmarks → facial proportions, pose-normalisation, and multi/video
 * aggregation. Pure JS (no model). Works on the 468/478-landmark layout MediaPipe Face Landmarker
 * emits; indices below are the well-known canonical-face-model vertex ids.
 *
 * Three jobs:
 *   1. proportions(landmarks)         — interpretable scale-invariant ratios (the clone params)
 *   2. poseNormalize(landmarks, mat?) — centre + scale (+ optional inverse pose) to canonical space
 *   3. aggregate([frames])            — most-frontal selection + per-vertex averaging (multi/video)
 *
 * A landmark is { x, y, z } (MediaPipe normalised image space; z relative depth). Robust to missing
 * indices — a distance with an out-of-range index degrades to 0 rather than throwing.
 */

// canonical-face-model landmark indices (MediaPipe)
export const LM = {
  faceTop: 10, chin: 152,
  cheekR: 234, cheekL: 454,        // face width
  zygoR: 116, zygoL: 345,          // cheekbone width
  jawR: 172, jawL: 397,            // jaw width
  eyeInR: 133, eyeInL: 362,        // inter-ocular (inner corners)
  eyeOutR: 33, eyeOutL: 263,       // outer corners
  eyeTopR: 159, browR: 105,        // brow→eye gap (right)
  nasion: 168, subnasale: 2, noseTip: 1,
  alaR: 98, alaL: 327,             // nose width
  mouthR: 61, mouthL: 291,         // mouth width
  lipTop: 13, lipBot: 14,          // inner lip height
  upperLip: 0,                     // philtrum lower point
};

const d = (p, q) => (p && q ? Math.hypot(p.x - q.x, p.y - q.y, (p.z || 0) - (q.z || 0)) : 0);
const at = (lms, i) => lms[i];

/**
 * Derive scale-invariant facial proportions (the clone parameters + faceprint ratios).
 * @param {Array<{x:number,y:number,z:number}>} lms  >= 468 landmarks
 * @returns {Record<string, number>}
 */
export function proportions(lms) {
  const faceWidth = d(at(lms, LM.cheekR), at(lms, LM.cheekL)) || 1e-6;
  const faceHeight = d(at(lms, LM.faceTop), at(lms, LM.chin)) || 1e-6;
  const eyeWidthR = d(at(lms, LM.eyeOutR), at(lms, LM.eyeInR));
  const eyeWidthL = d(at(lms, LM.eyeOutL), at(lms, LM.eyeInL));
  return {
    faceWidth, faceHeight,
    faceAspect: faceHeight / faceWidth,
    jawRatio: d(at(lms, LM.jawR), at(lms, LM.jawL)) / faceWidth,
    cheekRatio: d(at(lms, LM.zygoR), at(lms, LM.zygoL)) / faceWidth,
    interocularRatio: d(at(lms, LM.eyeInR), at(lms, LM.eyeInL)) / faceWidth,
    eyeWidthRatio: ((eyeWidthR + eyeWidthL) / 2) / faceWidth,
    noseLengthRatio: d(at(lms, LM.nasion), at(lms, LM.subnasale)) / faceHeight,
    noseWidthRatio: d(at(lms, LM.alaR), at(lms, LM.alaL)) / faceWidth,
    mouthWidthRatio: d(at(lms, LM.mouthR), at(lms, LM.mouthL)) / faceWidth,
    lipHeightRatio: d(at(lms, LM.lipTop), at(lms, LM.lipBot)) / faceHeight,
    philtrumRatio: d(at(lms, LM.subnasale), at(lms, LM.upperLip)) / faceHeight,
    browEyeRatio: d(at(lms, LM.browR), at(lms, LM.eyeTopR)) / faceHeight,
    chinRatio: d(at(lms, LM.lipBot), at(lms, LM.chin)) / faceHeight,
  };
}

/** Left-right symmetry score in [0,1] (1 = perfectly symmetric) from mirrored landmark pairs. */
export function symmetry(lms) {
  const cx = (at(lms, LM.cheekR).x + at(lms, LM.cheekL).x) / 2;
  const pairs = [[LM.eyeInR, LM.eyeInL], [LM.eyeOutR, LM.eyeOutL], [LM.alaR, LM.alaL], [LM.mouthR, LM.mouthL], [LM.jawR, LM.jawL]];
  const w = d(at(lms, LM.cheekR), at(lms, LM.cheekL)) || 1e-6;
  let err = 0;
  for (const [r, l] of pairs) {
    const pr = at(lms, r), pl = at(lms, l);
    err += Math.abs((cx - pr.x) - (pl.x - cx)) / w + Math.abs(pr.y - pl.y) / w;
  }
  return Math.max(0, 1 - err / (pairs.length * 2));
}

/**
 * Centre on the face centroid and scale by inter-ocular distance → canonical space. If a 4×4
 * facial transformation matrix is supplied (column-major, MediaPipe), its inverse rotation is
 * applied first so multi-view frames become comparable.
 * @returns {Array<{x:number,y:number,z:number}>}
 */
export function poseNormalize(lms, matrix) {
  let pts = lms.map((p) => ({ x: p.x, y: p.y, z: p.z || 0 }));
  if (matrix && matrix.length === 16) pts = pts.map((p) => applyInverseRotation(p, matrix));
  const cx = mean(pts, 'x'), cy = mean(pts, 'y'), cz = mean(pts, 'z');
  const scale = d(at(pts, LM.eyeInR), at(pts, LM.eyeInL)) || 1e-6;
  return pts.map((p) => ({ x: (p.x - cx) / scale, y: (p.y - cy) / scale, z: (p.z - cz) / scale }));
}

/** Frontality in [0,1] from a pose matrix (1 = facing camera) — used to pick the best frame. */
export function frontality(matrix) {
  if (!matrix || matrix.length !== 16) return 1;
  // yaw/pitch from the rotation block; flat-on ⇒ forward axis ≈ camera axis
  const yaw = Math.atan2(matrix[8], matrix[10]);
  const pitch = Math.atan2(-matrix[9], Math.hypot(matrix[8], matrix[10]));
  return Math.max(0, 1 - (Math.abs(yaw) + Math.abs(pitch)) / Math.PI);
}

/**
 * Aggregate multiple captures (perspective images or video frames) into one denoised landmark set.
 * Pose-normalises each frame, weights by frontality, and averages per-vertex in canonical space —
 * the single biggest quality win over any one frame. Returns the fused landmarks + the chosen
 * frontal frame index + a confidence proxy.
 * @param {Array<{landmarks:Array, matrix?:number[], confidence?:number}>} frames
 * @returns {{ landmarks:Array, frontalIndex:number, frames:number, meanFrontality:number }}
 */
export function aggregate(frames) {
  const valid = frames.filter((f) => f && f.landmarks && f.landmarks.length);
  if (!valid.length) throw new Error('face_clone: no valid frames to aggregate');
  if (valid.length === 1) {
    return { landmarks: valid[0].landmarks, frontalIndex: 0, frames: 1, meanFrontality: frontality(valid[0].matrix) };
  }
  const normed = valid.map((f) => ({ pts: poseNormalize(f.landmarks, f.matrix), w: Math.max(0.05, frontality(f.matrix)) }));
  const N = normed[0].pts.length;
  const out = new Array(N);
  let frontalIndex = 0, best = -1, fsum = 0;
  normed.forEach((f, i) => { if (f.w > best) { best = f.w; frontalIndex = i; } fsum += f.w; });
  const wsum = normed.reduce((a, f) => a + f.w, 0);
  for (let v = 0; v < N; v++) {
    let x = 0, y = 0, z = 0;
    for (const f of normed) { const p = f.pts[v]; x += p.x * f.w; y += p.y * f.w; z += p.z * f.w; }
    out[v] = { x: x / wsum, y: y / wsum, z: z / wsum };
  }
  return { landmarks: out, frontalIndex, frames: valid.length, meanFrontality: fsum / normed.length };
}

// ── helpers ──
function mean(pts, k) { let s = 0; for (const p of pts) s += p[k]; return s / pts.length; }
function applyInverseRotation(p, m) {
  // inverse of a rotation is its transpose; column-major 4×4 → use the 3×3 block transposed
  return {
    x: m[0] * p.x + m[1] * p.y + m[2] * p.z,
    y: m[4] * p.x + m[5] * p.y + m[6] * p.z,
    z: m[8] * p.x + m[9] * p.y + m[10] * p.z,
  };
}
