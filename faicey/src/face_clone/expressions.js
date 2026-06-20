/**
 * expressions.js — make a CLONED face emote.
 *
 * The cloned face is a set of MediaPipe landmarks (the person's geometry). To express an emotion we
 * displace the relevant landmarks (mouth corners/lips, brows, eyes) by an emotion-specific delta,
 * scaled by intensity — the landmark analog of voaice's emotion → faicey expression fan-out. The
 * 9-emotion vocabulary matches the voice side, so a persona's voice and face emote in lockstep.
 *
 * Deltas are in normalised landmark units (same space as the landmarks), sized relative to the
 * inter-ocular distance so the expression scales with any face. Pure JS, no model.
 */

import { LM } from './geometry.js';

// emotion → landmark deltas (× intensity × inter-ocular scale). +y is down (image space).
// mouth: corners (61,291) and lip centres (13 upper, 14 lower); brows (105 R, 334 L inner ends);
// eyes: lids (159/386 top) for openness.
const EXPR = {
  neutral:   { mouthCorner: 0.00, lipOpen: 0.00, browInner: 0.00, eyeOpen: 0.00, hue: 150 },
  happy:     { mouthCorner: -0.10, lipOpen: 0.03, browInner: -0.02, eyeOpen: 0.01, hue: 90 },
  excited:   { mouthCorner: -0.10, lipOpen: 0.08, browInner: -0.05, eyeOpen: 0.05, hue: 60 },
  calm:      { mouthCorner: -0.05, lipOpen: 0.00, browInner: 0.00, eyeOpen: 0.00, hue: 175 },
  sad:       { mouthCorner: 0.09, lipOpen: 0.00, browInner: -0.06, eyeOpen: -0.03, hue: 215 },
  angry:     { mouthCorner: 0.03, lipOpen: 0.00, browInner: 0.07, eyeOpen: -0.03, hue: 0 },
  surprised: { mouthCorner: 0.00, lipOpen: 0.12, browInner: -0.08, eyeOpen: 0.07, hue: 45 },
  confused:  { mouthCorner: 0.02, lipOpen: 0.01, browInner: 0.04, eyeOpen: 0.01, hue: 280 },
  thinking:  { mouthCorner: 0.01, lipOpen: 0.00, browInner: 0.03, eyeOpen: -0.01, hue: 195 },
};

export const EXPRESSION_LABELS = Object.keys(EXPR);
const browInnerL = 334; // left inner brow (mirror of 105)
const eyeTopL = 386;

const dist = (p, q) => (p && q ? Math.hypot(p.x - q.x, p.y - q.y) : 1e-6);

/**
 * Return a NEW landmark array with the emotion applied (originals untouched).
 * @param {Array<{x:number,y:number,z:number}>} landmarks
 * @param {string|{label?:string,intensity?:number}} emotion
 * @param {number} [intensity] override (0..1)
 * @returns {{ landmarks:Array, hue:number, label:string }}
 */
export function applyExpression(landmarks, emotion, intensity) {
  let label = typeof emotion === 'string' ? emotion : (emotion && emotion.label) || 'neutral';
  let amt = intensity ?? (emotion && typeof emotion.intensity === 'number' ? emotion.intensity : 0.8);
  if (!EXPR[label]) label = 'neutral';
  amt = Math.max(0, Math.min(1, amt));
  const e = EXPR[label];
  const out = landmarks.map((p) => (p ? { x: p.x, y: p.y, z: p.z || 0 } : p));
  const scale = dist(landmarks[LM.eyeInR], landmarks[LM.eyeInL]) || 0.1;
  const nudge = (i, dy, dx = 0) => { if (out[i]) { out[i].y += dy * amt * scale; out[i].x += dx * amt * scale; } };

  // mouth corners turn up (smile, negative y) / down (frown, positive y), symmetric
  nudge(LM.mouthR, e.mouthCorner, 0); nudge(LM.mouthL, e.mouthCorner, 0);
  // jaw / lips open
  nudge(LM.lipTop, -e.lipOpen * 0.4); nudge(LM.lipBot, e.lipOpen);
  // inner brows down (anger) / up (sad, surprise)
  nudge(LM.browR, e.browInner); nudge(browInnerL, e.browInner);
  // eyelids: widen (negative top y) / narrow
  nudge(LM.eyeTopR, -e.eyeOpen); nudge(eyeTopL, -e.eyeOpen);

  return { landmarks: out, hue: e.hue, label };
}

/** The display hue for an emotion (matches the voice-side palette). */
export function expressionHue(label) {
  return (EXPR[label] || EXPR.neutral).hue;
}
