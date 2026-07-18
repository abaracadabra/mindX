/**
 * mech.test.js — the human ↔ machine slider's pure core.
 * Run: node src/face_clone/mech.test.js
 */
import { strict as assert } from 'assert';
import { mechFactor, faceCenterX, featureIsMech, MECH_PALETTE } from './mech.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

test('mechFactor is 0 on the human side and ramps to the slider level on the mech side', () => {
  const C = 100, seam = 40;
  assert.equal(mechFactor(60, C, 1, { side: 'right', seam }), 0, 'human side → 0');
  assert.equal(mechFactor(100, C, 1, { side: 'right', seam }), 0, 'exactly on the centre line → 0');
  assert.ok(Math.abs(mechFactor(120, C, 1, { side: 'right', seam }) - 0.5) < 1e-9, 'half a seam in → half');
  assert.equal(mechFactor(200, C, 1, { side: 'right', seam }), 1, 'deep on the mech side → full level');
});

test('mechFactor scales by the slider level', () => {
  assert.ok(Math.abs(mechFactor(200, 100, 0.5, { seam: 40 }) - 0.5) < 1e-9);
  assert.equal(mechFactor(200, 100, 0, { seam: 40 }), 0, 'level 0 → no mech anywhere');
});

test("mechFactor honours the 'left' side", () => {
  assert.equal(mechFactor(120, 100, 1, { side: 'left', seam: 40 }), 0, 'right of centre is human when side=left');
  assert.ok(mechFactor(40, 100, 1, { side: 'left', seam: 40 }) > 0, 'left of centre mechanises');
});

test('faceCenterX averages the landmark x through the fit transform', () => {
  const lm = [{ x: 0, y: 0 }, { x: 1, y: 0 }, null, { x: 0.5, y: 0 }];
  const cx = faceCenterX(lm, (p) => ({ x: p.x * 100, y: p.y * 100 }));
  assert.ok(Math.abs(cx - 50) < 1e-9, 'mean x = 0.5 → 50 px');
});

test('featureIsMech + palette', () => {
  assert.equal(featureIsMech(200, 100, 1, { seam: 40 }), true);
  assert.equal(featureIsMech(50, 100, 1, { seam: 40 }), false);
  assert.equal(featureIsMech(200, 100, 0), false, 'level 0 → nothing is mech');
  assert.ok(MECH_PALETTE.optic && MECH_PALETTE.steel, 'palette tokens present');
});

console.log(`\nmech: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
