/**
 * scifi_substrate.test.js — the shared HUD substrate's geometry + field model.
 * The canvas draw is browser-only; the layout math and the drifting field are
 * proven headless.
 * Run: node src/face_clone/scifi_substrate.test.js
 */
import { strict as assert } from 'assert';
import { cornerBrackets, reticleSegments, ParticleField, SCIFI_PALETTE } from './scifi_substrate.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

test('cornerBrackets returns four L-shaped brackets inside the frame', () => {
  const W = 200, H = 100, b = cornerBrackets(W, H, 16, 5);
  assert.equal(b.length, 4);
  for (const poly of b) {
    assert.equal(poly.length, 3, 'each bracket is an L (3 points)');
    for (const p of poly) assert.ok(p.x >= 0 && p.x <= W && p.y >= 0 && p.y <= H, 'inside the frame');
  }
  // top-left corner sits near the origin (inset 5)
  assert.deepEqual(b[0][1], { x: 5, y: 5 });
});

test('reticleSegments makes four ticks centred on the point, with a gap', () => {
  const seg = reticleSegments(50, 40, 10, 3);
  assert.equal(seg.length, 4);
  for (const [a, bp] of seg) { // no segment crosses the centre gap
    const da = Math.hypot(a.x - 50, a.y - 40), db = Math.hypot(bp.x - 50, bp.y - 40);
    assert.ok(Math.min(da, db) >= 3 - 1e-9, 'gap around the centre');
    assert.ok(Math.max(da, db) <= 10 + 1e-9, 'within radius');
  }
});

test('ParticleField is deterministic for a seed and stays in [0,1] under stepping', () => {
  const a = new ParticleField({ count: 40, seed: 42 });
  const b = new ParticleField({ count: 40, seed: 42 });
  assert.deepEqual(a.particles()[0], b.particles()[0], 'same seed → same field');
  const c = new ParticleField({ count: 40, seed: 43 });
  assert.notDeepEqual(a.particles()[0], c.particles()[0], 'different seed → different field');
  for (let i = 0; i < 500; i++) a.step();
  for (const q of a.particles()) assert.ok(q.x >= 0 && q.x <= 1 && q.y >= 0 && q.y <= 1, 'particle stays in bounds (bounces)');
});

test('the palette exposes the sci-fi tokens', () => {
  for (const k of ['bg', 'cyan', 'grid', 'ok', 'warn', 'text']) assert.ok(SCIFI_PALETTE[k], `palette.${k}`);
});

console.log(`\nscifi_substrate: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
