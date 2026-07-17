/**
 * capture.test.js — accurate webcam → FAICE capture. Pure Node, synthetic
 * frames. Run: node src/face_clone/capture.test.js
 */
import { strict as assert } from 'assert';
import { FaceCapture } from './capture.js';
import { neutralFace } from './neutral_face.js';

let pass = 0, fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

// identity-ish transform matrix with a given yaw (radians) → controls frontality
const mat = (yaw = 0) => {
  const m = new Array(16).fill(0);
  m[0] = Math.cos(yaw); m[5] = 1; m[10] = Math.cos(yaw);
  m[8] = Math.sin(yaw); m[2] = -Math.sin(yaw); m[15] = 1;
  return m;
};
// a face frame from the canonical neutral, with optional jitter + pose
const frame = (jitter = 0, yaw = 0) => ({
  landmarks: neutralFace().map((p) => ({
    x: p.x + (jitter ? (Math.random() * 2 - 1) * jitter : 0),
    y: p.y + (jitter ? (Math.random() * 2 - 1) * jitter : 0),
    z: p.z,
  })),
  matrix: mat(yaw),
});

await test('add() drops frames that are too turned', () => {
  const c = new FaceCapture({ minFrontality: 0.5 });
  c.add(frame(0, 0));      // frontal — kept
  c.add(frame(0, 2.2));    // strongly turned — frontality < 0.5, dropped
  assert.equal(c.count, 1, 'only the frontal frame kept');
});

await test('a stable, frontal capture measures as ACCURATE', async () => {
  const c = new FaceCapture();
  for (let i = 0; i < 30; i++) c.add(frame(0.0003, 0.02)); // tiny jitter, near dead-on
  const acc = c.accuracy();
  assert.ok(acc.frames >= 24, 'enough frames');
  assert.ok(acc.frontality > 0.9, 'frontal');
  assert.ok(acc.stability > 0.7, `stable (spread ${acc.perVertexSpread.toFixed(4)})`);
  assert.ok(['accurate', 'good'].includes(acc.verdict), `verdict ${acc.verdict}`);
});

await test('a jittery, turned capture measures as ROUGH/insufficient', () => {
  const c = new FaceCapture();
  for (let i = 0; i < 8; i++) c.add(frame(0.01, 0.5)); // big jitter, turned, few frames
  const acc = c.accuracy();
  assert.ok(acc.score < 0.65, `low score (${acc.score.toFixed(2)})`);
  assert.ok(['rough', 'insufficient'].includes(acc.verdict), `verdict ${acc.verdict}`);
});

await test('accuracy rises with more, cleaner frames', () => {
  const few = new FaceCapture();
  for (let i = 0; i < 4; i++) few.add(frame(0.002, 0.1));
  const many = new FaceCapture();
  for (let i = 0; i < 30; i++) many.add(frame(0.0003, 0.02));
  assert.ok(many.accuracy().score > few.accuracy().score, 'more + cleaner is more accurate');
});

await test('aggregate() stabilises jitter — averaging beats any single frame', async () => {
  const { poseNormalize } = await import('./geometry.js');
  const truth = poseNormalize(frame(0, 0).landmarks, mat(0)); // clean, in normalised space
  const dist = (pts) => { let s = 0; for (let v = 0; v < pts.length; v++) s += Math.hypot(pts[v].x - truth[v].x, pts[v].y - truth[v].y, pts[v].z - truth[v].z); return s / pts.length; };

  const c = new FaceCapture();
  const singles = [];
  for (let i = 0; i < 24; i++) { const f = frame(0.004, 0); c.add(f); singles.push(dist(poseNormalize(f.landmarks, f.matrix))); }
  const agg = c.aggregate();
  assert.equal(agg.landmarks.length, neutralFace().length, 'canonical topology preserved');
  const aggErr = dist(agg.landmarks);
  const meanSingleErr = singles.reduce((a, b) => a + b, 0) / singles.length;
  assert.ok(aggErr < meanSingleErr, `aggregate (${aggErr.toFixed(4)}) tighter than a lone frame (${meanSingleErr.toFixed(4)})`);
  assert.equal(agg.frames, 24, 'reports frame count');
});

await test('result() binds a FAICE — captured face + accuracy-weighted faceprint', async () => {
  const c = new FaceCapture();
  for (let i = 0; i < 26; i++) c.add(frame(0.0004, 0.02));
  const r = await c.result();
  assert.ok(r.faceprint.hash.startsWith('0x'), 'faceprint hash');
  assert.ok(r.landmarks.length > 400, 'the captured face travels as the FAICE geometry');
  // accuracy IS the print precision — a clean capture yields a confident print
  const precision = Number(r.faceprint.precisionScore) / 1e18;
  assert.ok(precision > 0.6, `accurate capture → confident print (${precision.toFixed(2)})`);
  assert.ok(Math.abs(precision - r.accuracy.score) < 0.35, 'precision tracks the measured accuracy');
});

console.log(`\ncapture: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
