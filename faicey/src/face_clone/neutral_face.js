/**
 * neutral_face.js — a real, procedural NEUTRAL face.
 *
 * The demo used to render a ~30-point schematic blob. This synthesises an actual
 * anatomical face at the CANONICAL MediaPipe landmark indices — the same indices
 * a cloned face carries — so the existing renderers (contours.js / face3d.js) and
 * the expression system (expressions.js) work on it UNCHANGED. Feed it a webcam
 * clone later and nothing downstream has to change; the neutral face is just the
 * face before anyone is in front of the camera.
 *
 * Method: each feature is a parametric anatomical curve (face oval, almond eyes,
 * brow arcs, the cupid's-bow lips, the nose), sampled and mapped 1:1 onto that
 * feature's ordered MediaPipe index loop. The result is a 478-entry landmark
 * array with real eyes, brows, a nose with nostrils, and lips — not a blob.
 *
 *   import { neutralFace } from './neutral_face.js';
 *   const landmarks = neutralFace();            // 478 landmarks, normalised
 *   render(landmarks); applyExpression(landmarks, 'happy');
 *
 * Normalised image space: x,y in ~[0,1], +y DOWN (MediaPipe convention), a small
 * z for depth (nose forward, eyes/temples back). Pure JS, no model, no DOM.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { CONTOURS } from './contours.js';

const TAU = Math.PI * 2;
const lerp = (a, b, t) => a + (b - a) * t;

// Feature centres & radii in normalised units. Face centred at (0.5, 0.5).
const FACE = {
  cx: 0.5, cy: 0.52, rx: 0.26, ry: 0.36,   // face oval
  eyeY: 0.44, eyeDX: 0.13, eyeRx: 0.07, eyeRy: 0.032, // eyes (from centre)
  browY: 0.38, browDX: 0.13, browRx: 0.085, browArch: 0.03,
  noseTopY: 0.40, noseTipY: 0.545, noseW: 0.045,
  mouthY: 0.66, mouthRx: 0.10, mouthRy: 0.035,
};

/** Sample a closed ellipse-ish ring into `n` points, starting at angle a0. */
function ring(cx, cy, rx, ry, n, a0 = -Math.PI / 2, z = 0, squash = null) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = a0 + (i / n) * TAU;
    let x = cx + Math.cos(a) * rx;
    let y = cy + Math.sin(a) * ry;
    if (squash) ({ x, y } = squash(x, y, a, cx, cy));
    pts.push({ x, y, z });
  }
  return pts;
}

/** Assign an ordered list of points to an ordered list of MediaPipe indices. */
function assign(out, indices, pts) {
  const n = Math.min(indices.length, pts.length);
  for (let i = 0; i < n; i++) out[indices[i]] = pts[i];
}

/** Almond eye: an ellipse pinched at the corners so it reads as an eye, not a circle. */
function almond(cx, cy, rx, ry, n, z) {
  return ring(cx, cy, rx, ry, n, Math.PI, z, (x, y, a) => {
    // pinch vertical extent toward the corners (cos(a) near ±1)
    const pinch = 0.35 + 0.65 * Math.abs(Math.sin(a));
    return { x, y: cy + (y - cy) * pinch };
  });
}

/** Brow arc: an open arch above the eye. */
function browArc(cx, cy, rx, arch, n, z) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const x = cx - rx + t * 2 * rx;
    const y = cy - Math.sin(t * Math.PI) * arch;
    pts.push({ x, y, z });
  }
  return pts;
}

/**
 * Build the canonical neutral face.
 * @param {{cx?:number, cy?:number, scale?:number}} [opts] recentre / rescale
 * @returns {Array<{x:number,y:number,z:number}>} 478 landmarks (feature indices filled)
 */
