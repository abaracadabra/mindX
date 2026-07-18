/**
 * mech.js — the human ↔ machine slider.
 *
 * One side of the face morphs, on a sliding scale, from human into a tough,
 * detailed **endoskeleton** — the exposed-metal cyborg trope: skull plating,
 * rivets, a red optical sensor over the eye, a servo jaw. It is rendered
 * procedurally from the face landmarks (so it tracks and expresses), generic —
 * not a trace of any one film's character.
 *
 * This module is the pure part: which side a point is on, how mechanised it is
 * at a given slider level (a soft seam down the centre line), and the palette.
 * The endoskeleton draw is the demo's browser layer.
 *
 * © Professor Codephreak - rage.pythai.net
 */

export const MECH_PALETTE = Object.freeze({
  steel: '#8b9199', steelDark: '#3a3f45', steelLo: '#20242a',
  rivet: '#c8ccd2', servo: '#5a6068', optic: '#ff2a17', opticGlow: 'rgba(255,42,23,0.55)',
  // polished-chrome tones for the reflective, high-detail cyborgi endoskeleton
  chromeHi: '#f2f6fa', chrome: '#aeb8c1', chromeMid: '#7c868f', chromeLo: '#242a30',
  seam: '#0b0d10', edge: '#e6eef4', spec: '#ffffff',
  coolRim: 'rgba(120,200,255,0.55)', warmRim: 'rgba(255,150,90,0.35)', opticHot: '#ffe9d8',
});

/**
 * Mechanisation of a point in canvas space, 0..1.
 * On the human side it is 0; crossing the centre line it ramps up over a soft
 * `seam` to the slider `level` — a sliding scale, not a hard split.
 * @param {number} x        point x (canvas)
 * @param {number} centerX  face centre-line x
 * @param {number} level    slider 0..1 (human → full mech)
 * @param {{side?:'right'|'left', seam?:number}} [opts]
 */
export function mechFactor(x, centerX, level, opts = {}) {
  const side = opts.side || 'right', seam = opts.seam ?? 40;
  const past = side === 'right' ? x - centerX : centerX - x;
  if (past <= 0) return 0;                       // the human half
  const ramp = seam > 0 ? Math.min(1, past / seam) : 1;
  return Math.max(0, Math.min(1, level)) * ramp;
}

/** Face centre-line x (mean of the landmark x), in canvas space via `fit`. */
export function faceCenterX(landmarks, fit) {
  let sx = 0, n = 0;
  for (const lm of landmarks) { if (!lm) continue; sx += fit(lm).x; n++; }
  return n ? sx / n : 0;
}

/** Is this feature-name on the mechanised side, at all? (for whole-feature swaps) */
export function featureIsMech(cx, centerX, level, opts = {}) {
  return level > 0 && mechFactor(cx, centerX, level, opts) > 0;
}

export default mechFactor;
