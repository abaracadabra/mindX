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
  irisR: 0.024,                            // iris radius
  browY: 0.38, browDX: 0.13, browRx: 0.085, browArch: 0.03,
  noseTopY: 0.40, noseTipY: 0.545, noseW: 0.045, alaR: 0.03,
  mouthY: 0.66, mouthRx: 0.10, mouthRy: 0.035, lipInR: 0.075, lipInRy: 0.012,
  earY: 0.50, earH: 0.11,                  // ears at eye/nose height, on the oval edge
};

// Ear helix indices live above the MediaPipe range (0..477): a synthetic face
// carries them, a cloned MediaPipe face does not — so ears draw on the neutral
// face and are silently absent (renderer skips nulls) on a real clone.
const EAR_R = [478, 479, 480, 481, 482, 483];
const EAR_L = [484, 485, 486, 487, 488, 489];

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

/** Almond eye: pinched at the corners, with a taller UPPER lid than lower —
 *  the asymmetry is what separates an open eye from a lens shape. */
function almond(cx, cy, rx, ry, n, z) {
  return ring(cx, cy, rx, ry, n, Math.PI, z, (x, y, a) => {
    const pinch = 0.30 + 0.70 * Math.abs(Math.sin(a));  // corners pinch shut
    const upper = Math.sin(a) < 0;                       // +y is down → upper lid
    const lid = upper ? 1.18 : 0.72;                     // upper lid arches, lower flattens
    return { x, y: cy + (y - cy) * pinch * lid };
  });
}

/** Iris ring — a small circle around the eye centre (MediaPipe 469-472/474-477). */
function irisRing(cx, cy, r, n, z) {
  return ring(cx, cy, r, r, n, -Math.PI / 2, z);
}

/** Brow: a natural arch that peaks over the inner third and tapers down the
 *  outer tail — `innerFirst` flips for whichever end the index loop starts at. */
function brow(cx, cy, rx, arch, n, z, innerFirst) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    let t = i / (n - 1);              // 0 → end A, 1 → end B along the brow
    const inner = innerFirst ? 1 - t : t; // 0 at outer tail, 1 at inner head
    const x = cx - rx + t * 2 * rx;
    const peak = Math.sin(Math.pow(inner, 0.8) * Math.PI * 0.5 + Math.PI * 0.15);
    const y = cy - peak * arch + (1 - inner) * arch * 0.45; // outer tail drops
    pts.push({ x, y, z });
  }
  return pts;
}

/** Alar wing — the nostril curve flaring from the nose tip up to one ala. */
function alarWing(alaX, tipY, r, n, side) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);                    // tip → ala
    const a = Math.PI * (1 + t * 0.9);        // sweep up and out
    pts.push({ x: alaX + side * (1 - Math.cos(a)) * r * 0.5, y: tipY + 0.014 + Math.sin(a) * r, z: 0.05 });
  }
  return pts;
}

/** Ear helix — an open C on the side of the face, tip up. */
function earHelix(cx, cy, h, n, side, z) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);                 // top → bottom of the ear
    const a = Math.PI * (0.35 + t * 1.15); // sweep the helix arc
    const x = cx + side * Math.sin(a) * h * 0.5;
    const y = cy - h * 0.5 + t * h;
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
  const out = new Array(490).fill(null); // 0..477 MediaPipe + 478..489 synthetic ears

  // — face oval — the ordered loop runs clockwise from the forehead (index 10) —
  assign(out, CONTOURS.faceOval,
    ring(F.cx, F.cy, F.rx, F.ry, CONTOURS.faceOval.length, -Math.PI / 2, -0.04));

  // — eyes — right eye is the viewer-left almond (MediaPipe "right" = subject's) —
  const rEyeCx = F.cx - F.eyeDX, lEyeCx = F.cx + F.eyeDX;
  assign(out, CONTOURS.rightEye, almond(rEyeCx, F.eyeY, F.eyeRx, F.eyeRy, CONTOURS.rightEye.length, 0.01));
  assign(out, CONTOURS.leftEye, almond(lEyeCx, F.eyeY, F.eyeRx, F.eyeRy, CONTOURS.leftEye.length, 0.01));
  // — iris rings (a visible iris circle, not just a centre dot) —
  assign(out, CONTOURS.rightIris, irisRing(rEyeCx, F.eyeY, F.irisR, CONTOURS.rightIris.length, 0.02));
  assign(out, CONTOURS.leftIris, irisRing(lEyeCx, F.eyeY, F.irisR, CONTOURS.leftIris.length, 0.02));

  // — brows — angled arches, peaked inner, tapering down the outer tail —
  assign(out, CONTOURS.rightBrow, brow(rEyeCx, F.browY, F.browRx, F.browArch, CONTOURS.rightBrow.length, 0.0, false));
  assign(out, CONTOURS.leftBrow, brow(lEyeCx, F.browY, F.browRx, F.browArch, CONTOURS.leftBrow.length, 0.0, true));

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
  // — alar wings — the nostril curves flaring up from the tip to each ala —
  assign(out, CONTOURS.noseRightAla, alarWing(F.cx - F.noseW, F.noseTipY, F.alaR, CONTOURS.noseRightAla.length, -1));
  assign(out, CONTOURS.noseLeftAla, alarWing(F.cx + F.noseW, F.noseTipY, F.alaR, CONTOURS.noseLeftAla.length, 1));

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
  // — inner lip line — the mouth opening, so the lips read as two lips —
  assign(out, CONTOURS.lipsInner,
    ring(F.cx, F.mouthY, F.lipInR, F.lipInRy, CONTOURS.lipsInner.length, Math.PI, 0.025));

  // — ears — a helix on each side at eye/nose height, on the face-oval edge —
  assign(out, EAR_R, earHelix(F.cx - F.rx * 0.98, F.earY, F.earH, EAR_R.length, -1, -0.06));
  assign(out, EAR_L, earHelix(F.cx + F.rx * 0.98, F.earY, F.earH, EAR_L.length, 1, -0.06));

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
