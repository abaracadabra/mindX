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
});

/**
 * Build clickable feature regions (centre + radius, in canvas space) from the
 * landmarks and the same fit transform the renderer uses.
 * @param {Array<{x,y}|null>} landmarks
 * @param {(p:{x,y})=>{x,y}} fit  landmark → canvas transform
 * @returns {Array<{name,control,cx,cy,r}>}
 */
export function featureRegions(landmarks, fit) {
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
