/**
 * render_surface.js — lift the FACE from a wireframe to a rendered SURFACE.
 *
 * Two honest render modes, both built on one mesh:
 *   • surface   — the mesh shaded as a solid (Lambert on the real 3D normals);
 *                 a rendered face, still synthetic geometry.
 *   • photoreal — the person's own captured frame, affine-mapped per triangle
 *                 onto the measured mesh. Real texture on real geometry, so it
 *                 is genuine PHOTOGRAPHIC realism OF THE CAPTURE — and because
 *                 the UVs are tied to landmark indices, it re-warps as the mesh
 *                 deforms, so the cloned face emotes photoreally.
 *
 * What this is NOT: neural view-synthesis. It cannot invent occluded or novel
 * views, and it does not claim "hyperrealism indistinguishable from reality" —
 * that tier needs a neural renderer (a labeled future), not affine warping.
 *
 * Pure JS, no dependencies, browser + Node. The canvas drawing lives in
 * contours.js (drawFaceSurface); this module is the geometry + the math, so it
 * is fully testable headless.
 *
 * © Professor Codephreak - rage.pythai.net
 */

/** Default skin base (a mid warm tone); shading modulates it. */
export const SKIN = { r: 214, g: 168, b: 142 };

/** Light from upper-front-right in image space (x→right, y→down, z→viewer). */
export const DEFAULT_LIGHT = normalize3([-0.3, -0.55, 0.78]);

function normalize3(v) {
  const m = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / m, v[1] / m, v[2] / m];
}

function circumcircle(ax, ay, bx, by, cx, cy) {
  const d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
  if (Math.abs(d) < 1e-12) return null; // colinear
  const a2 = ax * ax + ay * ay, b2 = bx * bx + by * by, c2 = cx * cx + cy * cy;
  const ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d;
  const uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d;
  return { x: ux, y: uy, r2: (ax - ux) ** 2 + (ay - uy) ** 2 };
}

/**
 * Bowyer–Watson Delaunay triangulation of 2D points.
 * @param {Array<{x:number,y:number}|null>} pts
 * @returns {Array<[number,number,number]>} index triangles into `pts`
 *   (null points are skipped; the returned indices always reference real points)
 */
export function triangulate(pts) {
  const idx = [];
  const P = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) { idx.push(i); P.push({ x: p.x, y: p.y }); }
  }
  const n = P.length;
  if (n < 3) return [];

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of P) { minX = Math.min(minX, p.x); minY = Math.min(minY, p.y); maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y); }
  const dmax = Math.max(maxX - minX, maxY - minY) || 1, midx = (minX + maxX) / 2, midy = (minY + maxY) / 2;

  // super-triangle (indices n, n+1, n+2 into a working copy)
  const W = P.concat([
    { x: midx - 20 * dmax, y: midy - dmax },
    { x: midx, y: midy + 20 * dmax },
    { x: midx + 20 * dmax, y: midy - dmax },
  ]);
  let tris = [[n, n + 1, n + 2]];

  for (let ip = 0; ip < n; ip++) {
    const p = W[ip];
    const good = [], edges = new Map();
    for (const t of tris) {
      const cc = circumcircle(W[t[0]].x, W[t[0]].y, W[t[1]].x, W[t[1]].y, W[t[2]].x, W[t[2]].y);
      const inside = cc && ((p.x - cc.x) ** 2 + (p.y - cc.y) ** 2) <= cc.r2 + 1e-9;
      if (!inside) { good.push(t); continue; }
      // triangle is "bad" — record its edges (shared edges cancel)
      for (const [a, b] of [[t[0], t[1]], [t[1], t[2]], [t[2], t[0]]]) {
        const key = a < b ? `${a}_${b}` : `${b}_${a}`;
        const e = edges.get(key);
        if (e) e.count++; else edges.set(key, { a, b, count: 1 });
      }
    }
    tris = good;
    for (const e of edges.values()) if (e.count === 1) tris.push([e.a, e.b, ip]);
  }

  // drop triangles touching the super-triangle, map back to original indices
  return tris.filter((t) => t.every((i) => i < n)).map((t) => [idx[t[0]], idx[t[1]], idx[t[2]]]);
}

