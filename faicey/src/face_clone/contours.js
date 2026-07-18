/**
 * contours.js — MediaPipe face-mesh contour loops + a wireframe renderer.
 *
 * The well-known canonical-face-model index loops (face oval, eyes, brows, lips, nose). Drawing
 * polylines through a person's landmark positions yields a recognisable wireframe OF THAT PERSON —
 * i.e. the cloned face. Pure 2D canvas; auto-fits any landmark coordinate range (raw image space
 * or pose-normalised). Shared by the clone studio and the showcase renderer (no duplication).
 */

import { buildSurface, affineFromTriangle, shadeColor, paintOrder, SKIN, DEFAULT_LIGHT } from './render_surface.js';

export const CONTOURS = {
  faceOval: [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109],
  rightEye: [33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246],
  leftEye: [362,382,381,380,374,373,390,249,263,466,388,387,386,385,384,398],
  rightBrow: [70,63,105,66,107,55,65,52,53,46],
  leftBrow: [300,293,334,296,336,285,295,282,283,276],
  lipsOuter: [61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185],
  lipsInner: [78,95,88,178,87,14,317,402,318,324,308,415,310,311,312,13,82,81,80,191],
  noseBridge: [168,6,197,195,5,4,1],
  noseBottom: [98,97,2,326,327],
  noseRightAla: [98,64,240,75,60],   // right nostril wing (tip → ala)
  noseLeftAla: [327,294,460,305,290], // left nostril wing
  rightIris: [469,470,471,472],       // right iris ring (478-landmark models)
  leftIris: [474,475,476,477],        // left iris ring
  // synthetic ears — indices above the MediaPipe range; present only on the
  // procedural neutral face (a real MediaPipe clone has no ear mesh, so these
  // are absent and the renderer skips them).
  rightEar: [478,479,480,481,482,483],
  leftEar: [484,485,486,487,488,489],
};
const CLOSED = new Set(['faceOval', 'rightEye', 'leftEye', 'lipsOuter', 'lipsInner', 'rightIris', 'leftIris']);

/** Compute a fit transform mapping the landmarks' bbox into a padded canvas box. */
export function computeFit(landmarks, W, H, pad = 0.12) { return fit(landmarks, W, H, pad); }
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
/**
 * drawMouthScope — the live voice waveform, drawn INSIDE the lips.
 *
 * The mouth becomes a little oscilloscope: the waveform is clipped to the outer
 * lip contour and scaled to the mouth's height, so the voice literally shows
 * between the lips. Uses the SAME fit() transform as the face, so it lands
 * exactly on the rendered mouth however the face is framed.
 *
 * @param {Array} landmarks   the same landmarks passed to drawFaceTheme
 * @param {Float32Array} wave live time-domain samples (−1..1)
 * @param {{W,H,hue,gain?}} opts
 */
