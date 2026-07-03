/**
 * contours.js — MediaPipe face-mesh contour loops + a wireframe renderer.
 *
 * The well-known canonical-face-model index loops (face oval, eyes, brows, lips, nose). Drawing
 * polylines through a person's landmark positions yields a recognisable wireframe OF THAT PERSON —
 * i.e. the cloned face. Pure 2D canvas; auto-fits any landmark coordinate range (raw image space
 * or pose-normalised). Shared by the clone studio and the showcase renderer (no duplication).
 */

export const CONTOURS = {
  faceOval: [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109],
  rightEye: [33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246],
  leftEye: [362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398],
  rightBrow: [70,63,105,66,107,55,65,52,53,46],
  leftBrow: [300,293,334,296,336,285,295,282,283,276],
  lipsOuter: [61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185],
  noseBridge: [168,6,197,195,5,4,1],
  noseBottom: [98,97,2,326,327],
};
const CLOSED = new Set(['faceOval', 'rightEye', 'leftEye', 'lipsOuter']);

/** Compute a fit transform mapping the landmarks' bbox into a padded canvas box. */
function fit(landmarks, W, H, pad = 0.12) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of landmarks) {
    if (!p) continue;
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  const bw = (maxX - minX) || 1, bh = (maxY - minY) || 1;
  const s = Math.min((W * (1 - 2 * pad)) / bw, (H * (1 - 2 * pad)) / bh);
  const ox = (W - bw * s) / 2 - minX * s, oy = (H - bh * s) / 2 - minY * s;
  return (p) => ({ x: p.x * s + ox, y: p.y * s + oy });
}

/**
 * Draw the cloned face wireframe from landmarks.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array<{x:number,y:number,z:number}>} landmarks
 * @param {{ W:number, H:number, hue?:number, points?:boolean }} opts
 */
export function drawFaceWireframe(ctx, landmarks, opts) {
  const { W, H, hue = 150, points = false } = opts;
  const T = fit(landmarks, W, H);
  const stroke = `hsl(${hue},90%,55%)`, dim = `hsl(${hue},70%,40%)`;
  ctx.lineWidth = 1.6; ctx.lineJoin = 'round';

  for (const [name, idx] of Object.entries(CONTOURS)) {
    ctx.strokeStyle = name === 'faceOval' ? dim : stroke;
    ctx.beginPath();
    let started = false;
    for (const i of idx) {
      const lm = landmarks[i]; if (!lm) continue;
      const p = T(lm);
      started ? ctx.lineTo(p.x, p.y) : (ctx.moveTo(p.x, p.y), started = true);
    }
    if (CLOSED.has(name)) ctx.closePath();
    ctx.stroke();
  }
  // iris / eye centres as accents (478-landmark models carry iris points 468..477)
  ctx.fillStyle = `hsl(${hue},90%,65%)`;
  for (const i of [468, 473]) { const lm = landmarks[i]; if (lm) { const p = T(lm); ctx.beginPath(); ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2); ctx.fill(); } }
  if (points) {
    ctx.fillStyle = `hsla(${hue},80%,60%,.25)`;
    for (const lm of landmarks) { if (!lm) continue; const p = T(lm); ctx.fillRect(p.x, p.y, 1, 1); }
  }
}

// ── face render THEMES — the simple wireframe is the default; the rest are alternate styles ──
export const FACE_THEMES = ['wireframe', 'neon', 'dots', 'mesh', 'filled', 'scan'];

/** Dispatch to a themed renderer. `wireframe` is the original simple face, unchanged. */
export function drawFaceTheme(ctx, landmarks, opts) {
  const { W, H, hue = 150, theme = 'wireframe' } = opts;
  ctx.save();
  if (theme === 'neon') {
    ctx.shadowColor = `hsl(${hue},90%,55%)`; ctx.shadowBlur = 12; ctx.lineWidth = 2;
    drawFaceWireframe(ctx, landmarks, { W, H, hue });
    ctx.restore(); return;
  }
  if (theme === 'wireframe') { drawFaceWireframe(ctx, landmarks, { W, H, hue }); ctx.restore(); return; }

  const T = fit(landmarks, W, H);
  const accent = `hsl(${hue},90%,55%)`, dim = `hsl(${hue},70%,42%)`;
  const path = (idx, close) => { ctx.beginPath(); let started = false;
    for (const i of idx) { const lm = landmarks[i]; if (!lm) continue; const p = T(lm); started ? ctx.lineTo(p.x, p.y) : (ctx.moveTo(p.x, p.y), started = true); }
    if (close) ctx.closePath(); };

  if (theme === 'dots') {
    ctx.fillStyle = accent;
    for (const lm of landmarks) { if (!lm) continue; const p = T(lm); ctx.beginPath(); ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2); ctx.fill(); }
  } else if (theme === 'mesh') {
    ctx.fillStyle = `hsla(${hue},80%,60%,.55)`;
    for (const lm of landmarks) { if (!lm) continue; const p = T(lm); ctx.fillRect(p.x - 0.6, p.y - 0.6, 1.4, 1.4); }
    ctx.strokeStyle = `hsla(${hue},70%,45%,.5)`; ctx.lineWidth = 1;
    for (const [n, idx] of Object.entries(CONTOURS)) { path(idx, CLOSED.has(n)); ctx.stroke(); }
  } else if (theme === 'filled') {
    ctx.fillStyle = `hsla(${hue},70%,16%,1)`; path(CONTOURS.faceOval, true); ctx.fill();
    ctx.fillStyle = `hsla(${hue},90%,55%,.85)`;
    for (const n of ['lipsOuter', 'rightEye', 'leftEye']) { path(CONTOURS[n], true); ctx.fill(); }
    ctx.strokeStyle = dim; ctx.lineWidth = 1.4;
    for (const [n, idx] of Object.entries(CONTOURS)) { path(idx, CLOSED.has(n)); ctx.stroke(); }
  } else if (theme === 'scan') {
    // bbox phosphor scanlines behind the wireframe
    let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
    for (const lm of landmarks) { if (!lm) continue; const p = T(lm); minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
    ctx.strokeStyle = `hsla(${hue},90%,55%,.18)`; ctx.lineWidth = 1;
    for (let y = minY; y < maxY; y += 6) { ctx.beginPath(); ctx.moveTo(minX, y); ctx.lineTo(maxX, y); ctx.stroke(); }
    drawFaceWireframe(ctx, landmarks, { W, H, hue });
  }
  ctx.restore();
}