export function neutralFace(opts = {}) {
  const F = { ...FACE };
  const out = new Array(478).fill(null);

  // — face oval — the ordered loop runs clockwise from the forehead (index 10) —
  assign(out, CONTOURS.faceOval,
    ring(F.cx, F.cy, F.rx, F.ry, CONTOURS.faceOval.length, -Math.PI / 2, -0.04));

  // — eyes — right eye is the viewer-left almond (MediaPipe "right" = subject's) —
  const rEyeCx = F.cx - F.eyeDX, lEyeCx = F.cx + F.eyeDX;
  assign(out, CONTOURS.rightEye, almond(rEyeCx, F.eyeY, F.eyeRx, F.eyeRy, CONTOURS.rightEye.length, 0.01));
  assign(out, CONTOURS.leftEye, almond(lEyeCx, F.eyeY, F.eyeRx, F.eyeRy, CONTOURS.leftEye.length, 0.01));

  // — brows —
  assign(out, CONTOURS.rightBrow, browArc(rEyeCx, F.browY, F.browRx, F.browArch, CONTOURS.rightBrow.length, 0.0));
  assign(out, CONTOURS.leftBrow, browArc(lEyeCx, F.browY, F.browRx, F.browArch, CONTOURS.leftBrow.length, 0.0));

  // — nose — bridge (nasion → tip, coming forward in z) + the nostril base —
  const bridge = CONTOURS.noseBridge.map((_, i) => {
    const t = i / (CONTOURS.noseBridge.length - 1);
    return { x: F.cx, y: lerp(F.noseTopY, F.noseTipY, t), z: 0.02 + t * 0.10 }; // tip juts forward
  });
  assign(out, CONTOURS.noseBridge, bridge);
  const nb = CONTOURS.noseBottom.length;
  const noseBottom = CONTOURS.noseBottom.map((_, i) => {
    const t = i / (nb - 1);                    // left ala → subnasale → right ala
    const x = F.cx + (t - 0.5) * 2 * F.noseW;
    const dip = Math.sin(t * Math.PI);         // subnasale sits a touch higher
    return { x, y: F.noseTipY + 0.012 - dip * 0.006, z: 0.05 };
  });
  assign(out, CONTOURS.noseBottom, noseBottom);

  // — lips — the cupid's bow: outer contour with a dip at the philtrum —
  const lo = CONTOURS.lipsOuter.length;
  const lips = ring(F.cx, F.mouthY, F.mouthRx, F.mouthRy, lo, Math.PI, 0.02, (x, y, a, cx, cy) => {
    const upper = Math.sin(a) < 0;             // upper lip half
    let yy = y;
    if (upper) {
      // cupid's bow: dip at centre (a≈-π/2), peaks either side
      const centre = Math.cos(a);              // −1..1 across the mouth
      yy = cy + (y - cy) * (0.7 + 0.5 * Math.abs(centre)) - (1 - Math.abs(centre)) * 0.006;
    } else {
      yy = cy + (y - cy) * 1.15;               // fuller lower lip
    }
    return { x, y: yy };
  });
  assign(out, CONTOURS.lipsOuter, lips);

  // — named singletons the expression/measurement code reads by index —
  out[1] = { x: F.cx, y: F.noseTipY, z: 0.13 };      // nose tip (furthest forward)
  out[168] = { x: F.cx, y: F.noseTopY, z: 0.0 };     // nasion
  out[2] = { x: F.cx, y: F.noseTipY + 0.012, z: 0.05 }; // subnasale
  out[133] = { x: rEyeCx + F.eyeRx, y: F.eyeY, z: 0.01 }; // right eye inner corner
  out[362] = { x: lEyeCx - F.eyeRx, y: F.eyeY, z: 0.01 }; // left eye inner corner
  out[33] = { x: rEyeCx - F.eyeRx, y: F.eyeY, z: 0.0 };   // right eye outer
  out[263] = { x: lEyeCx + F.eyeRx, y: F.eyeY, z: 0.0 };  // left eye outer
  out[159] = { x: rEyeCx, y: F.eyeY - F.eyeRy, z: 0.01 }; // right upper lid
  out[386] = { x: lEyeCx, y: F.eyeY - F.eyeRy, z: 0.01 }; // left upper lid
  out[105] = { x: rEyeCx, y: F.browY - F.browArch, z: 0 }; // right inner brow
  out[334] = { x: lEyeCx, y: F.browY - F.browArch, z: 0 }; // left inner brow
  out[13] = { x: F.cx, y: F.mouthY - 0.008, z: 0.02 };   // inner upper lip
  out[14] = { x: F.cx, y: F.mouthY + 0.008, z: 0.02 };   // inner lower lip
  out[0] = { x: F.cx, y: F.mouthY - F.mouthRy - 0.004, z: 0.02 }; // philtrum
  out[61] = { x: F.cx - F.mouthRx, y: F.mouthY, z: 0.01 };  // mouth right corner
  out[291] = { x: F.cx + F.mouthRx, y: F.mouthY, z: 0.01 }; // mouth left corner
  out[10] = { x: F.cx, y: F.cy - F.ry, z: -0.04 };         // forehead top
  out[152] = { x: F.cx, y: F.cy + F.ry, z: -0.02 };        // chin
  // cheekbones (zygomatic) — narrower than the widest face point, at eye level;
  // geometry.proportions() reads these (116/345) for cheekRatio, and they sit in
  // no contour loop, so they must be placed explicitly or the faceprint degenerates.
  out[116] = { x: F.cx - F.rx * 0.9, y: F.eyeY + 0.04, z: -0.02 };  // right cheekbone
  out[345] = { x: F.cx + F.rx * 0.9, y: F.eyeY + 0.04, z: -0.02 };  // left cheekbone

  // — iris centres (478-model accents drawn by contours.js) —
  out[468] = { x: rEyeCx, y: F.eyeY, z: 0.02 };  // right iris
  out[473] = { x: lEyeCx, y: F.eyeY, z: 0.02 };  // left iris

  // Fill any remaining nulls near the face centre so array ops never hit holes,
  // but keep them OUT of the visible feature space (behind, tiny).
  for (let i = 0; i < out.length; i++) {
    if (!out[i]) out[i] = { x: F.cx, y: F.cy, z: -0.2 };
  }

  // optional recentre / rescale
  if (opts.cx != null || opts.cy != null || opts.scale != null) {
    const s = opts.scale ?? 1, dx = (opts.cx ?? F.cx) - F.cx, dy = (opts.cy ?? F.cy) - F.cy;
    for (const p of out) {
      p.x = F.cx + (p.x - F.cx) * s + dx;
      p.y = F.cy + (p.y - F.cy) * s + dy;
      p.z *= s;
    }
  }
  return out;
}

/** The set of indices this neutral face actually places (for tests / sanity). */
export function placedIndices() {
  const s = new Set();
  for (const loop of Object.values(CONTOURS)) for (const i of loop) s.add(i);
  for (const i of [1, 168, 2, 133, 362, 33, 263, 159, 386, 105, 334, 13, 14, 0, 61, 291, 10, 152, 116, 345, 468, 473]) s.add(i);
  return s;
}

export default neutralFace;
