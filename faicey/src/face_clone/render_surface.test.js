/**
 * render_surface.test.js — the photoreal surface renderer's geometry + math.
 * The canvas draw is browser-only; everything provable headless is proven here.
 * Run: node src/face_clone/render_surface.test.js
 */
import { strict as assert } from 'assert';
import {
  triangulate, buildSurface, affineFromTriangle, shadeColor, paintOrder, SKIN,
} from './render_surface.js';
import { neutralFace } from './neutral_face.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

// Delaunay property: no point lies strictly inside any triangle's circumcircle.
function isDelaunay(pts, tris) {
  const cc = (A, B, C) => {
    const d = 2 * (A.x * (B.y - C.y) + B.x * (C.y - A.y) + C.x * (A.y - B.y));
    if (Math.abs(d) < 1e-12) return null;
    const a2 = A.x * A.x + A.y * A.y, b2 = B.x * B.x + B.y * B.y, c2 = C.x * C.x + C.y * C.y;
    const ux = (a2 * (B.y - C.y) + b2 * (C.y - A.y) + c2 * (A.y - B.y)) / d;
    const uy = (a2 * (C.x - B.x) + b2 * (A.x - C.x) + c2 * (B.x - A.x)) / d;
    return { x: ux, y: uy, r2: (A.x - ux) ** 2 + (A.y - uy) ** 2 };
  };
  for (const [i, j, k] of tris) {
    const c = cc(pts[i], pts[j], pts[k]); if (!c) continue;
    for (let m = 0; m < pts.length; m++) {
      if (m === i || m === j || m === k) continue;
      const dd = (pts[m].x - c.x) ** 2 + (pts[m].y - c.y) ** 2;
      if (dd < c.r2 - 1e-6) return false; // strictly inside → not Delaunay
    }
  }
  return true;
}

test('triangulate produces a valid Delaunay mesh with no degenerate triangles', () => {
  const pts = [
    { x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 },
    { x: 0.5, y: 0.5 }, { x: 0.2, y: 0.8 }, { x: 0.9, y: 0.3 },
  ];
  const tris = triangulate(pts);
  assert.ok(tris.length >= 5, 'a 7-point set triangulates into several triangles');
  assert.ok(isDelaunay(pts, tris), 'the empty-circumcircle property holds');
  for (const [i, j, k] of tris) {
    const area = Math.abs((pts[j].x - pts[i].x) * (pts[k].y - pts[i].y) - (pts[k].x - pts[i].x) * (pts[j].y - pts[i].y));
    assert.ok(area > 1e-9, 'no zero-area (degenerate) triangle');
  }
});

test('triangulate skips null/non-finite points and only references real ones', () => {
  const pts = [{ x: 0, y: 0 }, null, { x: 2, y: 0 }, { x: 1, y: 2 }, { x: NaN, y: 1 }, { x: 1, y: 0.5 }];
  const tris = triangulate(pts);
  const valid = new Set([0, 2, 3, 5]);
  assert.ok(tris.length > 0);
  for (const t of tris) for (const i of t) assert.ok(valid.has(i), `index ${i} is a real point`);
});

test('affineFromTriangle maps each source corner exactly onto its destination', () => {
  const src = [{ x: 10, y: 20 }, { x: 90, y: 15 }, { x: 40, y: 80 }];
  const dst = [{ x: 100, y: 100 }, { x: 260, y: 130 }, { x: 150, y: 300 }];
  const m = affineFromTriangle(src, dst);
  assert.ok(m, 'non-degenerate → a transform');
  for (let i = 0; i < 3; i++) {
    const x = m.a * src[i].x + m.c * src[i].y + m.e;
    const y = m.b * src[i].x + m.d * src[i].y + m.f;
    assert.ok(Math.abs(x - dst[i].x) < 1e-6 && Math.abs(y - dst[i].y) < 1e-6, `corner ${i} lands on target`);
  }
});

test('affineFromTriangle rejects a degenerate (colinear) source', () => {
  const m = affineFromTriangle(
    [{ x: 0, y: 0 }, { x: 1, y: 1 }, { x: 2, y: 2 }],
    [{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 0, y: 5 }],
  );
  assert.equal(m, null);
});

test('buildSurface shades the neutral face: unit normals, shades in [ambient,1]', () => {
  const face = neutralFace();
  const surf = buildSurface(face, { ambient: 0.3 });
  assert.ok(surf.triangles.length > 100, 'the 478-point face meshes into a full surface');
  for (const n of surf.normals) assert.ok(Math.abs(Math.hypot(n[0], n[1], n[2]) - 1) < 1e-6, 'normal is unit length');
  for (const s of surf.shades) assert.ok(s >= 0.3 - 1e-9 && s <= 1 + 1e-9, `shade ${s} within [ambient,1]`);
  assert.ok(surf.shades.some((s) => s > 0.3 + 1e-6), 'the 3D relief actually produces lit facets, not a flat fill');
});

test('topology reuse keeps the mesh stable while an expression deforms it', () => {
  const face = neutralFace();
  const base = buildSurface(face);
  // a crude "expression": drop the jaw region by shifting lower-face vertices down
  const expressed = face.map((p, i) => (p && i > 150 ? { x: p.x, y: p.y + 0.03, z: p.z } : p));
  const same = buildSurface(expressed, { topology: base.triangles });
  assert.deepEqual(same.triangles, base.triangles, 'SAME triangle topology — indices do not flicker');
  assert.ok(same.shades.some((s, i) => Math.abs(s - base.shades[i]) > 1e-6), 'yet the shading changed — the surface moved');
});

test('shadeColor darkens toward black and never exceeds the skin base', () => {
  const lit = shadeColor(1), dark = shadeColor(0), mid = shadeColor(0.5);
  assert.deepEqual(lit, { r: SKIN.r, g: SKIN.g, b: SKIN.b }, 'full light = the skin base');
  assert.deepEqual(dark, { r: 0, g: 0, b: 0 }, 'no light = black');
  assert.ok(mid.r < SKIN.r && mid.r > 0, 'mid shade sits between');
  assert.deepEqual(shadeColor(2), shadeColor(1), 'clamped above 1');
});

test('paintOrder sorts triangles back-to-front by depth', () => {
  const order = paintOrder([0.5, -0.2, 0.9, 0.1]);
  assert.deepEqual(order, [1, 3, 0, 2], 'smallest z (furthest) painted first');
});

console.log(`\nrender_surface: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