export function drawMouthScope(ctx, landmarks, wave, opts) {
  const { W, H, hue = 150, gain = 1.4, speaking = false } = opts;
  const loop = CONTOURS.lipsOuter.map((i) => landmarks[i]).filter(Boolean);
  if (loop.length < 4 || !wave || !wave.length) return;
  const T = fit(landmarks, W, H);
  const pts = loop.map(T);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of pts) { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  const midY = (minY + maxY) / 2, half = (maxY - minY) / 2, w = maxX - minX;
  if (w < 2) return;
  const yAt = (x) => { const v = wave[Math.floor((x / w) * (wave.length - 1))] || 0; return midY - Math.max(-1, Math.min(1, v * gain)) * half * 0.92; };
  ctx.save();
  // clip to the lip polygon so the scope is CONTAINED by the lips
  ctx.beginPath();
  pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  ctx.closePath();
  ctx.clip();
  // baseline
  ctx.strokeStyle = `hsla(${hue},80%,50%,.28)`; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(minX, midY); ctx.lineTo(maxX, midY); ctx.stroke();
  // filled waveform area (down to the baseline) — reads as a real scope when speaking
  ctx.beginPath(); ctx.moveTo(minX, midY);
  for (let x = 0; x <= w; x++) ctx.lineTo(minX + x, yAt(x));
  ctx.lineTo(maxX, midY); ctx.closePath();
  ctx.fillStyle = `hsla(${hue},95%,60%,${speaking ? 0.3 : 0.16})`; ctx.fill();
  // the trace — brighter, thicker, and glowing while the avatar speaks
  if (speaking) { ctx.shadowColor = `hsl(${hue},95%,66%)`; ctx.shadowBlur = 7; }
  ctx.strokeStyle = `hsl(${hue},95%,${speaking ? 72 : 62}%)`; ctx.lineWidth = speaking ? 1.9 : 1.3; ctx.lineJoin = 'round';
  ctx.beginPath();
  for (let x = 0; x <= w; x++) { const px = minX + x, py = yAt(x); x ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
  ctx.stroke();
  ctx.restore();
}

/**
 * drawFaceSurface — the photoreal renderer. Meshes the landmarks into shaded
 * triangles and either (a) fills each with lit skin ('surface'), or (b) affine-
 * maps the person's captured frame per triangle onto the mesh ('photoreal').
 *
 * In photoreal mode the texture is tied to landmark indices, so as the mesh
 * deforms (an expression, or the cloned voice driving the mouth) the texture
 * re-warps with it — the captured face emotes photoreally. This is real texture
 * on real geometry; it is NOT neural view-synthesis and makes no claim to
 * invent occluded views.
 *
 * @param {Array<{x,y,z?}|null>} landmarks  destination geometry (current pose)
 * @param {{W,H,hue?,light?,skin?,topology?,
 *          texture?:CanvasImageSource, texLandmarks?:Array<{x,y}|null>,
 *          mode?:'surface'|'photoreal'}} opts
 *   texture      — the captured frame (video/canvas/image) for photoreal
 *   texLandmarks — the SAME landmarks in the texture's pixel space (source UVs)
 */
export function drawFaceSurface(ctx, landmarks, opts) {
  const { W, H, hue = 150, light = DEFAULT_LIGHT, skin = SKIN, topology, texture, texLandmarks } = opts;
  const mode = opts.mode || (texture && texLandmarks ? 'photoreal' : 'surface');
  const T = fit(landmarks, W, H);
  const dst = landmarks.map((lm) => (lm ? T(lm) : null));
  const surf = buildSurface(landmarks, { topology, light });
  const order = paintOrder(surf.depths); // back-to-front (painter's algorithm)

  // grow a triangle slightly around its centroid — overlapping triangles hide seams
  const dilate = (a, b, c, k = 1.03) => {
    const cx = (a.x + b.x + c.x) / 3, cy = (a.y + b.y + c.y) / 3;
    const g = (p) => ({ x: cx + (p.x - cx) * k, y: cy + (p.y - cy) * k });
    return [g(a), g(b), g(c)];
  };

  ctx.save();
  const photoreal = mode === 'photoreal' && texture && texLandmarks;
  for (const t of order) {
    const [i, j, k] = surf.triangles[t];
    const a = dst[i], b = dst[j], c = dst[k];
    if (!a || !b || !c) continue;
    const [A, B, C] = dilate(a, b, c);

    if (photoreal) {
      const s0 = texLandmarks[i], s1 = texLandmarks[j], s2 = texLandmarks[k];
      if (!s0 || !s1 || !s2) continue;
      const m = affineFromTriangle([s0, s1, s2], [A, B, C]);
      if (!m) continue;
      ctx.save();
      ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.lineTo(C.x, C.y); ctx.closePath(); ctx.clip();
      ctx.setTransform(m.a, m.b, m.c, m.d, m.e, m.f);
      ctx.drawImage(texture, 0, 0);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      // multiply the lit shade over the texture for relief (subtle)
      const sh = surf.shades[t];
      if (sh < 0.98) { ctx.fillStyle = `rgba(0,0,0,${(1 - sh) * 0.5})`; ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.lineTo(C.x, C.y); ctx.closePath(); ctx.fill(); }
      ctx.restore();
    } else {
      const rgb = shadeColor(surf.shades[t], skin);
      ctx.fillStyle = `rgb(${rgb.r},${rgb.g},${rgb.b})`;
      ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.lineTo(C.x, C.y); ctx.closePath(); ctx.fill();
    }
  }
  // a whisper of feature definition so eyes/lips read on the shaded surface
  if (!photoreal) {
    ctx.strokeStyle = `hsla(${hue},40%,20%,.55)`; ctx.lineWidth = 1;
    for (const n of ['rightEye', 'leftEye', 'lipsOuter', 'lipsInner', 'rightBrow', 'leftBrow']) {
      ctx.beginPath(); let started = false;
      for (const i of CONTOURS[n]) { const lm = landmarks[i]; if (!lm) continue; const p = T(lm); started ? ctx.lineTo(p.x, p.y) : (ctx.moveTo(p.x, p.y), started = true); }
      if (CLOSED.has(n)) ctx.closePath();
      ctx.stroke();
    }
  }
  ctx.restore();
}

export const FACE_THEMES = ['wireframe', 'neon', 'dots', 'mesh', 'filled', 'scan', 'surface', 'photoreal'];

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
  if (theme === 'surface' || theme === 'photoreal') {
    drawFaceSurface(ctx, landmarks, { ...opts, mode: theme === 'photoreal' ? 'photoreal' : 'surface' });
    ctx.restore(); return;
  }

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
