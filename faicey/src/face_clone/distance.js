/**
 * distance.js — a monocular distance finder for the webcam.
 *
 * The eye is a camera, so the camera can range-find: a pinhole model turns the
 * measured inter-pupillary distance (IPD) in pixels into a distance to the
 * subject. Adult IPD is a tight biometric constant (~63 mm), which makes it a
 * reliable ruler — the same trick face-tracking AR uses.
 *
 *   image size s(px) = f · S / D   ⇒   D = f · S / s
 *   S = real IPD (mm), f = focal length (px), s = IPD (px)
 *
 * Pure geometry, headless-tested. Returns null when the iris landmarks needed to
 * measure IPD aren't present — it never guesses a distance.
 *
 * © Professor Codephreak - rage.pythai.net
 */

export const ADULT_IPD_MM = 63;      // mean adult inter-pupillary distance
export const DEFAULT_FOV_DEG = 60;   // typical webcam horizontal field of view

// MediaPipe iris centres (478-landmark model): 468 = right iris, 473 = left iris.
export const IRIS_RIGHT = 468, IRIS_LEFT = 473;

/** Focal length in pixels from the frame width and horizontal FOV. */
export function focalFromFov(frameWidthPx, fovDeg = DEFAULT_FOV_DEG) {
  return (frameWidthPx / 2) / Math.tan((fovDeg * Math.PI / 180) / 2);
}

/** Inter-pupillary distance in pixels from the iris landmarks; null if absent. */
export function ipdPixels(landmarks, frameWidthPx, frameHeightPx) {
  const a = landmarks[IRIS_RIGHT], b = landmarks[IRIS_LEFT];
  if (!a || !b) return null;
  return Math.hypot((a.x - b.x) * frameWidthPx, (a.y - b.y) * frameHeightPx);
}

/** Distance to the subject in millimetres from a measured IPD in pixels. */
export function estimateDistanceMm(ipdPx, opts = {}) {
  if (!(ipdPx > 0)) return null;
  const ipdMm = opts.ipdMm ?? ADULT_IPD_MM;
  const focalPx = opts.focalPx ?? focalFromFov(opts.frameWidthPx ?? 640, opts.fovDeg ?? DEFAULT_FOV_DEG);
  return focalPx * ipdMm / ipdPx;
}
export const estimateDistanceCm = (ipdPx, opts) => { const mm = estimateDistanceMm(ipdPx, opts); return mm == null ? null : mm / 10; };

/**
 * Full range-find from landmarks + frame size → { cm, mm, ipdPx, focalPx } or
 * null when the iris landmarks are missing.
 */
export function rangeFind(landmarks, frameWidthPx, frameHeightPx, opts = {}) {
  const ipdPx = ipdPixels(landmarks, frameWidthPx, frameHeightPx);
  if (ipdPx == null || !(ipdPx > 0)) return null;
  const focalPx = opts.focalPx ?? focalFromFov(frameWidthPx, opts.fovDeg ?? DEFAULT_FOV_DEG);
  const mm = estimateDistanceMm(ipdPx, { ...opts, focalPx });
  return { cm: mm / 10, mm, ipdPx, focalPx };
}

export default rangeFind;
