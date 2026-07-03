/**
 * animate.js — drive the cloned face: MediaPipe 52 ARKit blendshapes + audio → motion.
 *
 * The cloned face animates two ways, both torch-free + in-browser:
 *   1. LIVE reenactment — MediaPipe Face Landmarker's 52 blendshapes (live webcam) → faicey
 *      morph influences (jawOpen→mouth, smile, brows, blink) for the 3D engine; the 2D wireframe
 *      just redraws each frame from the fresh landmarks.
 *   2. Voice lip-sync — the cloned voice's audio amplitude → mouth-open, so the cloned face TALKS
 *      to the cloned voice (the shared ARKit/morph channel is how met4citizen TalkingHead works).
 *
 * Pure functions (no DOM, no model) so the mapping is testable; the studio calls them per frame.
 */

import { LM } from './geometry.js';

const clamp = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

/**
 * Map MediaPipe faceBlendshapes categories → faicey morph influences (0..1).
 * @param {Array<{categoryName:string, score:number}>} categories
 * @returns {{ mouthOpen:number, smile:number, frown:number, browUp:number, browDown:number,
 *             blinkLeft:number, blinkRight:number, pucker:number }}
 */
export function blendshapesToMorphs(categories) {
  const b = Object.create(null);
  for (const c of categories || []) b[c.categoryName] = c.score;
  const g = (k) => b[k] || 0;
  return {
    mouthOpen: clamp(g('jawOpen')),
    smile: clamp((g('mouthSmileLeft') + g('mouthSmileRight')) / 2),
    frown: clamp((g('mouthFrownLeft') + g('mouthFrownRight')) / 2),
    browUp: clamp((g('browInnerUp') + g('browOuterUpLeft') + g('browOuterUpRight')) / 3),
    browDown: clamp((g('browDownLeft') + g('browDownRight')) / 2),
    blinkLeft: clamp(g('eyeBlinkLeft')),
    blinkRight: clamp(g('eyeBlinkRight')),
    pucker: clamp(g('mouthPucker')),
  };
}

/** faicey morph map → the engine's named-morph influences (FaceGeometry morph names). */
export function morphsToEngine(m) {
  return {
    mouth_open: m.mouthOpen,
    smile: m.smile,
    frown: m.frown,
    eyebrows_raised: m.browUp,
    eyebrows_furrowed: m.browDown,
    blink: Math.max(m.blinkLeft, m.blinkRight),
  };
}

/**
 * Audio amplitude (RMS) → mouth-open amount, a cheap viseme proxy for lip-sync.
 * @param {number} rms  ~[0, 0.4]
 * @param {{ gain?:number, floor?:number }} [opts]
 * @returns {number} 0..1
 */
export function audioMouth(rms, opts = {}) {
  const gain = opts.gain ?? 6, floor = opts.floor ?? 0.02;
  return clamp(rms <= floor ? 0 : (rms - floor) * gain);
}

/** RMS over a time-domain frame. */
export function rms(frame) {
  let s = 0;
  for (let i = 0; i < frame.length; i++) s += frame[i] * frame[i];
  return frame.length ? Math.sqrt(s / frame.length) : 0;
}

/**
 * Open the mouth on a cloned-face landmark set by `open` (0..1) for the 2D wireframe lip-sync.
 * Returns a NEW landmark array (originals untouched). Displaces inner lips, mouth corners and the
 * chin, scaled by the inter-ocular distance so it works at any face size.
 */
export function applyMouthOpen(landmarks, open) {
  const out = landmarks.map((p) => (p ? { x: p.x, y: p.y, z: p.z || 0 } : p));
  const a = clamp(open);
  const eyeR = landmarks[LM.eyeInR], eyeL = landmarks[LM.eyeInL];
  const scale = eyeR && eyeL ? Math.hypot(eyeR.x - eyeL.x, eyeR.y - eyeL.y) : 0.1;
  const nudge = (i, dy) => { if (out[i]) out[i].y += dy * a * scale; };
  nudge(LM.lipTop, -0.18);    // upper lip up a touch
  nudge(LM.lipBot, 0.55);     // lower lip down
  nudge(LM.upperLip, -0.12);
  nudge(17, 0.35);            // outer lower lip
  nudge(LM.mouthR, 0.12); nudge(LM.mouthL, 0.12); // corners drop slightly
  nudge(LM.chin, 0.30);      // jaw opens
  return out;
}
