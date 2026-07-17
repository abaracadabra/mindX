/**
 * webgl_face.test.js — the WebGL renderer's geometry + matrix math.
 * The GL draw is browser-only; the buffers it uploads and the transforms it
 * applies are proven headless here.
 * Run: node src/face_clone/webgl_face.test.js
 */
import { strict as assert } from 'assert';
import {
  buildFaceGeometry, computeSmoothNormals,
  m4identity, m4perspective, m4rotationY, m4translation, m4multiply,
} from './webgl_face.js';
import { neutralFace } from './neutral_face.js';
import { triangulate } from './render_surface.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

const face = neutralFace();
const topo = triangulate(face);

test('buildFaceGeometry produces the four buffers at the right sizes', () => {
  const g = buildFaceGeometry(face, { topology: topo });
  assert.equal(g.positions.length, face.length * 3);
  assert.equal(g.normals.length, face.length * 3);
  assert.equal(g.uvs.length, face.length * 2);
  assert.equal(g.indices.length, topo.length * 3);
  assert.equal(g.count, topo.length);
});

test('positions are centred on the origin and Y is flipped (image-down → GL-up)', () => {
  const g = buildFaceGeometry(face, { topology: topo });
  let sx = 0, sy = 0;
  for (let i = 0; i < face.length; i++) { sx += g.positions[i * 3]; sy += g.positions[i * 3 + 1]; }
  assert.ok(Math.abs(sx / face.length) < 1e-6 && Math.abs(sy / face.length) < 1e-6, 'centroid ~ origin');
  // a landmark lower in the image (larger y) must map to a smaller GL-y
  let lo = 0, hi = 0;
  for (let i = 0; i < face.length; i++) { if (face[i].y > face[hi].y) hi = i; if (face[i].y < face[lo].y) lo = i; }
  assert.ok(g.positions[hi * 3 + 1] < g.positions[lo * 3 + 1], 'the lower face vertex sits lower in GL space');
});

test('uvs come from the capture-frame source, flipped for the GL texture origin, in [0,1]', () => {
  const uvSource = face.map((p) => ({ x: p.x, y: p.y }));
  const g = buildFaceGeometry(face, { topology: topo, uvSource });
  for (let i = 0; i < face.length; i++) {
    assert.ok(Math.abs(g.uvs[i * 2] - clamp01(face[i].x)) < 1e-6, 'u = source x');
    assert.ok(Math.abs(g.uvs[i * 2 + 1] - clamp01(1 - face[i].y)) < 1e-6, 'v = 1 - source y');
    assert.ok(g.uvs[i * 2] >= 0 && g.uvs[i * 2] <= 1 && g.uvs[i * 2 + 1] >= 0 && g.uvs[i * 2 + 1] <= 1);
  }
});

test('normals are unit length', () => {
  const g = buildFaceGeometry(face, { topology: topo });
  for (let i = 0; i < face.length; i++) {
    const m = Math.hypot(g.normals[i * 3], g.normals[i * 3 + 1], g.normals[i * 3 + 2]);
    assert.ok(Math.abs(m - 1) < 1e-5, `normal ${i} is unit (${m})`);
  }
});

test('a null landmark does not produce NaNs', () => {
  const holed = face.slice(); holed[5] = null;
  const g = buildFaceGeometry(holed, { topology: topo });
  for (const v of g.positions) assert.ok(Number.isFinite(v));
  for (const v of g.normals) assert.ok(Number.isFinite(v));
});

test('computeSmoothNormals gives a flat +Z sheet an all-facing-viewer normal', () => {
  const pos = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]); // one triangle in the z=0 plane
  const n = computeSmoothNormals(pos, [[0, 1, 2]], 3);
  for (let i = 0; i < 3; i++) assert.ok(Math.abs(Math.abs(n[i * 3 + 2]) - 1) < 1e-9, 'normal is ±Z');
});

// ── mat4 ────────────────────────────────────────────────────────────────────
test('m4multiply with identity is a no-op both sides', () => {
  const a = m4perspective(1, 1.5, 0.1, 100);
  assert.deepEqual([...m4multiply(m4identity(), a)], [...a]);
  assert.deepEqual([...m4multiply(a, m4identity())], [...a]);
});

test('rotationY(0) is the identity; rotationY(π/2) sends +X to −Z', () => {
  const r0 = m4rotationY(0), id = m4identity();
  for (let i = 0; i < 16; i++) assert.ok(Math.abs(r0[i] - id[i]) < 1e-9, `rotationY(0)[${i}] = identity`);
  const r = m4rotationY(Math.PI / 2);
  // column-major: transforming (1,0,0) → column 0 = (r0,r1,r2)
  assert.ok(Math.abs(r[0]) < 1e-9 && Math.abs(r[2] - -1) < 1e-9, '+X rotates toward −Z');
});

test('perspective has the expected diagonal and w-clip term', () => {
  const p = m4perspective(Math.PI / 2, 1, 1, 3);
  assert.ok(Math.abs(p[5] - 1) < 1e-9, 'f = cot(fovy/2) = 1 at 90°');
  assert.equal(p[11], -1, 'w = -z clip term');
  assert.equal(p[15], 0);
});

test('translation places the offset in the last column', () => {
  const t = m4translation(2, -3, 5);
  assert.equal(t[12], 2); assert.equal(t[13], -3); assert.equal(t[14], 5);
});

function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

console.log(`\nwebgl_face: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
