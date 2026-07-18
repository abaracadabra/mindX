/**
 * face_controls.js — the face IS the control surface.
 *
 * Each sense organ drives the hardware it represents:
 *   • the EYE is a camera   → clicking an eye toggles the webcam
 *   • the EAR hears          → clicking an ear controls microphone input
 *   • the MOUTH speaks       → clicking the mouth controls output audio
 *
 * Given the rendered face's landmarks and its fit transform, this maps a click
 * on the canvas to the control the feature under it represents. Pure geometry
 * (feature discs in canvas space + nearest-hit), headless-tested; the wiring to
 * the actual camera/mic/speaker lives in the demo.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { CONTOURS } from './contours.js';

/** Which control each facial feature drives. */
export const CONTROL_MAP = Object.freeze({
  rightEye: 'camera', leftEye: 'camera',
  rightEar: 'mic', leftEar: 'mic',
  lipsOuter: 'output',
  noseBridge: 'network', noseBottom: 'network', // the nose = networking diagnostics
  noseRightAla: 'blockchain',                    // right nostril = blockchain scan
  noseLeftAla: 'rage',                           // left nostril  = RAGE search
});

/** Point-based controls (not a contour loop) — a landmark + a control. */
export const POINT_CONTROLS = Object.freeze({
  thirdEye: { index: 168, control: 'matrix' },   // glabella — the deep diagnostic matrix (easter egg)
  leftBrain: { index: 103, control: 'analytical' }, // left forehead — analytical reasoning + math
  rightBrain: { index: 332, control: 'creative' },  // right forehead — creativity + expression
});

/**
 * Build clickable feature regions (centre + radius, in canvas space) from the
 * landmarks and the same fit transform the renderer uses.
 * @param {Array<{x,y}|null>} landmarks
 * @param {(p:{x,y})=>{x,y}} fit  landmark → canvas transform
 * @param {{points?:string[]}} [opts]  point controls to include (e.g. the third
 *   eye) — omitted by default because the third eye "is not always there".
 * @returns {Array<{name,control,cx,cy,r}>}
 */
export function featureRegions(landmarks, fit, opts = {}) {
  const out = [];
  for (const [name, control] of Object.entries(CONTROL_MAP)) {
    const idx = CONTOURS[name]; if (!idx) continue;
    let sx = 0, sy = 0, n = 0, minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const i of idx) {
      const lm = landmarks[i]; if (!lm) continue;
      const p = fit(lm); sx += p.x; sy += p.y; n++;
      if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
    }
    if (!n) continue;
    const cx = sx / n, cy = sy / n;
    // radius from the feature's extent, with a small minimum so tiny features stay clickable
    const r = Math.max(10, 0.6 * Math.max(maxX - minX, maxY - minY));
    out.push({ name, control, cx, cy, r });
  }
  // point controls (the third eye) — only when the caller says it's visible
  for (const name of (opts.points || [])) {
    const pc = POINT_CONTROLS[name]; if (!pc) continue;
    const lm = landmarks[pc.index]; if (!lm) continue;
    const p = fit(lm);
    out.push({ name, control: pc.control, cx: p.x, cy: p.y, r: 12 });
  }
  return out;
}

/**
 * The control whose feature a click lands on — nearest disc that contains the
 * point, or null. Returns { name, control, cx, cy, r, dist }.
 */
export function featureAtPoint(regions, x, y) {
  let best = null;
  for (const reg of regions) {
    const d = Math.hypot(x - reg.cx, y - reg.cy);
    if (d <= reg.r && (!best || d < best.dist)) best = { ...reg, dist: d };
  }
  return best;
}

export default featureAtPoint;
