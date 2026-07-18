/**
 * face_controls.test.js — the face-as-control-surface geometry + the range finder.
 * Run: node src/face_clone/face_controls.test.js
 */
import { strict as assert } from 'assert';
import { featureRegions, featureAtPoint, CONTROL_MAP } from './face_controls.js';
import { focalFromFov, ipdPixels, estimateDistanceMm, estimateDistanceCm, rangeFind, ADULT_IPD_MM } from './distance.js';
import { neutralFace } from './neutral_face.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

const face = neutralFace();
const fit = (p) => ({ x: p.x * 300, y: p.y * 300 }); // simple normalized→canvas

test('featureRegions builds discs for eyes(camera), ears(mic), mouth(output)', () => {
  const regions = featureRegions(face, fit);
  const controls = new Set(regions.map((r) => r.control));
  assert.ok(controls.has('camera') && controls.has('mic') && controls.has('output'), 'all three controls present');
  for (const r of regions) { assert.ok(r.r >= 10, 'clickable radius'); assert.equal(CONTROL_MAP[r.name], r.control); }
});

test('a click on an eye maps to the camera; on an ear to the mic; on the mouth to output', () => {
  const regions = featureRegions(face, fit);
  const hitOf = (name) => { const reg = regions.find((r) => r.name === name); return featureAtPoint(regions, reg.cx, reg.cy); };
  assert.equal(hitOf('rightEye').control, 'camera', 'eye → camera (the eye is a camera)');
  assert.equal(hitOf('leftEar').control, 'mic', 'ear → mic');
  assert.equal(hitOf('lipsOuter').control, 'output', 'mouth → output');
});

test('the nose maps to network diagnostics; the nostrils to blockchain + rage', () => {
  const regions = featureRegions(face, fit);
  const controls = new Set(regions.map((r) => r.control));
  assert.ok(controls.has('network'), 'nose → network');
  assert.ok(controls.has('blockchain'), 'right nostril → blockchain');
  assert.ok(controls.has('rage'), 'left nostril → rage');
  const hitOf = (name) => { const reg = regions.find((r) => r.name === name); return featureAtPoint(regions, reg.cx, reg.cy).control; };
  assert.equal(hitOf('noseRightAla'), 'blockchain');
  assert.equal(hitOf('noseLeftAla'), 'rage');
});

test('the third eye is NOT there by default, and opens the matrix when made visible', () => {
  const hidden = featureRegions(face, fit); // no points → the third eye is absent
  assert.ok(!hidden.some((r) => r.control === 'matrix'), 'third eye absent by default (not always there)');
  const shown = featureRegions(face, fit, { points: ['thirdEye'] });
  const eye = shown.find((r) => r.control === 'matrix');
  assert.ok(eye, 'appears when the caller says it is visible');
  assert.equal(featureAtPoint(shown, eye.cx, eye.cy).control, 'matrix', 'clicking it opens the matrix');
});

test('the brain hemispheres: left → analytical/math, right → creative/expression', () => {
  const regions = featureRegions(face, fit, { points: ['leftBrain', 'rightBrain'] });
  const controls = new Set(regions.map((r) => r.control));
  assert.ok(controls.has('analytical'), 'left brain → analytical');
  assert.ok(controls.has('creative'), 'right brain → creative');
  const hitOf = (name) => { const reg = regions.find((r) => r.name === name); return featureAtPoint(regions, reg.cx, reg.cy).control; };
  assert.equal(hitOf('leftBrain'), 'analytical');
  assert.equal(hitOf('rightBrain'), 'creative');
});

test('a click far from every feature hits nothing', () => {
  const regions = featureRegions(face, fit);
  assert.equal(featureAtPoint(regions, -500, -500), null);
});

test('overlapping discs resolve to the nearest feature centre', () => {
  const regions = [
    { name: 'a', control: 'camera', cx: 100, cy: 100, r: 40 },
    { name: 'b', control: 'mic', cx: 130, cy: 100, r: 40 },
  ];
  assert.equal(featureAtPoint(regions, 105, 100).name, 'a', 'closer centre wins');
  assert.equal(featureAtPoint(regions, 125, 100).name, 'b');
});

// ── the range finder (eye is a camera) ──────────────────────────────────────
test('focalFromFov: a 60° / 640px camera has focal ≈ 554 px', () => {
  const f = focalFromFov(640, 60);
  assert.ok(Math.abs(f - 554.26) < 1, `focal ${f.toFixed(1)} px`);
});

test('distance is inverse in IPD pixels — a nearer face (bigger IPD) reads closer', () => {
  const focalPx = focalFromFov(640, 60);
  const far = estimateDistanceMm(40, { focalPx }), near = estimateDistanceMm(120, { focalPx });
  assert.ok(near < far, 'bigger IPD-px → nearer');
  // exact pinhole: D = f·S/s
  assert.ok(Math.abs(far - focalPx * ADULT_IPD_MM / 40) < 1e-6, 'matches D = f·S/s');
});

test('a 63 mm IPD imaged at the focal-length-in-px equivalent reads ~1 m', () => {
  // if IPD px equals f·S/1000, the subject is 1000 mm away
  const focalPx = focalFromFov(640, 60);
  const ipdPx = focalPx * ADULT_IPD_MM / 1000;
  assert.ok(Math.abs(estimateDistanceCm(ipdPx, { focalPx }) - 100) < 0.1, '≈ 100 cm');
});

test('ipdPixels reads the iris landmarks; rangeFind is null without them', () => {
  const lm = []; lm[468] = { x: 0.45, y: 0.5 }; lm[473] = { x: 0.55, y: 0.5 };
  const ipd = ipdPixels(lm, 640, 480);
  assert.ok(Math.abs(ipd - 0.1 * 640) < 1e-6, 'IPD px = Δx·W');
  assert.ok(rangeFind(lm, 640, 480), 'range-finds with iris points');
  assert.equal(rangeFind([], 640, 480), null, 'no iris → null (never guesses)');
});

console.log(`\nface_controls: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