/** Unit 3D normal of a triangle, oriented toward the viewer (+z). */
function triNormal(a, b, c) {
  const ux = b.x - a.x, uy = b.y - a.y, uz = (b.z || 0) - (a.z || 0);
  const vx = c.x - a.x, vy = c.y - a.y, vz = (c.z || 0) - (a.z || 0);
  let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  const m = Math.hypot(nx, ny, nz) || 1;
  nx /= m; ny /= m; nz /= m;
  if (nz < 0) { nx = -nx; ny = -ny; nz = -nz; } // face the camera
  return [nx, ny, nz];
}

/**
 * Build the shaded surface mesh for a set of 3D landmarks.
 * @param {Array<{x,y,z?}|null>} landmarks
 * @param {{topology?:Array<[number,number,number]>, light?:number[], ambient?:number}} [opts]
 *   topology — reuse a precomputed triangle index list (keeps the mesh stable
 *   across expressions; the SAME triangles, only their vertices move).
 * @returns {{triangles:Array<[number,number,number]>, normals:number[][],
 *            shades:number[], depths:number[]}}
 *   shades ∈ [ambient, 1]; depths = mean z (for painter's-order back-to-front).
 */
export function buildSurface(landmarks, opts = {}) {
  const light = opts.light || DEFAULT_LIGHT;
  const ambient = opts.ambient ?? 0.32;
  const triangles = opts.topology || triangulate(landmarks);
  const normals = [], shades = [], depths = [];
  for (const [i, j, k] of triangles) {
    const a = landmarks[i], b = landmarks[j], c = landmarks[k];
    if (!a || !b || !c) { normals.push([0, 0, 1]); shades.push(ambient); depths.push(0); continue; }
    const nrm = triNormal(a, b, c);
    const diff = Math.max(0, nrm[0] * light[0] + nrm[1] * light[1] + nrm[2] * light[2]);
    normals.push(nrm);
    shades.push(Math.min(1, ambient + (1 - ambient) * diff));
    depths.push(((a.z || 0) + (b.z || 0) + (c.z || 0)) / 3);
  }
  return { triangles, normals, shades, depths };
}

/** Painter's order: indices of `triangles` sorted back (small +z away) to front. */
export function paintOrder(depths) {
  return depths.map((d, i) => i).sort((p, q) => depths[p] - depths[q]);
}

/** SKIN modulated by a shade intensity → an {r,g,b} of 0..255 ints. */
export function shadeColor(intensity, skin = SKIN) {
  const s = Math.max(0, Math.min(1, intensity));
  return { r: Math.round(skin.r * s), g: Math.round(skin.g * s), b: Math.round(skin.b * s) };
}

/**
 * Affine transform mapping a source triangle → a destination triangle, as the
 * six values canvas `setTransform(a,b,c,d,e,f)` takes
 * (x' = a·x + c·y + e ; y' = b·x + d·y + f). This is exact per-triangle texture
 * mapping — solved, not approximated. Returns null for a degenerate source.
 * @param {[{x,y},{x,y},{x,y}]} src  source (texture-pixel) triangle
 * @param {[{x,y},{x,y},{x,y}]} dst  destination (canvas) triangle
 */
export function affineFromTriangle(src, dst) {
  const M = src.map((p) => [p.x, p.y, 1]);
  const ace = solve3(M, dst.map((p) => p.x)); // a,c,e
  const bdf = solve3(M, dst.map((p) => p.y)); // b,d,f
  if (!ace || !bdf) return null;
  return { a: ace[0], b: bdf[0], c: ace[1], d: bdf[1], e: ace[2], f: bdf[2] };
}

function det3(m) {
  return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
       - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
       + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
}
function solve3(M, r) { // Cramer's rule for M·x = r (3×3)
  const D = det3(M);
  if (Math.abs(D) < 1e-12) return null;
  const col = (c) => M.map((row, i) => row.map((v, j) => (j === c ? r[i] : v)));
  return [det3(col(0)) / D, det3(col(1)) / D, det3(col(2)) / D];
}

export default buildSurface;
