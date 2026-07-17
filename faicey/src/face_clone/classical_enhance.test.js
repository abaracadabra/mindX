/**
 * classical_enhance.test.js — the weight-free enhancement fallback.
 * Pure DSP, so every claim is proven headless. It must genuinely improve the
 * composite AND be honestly capped at realism by the gate.
 * Run: node src/face_clone/classical_enhance.test.js
 */
import { strict as assert } from 'assert';
import {
  boxBlur, featherSeams, unsharpMask, toneCurve, enhanceClassical, ClassicalEnhancer,
} from './classical_enhance.js';
import { gradeFidelity } from './neural_render.js';

let pass = 0, fail = 0;
const test = async (name, fn) => { try { await fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

// build an RGBA image from a per-pixel grey function
const mk = (w, h, f) => {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const v = f(x, y), o = (y * w + x) * 4;
    data[o] = v; data[o + 1] = v; data[o + 2] = v; data[o + 3] = 255;
  }
  return { data, width: w, height: h };
};
const at = (img, x, y) => img.data[(y * img.width + x) * 4]; // red channel

await test('boxBlur leaves a constant image unchanged and preserves alpha', () => {
  const img = mk(8, 8, () => 120);
  const b = boxBlur(img, 2);
  for (let i = 0; i < b.data.length; i += 4) { assert.equal(b.data[i], 120); assert.equal(b.data[i + 3], 255); }
});

await test('boxBlur spreads an impulse to its neighbours (and dims the peak)', () => {
  const img = mk(9, 9, (x, y) => (x === 4 && y === 4 ? 255 : 0));
  const b = boxBlur(img, 1);
  assert.ok(at(b, 4, 4) < 255, 'the peak is spread out');
  assert.ok(at(b, 3, 4) > 0 && at(b, 5, 4) > 0 && at(b, 4, 3) > 0, 'energy reached the neighbours');
});

await test('unsharpMask increases contrast across an edge (overshoot), flat stays flat', () => {
  const edge = mk(10, 4, (x) => (x < 5 ? 80 : 160));
  const u = unsharpMask(edge, { amount: 0.8, radius: 1 });
  assert.ok(at(u, 4, 2) < 80 || at(u, 5, 2) > 160, 'the edge is sharpened (overshoot on one side)');
  const flat = mk(6, 6, () => 100);
  const uf = unsharpMask(flat, { amount: 1 });
  for (let i = 0; i < uf.data.length; i += 4) assert.equal(uf.data[i], 100, 'no detail → no change');
});

await test('toneCurve with contrast>1 pushes values away from mid; identity leaves them', () => {
  const img = mk(4, 4, (x) => (x < 2 ? 100 : 160)); // straddle mid (128)
  const t = toneCurve(img, { contrast: 1.2 });
  assert.ok(at(t, 0, 0) < 100, 'below mid pushed down');
  assert.ok(at(t, 3, 0) > 160, 'above mid pushed up');
  const id = toneCurve(img, { contrast: 1, gamma: 1 });
  for (let i = 0; i < id.data.length; i += 4) assert.equal(id.data[i], img.data[i], 'identity params → unchanged');
});

await test('featherSeams pulls a seam toward its neighbours (softens the step)', () => {
  // a hard vertical seam like an affine triangle boundary
  const img = mk(10, 6, (x) => (x < 5 ? 60 : 200));
  const f = featherSeams(img, { radius: 1, blend: 0.5 });
  assert.ok(at(f, 4, 3) > 60, 'the dark side of the seam lifts toward the light side');
  assert.ok(at(f, 5, 3) < 200, 'the light side eases toward the dark side');
});

await test('enhanceClassical returns a same-size image, alpha intact, and actually changes pixels', () => {
  const img = mk(16, 16, (x, y) => ((x + y) % 4 === 0 ? 90 : 170)); // textured with seams
  const e = enhanceClassical(img);
  assert.equal(e.width, 16); assert.equal(e.height, 16);
  let changed = 0;
  for (let i = 0; i < e.data.length; i += 4) { if (e.data[i] !== img.data[i]) changed++; assert.equal(e.data[i + 3], 255); }
  assert.ok(changed > 0, 'the enhancement is not a no-op');
});

await test('the ClassicalEnhancer backend is always available and the gate caps it at realism', async () => {
  const ce = new ClassicalEnhancer();
  const d = ce.describe();
  assert.equal(d.available, true);
  assert.equal(d.backend, 'classical');
  const frame = mk(8, 8, () => 128);
  const out = await ce.refine(frame);
  assert.equal(out.backend, 'classical');
  assert.equal(out.neural, false);
  // the doctrine: classical enhancement can NEVER be graded hyperreal
  const g = gradeFidelity({ backend: out.backend, identity: 1, structural: 1, coverage: 1, hasTexture: true });
  assert.equal(g.hyperreal, false);
  assert.equal(g.verdict, 'realism');
  assert.ok(g.reasons.some((r) => r.includes('only a neural render')));
});

console.log(`\nclassical_enhance: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
