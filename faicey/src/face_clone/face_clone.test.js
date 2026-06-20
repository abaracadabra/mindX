/**
 * face_clone.test.js — face cloning core, dependency-free (no MediaPipe needed).
 *
 * Exercises the pure-JS pipeline with synthetic pre-detected landmark frames: proportions,
 * pose-normalised aggregation, the 18-dp forensic faceprint, and identity matching. The same
 * paths run unchanged in the browser with real MediaPipe landmarks.
 *
 *   node src/face_clone/face_clone.test.js
 */

import assert from 'node:assert/strict';
import { proportions, symmetry, aggregate, frontality } from './geometry.js';
import { measureFaceprint, toRegisterArgs, faceprintDistance, FACEPRINT_MEASURES } from './faceprint.js';
import { FaceCloneEngine } from './face_clone_engine.js';
import { applyExpression, EXPRESSION_LABELS } from './expressions.js';
import { personaPrint, personaMatch } from './persona.js';
import { blendshapesToMorphs, morphsToEngine, audioMouth, applyMouthOpen } from './animate.js';
import { LM } from './geometry.js';
import { FACE_THEMES } from './contours.js';

let passed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log(`  ok   ${name}`); }
  catch (e) { console.error(`  FAIL ${name}\n       ${e.message}`); process.exitCode = 1; }
}

// synthetic 478-landmark face parameterised by jaw + interocular so distinct people differ
function face({ jitter = 0, jaw = 0.72, eyeX = 0.07, ox = 0 } = {}) {
  const L = new Array(478).fill(0).map(() => ({ x: 0.5, y: 0.5, z: 0 }));
  const j = () => (jitter ? (Math.sin(L.length * 7 + Math.random() * 1e3) * jitter) : 0);
  const set = (i, x, y, z = 0) => (L[i] = { x: x + ox + j(), y: y + j(), z });
  set(10, 0.5, 0.13); set(152, 0.5, 0.92); set(234, 0.22, 0.5); set(454, 0.78, 0.5);
  set(116, 0.27, 0.46); set(345, 0.73, 0.46); set(172, 0.5 - jaw / 2, 0.78); set(397, 0.5 + jaw / 2, 0.78);
  set(133, 0.5 - eyeX, 0.42); set(362, 0.5 + eyeX, 0.42); set(33, 0.5 - eyeX - 0.08, 0.42); set(263, 0.5 + eyeX + 0.08, 0.42);
  set(159, 0.39, 0.40); set(105, 0.39, 0.36); set(168, 0.5, 0.42); set(2, 0.5, 0.6); set(1, 0.5, 0.58);
  set(98, 0.45, 0.6); set(327, 0.55, 0.6); set(61, 0.42, 0.72); set(291, 0.58, 0.72);
  set(13, 0.5, 0.70); set(14, 0.5, 0.74); set(0, 0.5, 0.69);
  return L;
}
const ID = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
const YAW = [0.88, 0, 0.48, 0, 0, 1, 0, 0, -0.48, 0, 0.88, 0, 0, 0, 0, 1];

console.log('faicey face clone');

await test('proportions are scale-invariant ratios', () => {
  const p = proportions(face());
  assert.ok(p.faceAspect > 0 && p.jawRatio > 0 && p.interocularRatio > 0);
  // scaling the whole face must not change the ratios
  const big = face().map((q) => ({ x: q.x * 2, y: q.y * 2, z: 0 }));
  const pb = proportions(big);
  for (const k of FACEPRINT_MEASURES) assert.ok(Math.abs(p[k] - pb[k]) < 1e-9, `${k} not scale-invariant`);
});

await test('faceprint: 18-dp measures + deterministic sha256 + registerArgs', async () => {
  const p = proportions(face());
  const fp = await measureFaceprint(p, { confidence: 0.95, symmetry: 1, frontality: 1 });
  assert.equal(fp.measures.length, FACEPRINT_MEASURES.length);
  for (const m of fp.measures) assert.equal(typeof m, 'bigint');
  assert.match(fp.hash, /^0x[0-9a-f]{64}$/);
  const fp2 = await measureFaceprint(proportions(face()), { confidence: 0.95, symmetry: 1, frontality: 1 });
  assert.equal(fp.hash, fp2.hash, 'same face → same hash');
  const args = toRegisterArgs(fp);
  assert.equal(args.m.length, FACEPRINT_MEASURES.length);
  // faceAspect ratio reads back at 18-dp fixed point
  assert.equal(args.m[0], String(BigInt(Math.round(p.faceAspect * 1e9)) * 10n ** 9n));
});

await test('aggregate denoises multi-frame toward the clean geometry', () => {
  const clean = face();
  const frames = [
    { landmarks: clean, matrix: ID },
    { landmarks: face({ jitter: 0.03 }), matrix: YAW },
    { landmarks: face({ jitter: 0.03 }), matrix: YAW },
  ];
  const agg = aggregate(frames);
  assert.equal(agg.frames, 3);
  assert.equal(agg.frontalIndex, 0); // identity matrix is the most frontal
  assert.ok(frontality(ID) > frontality(YAW));
});

await test('engine clones from single / perspectives / video', async () => {
  const eng = await new FaceCloneEngine().init();
  assert.equal(typeof eng.capability.mediapipe, 'boolean');
  const s = await eng.cloneFromImage({ landmarks: face(), matrix: ID, confidence: 0.9 });
  assert.equal(s.source, 'single-image');
  assert.ok(s.faceprint.hash.startsWith('0x') && s.proportions.faceAspect > 0);
  const p = await eng.cloneFromPerspectives([
    { landmarks: face({ jitter: 0.01 }), matrix: ID },
    { landmarks: face({ jitter: 0.01 }), matrix: YAW },
  ]);
  assert.equal(p.frames, 2);
  const v = await eng.cloneFromVideo(Array.from({ length: 6 }, () => ({ landmarks: face({ jitter: 0.02 }), matrix: ID })));
  assert.ok(v.frames >= 1 && v.frames <= 6, 'video clones from the recognized frames');
  assert.ok(v.recognition, 'video clone reports recognition');
});

await test('faceprint identity: same person matches, different rejects', async () => {
  const eng = await new FaceCloneEngine().init();
  const a = await eng.cloneFromImage({ landmarks: face({ jaw: 0.72 }), matrix: ID });
  const a2 = await eng.cloneFromImage({ landmarks: face({ jaw: 0.72, jitter: 0.004 }), matrix: ID });
  const b = await eng.cloneFromImage({ landmarks: face({ jaw: 0.5, eyeX: 0.05 }), matrix: ID });
  assert.equal(FaceCloneEngine.match(a, a2).same, true, 'same person should match');
  assert.equal(FaceCloneEngine.match(a, b).same, false, 'different people should not match');
  assert.ok(faceprintDistance(a.faceprint, b.faceprint) > faceprintDistance(a.faceprint, a2.faceprint));
});

await test('symmetry is high for a symmetric face', () => {
  assert.ok(symmetry(face()) > 0.95);
});

await test('video recognition keeps one person, drops outlier frames', async () => {
  const eng = await new FaceCloneEngine().init();
  // 6 frames of person A (wide jaw) + 2 frames of person B (narrow jaw)
  const frames = [
    ...Array.from({ length: 6 }, () => ({ landmarks: face({ jaw: 0.72, jitter: 0.004 }), matrix: ID })),
    { landmarks: face({ jaw: 0.5, eyeX: 0.05 }), matrix: ID },
    { landmarks: face({ jaw: 0.5, eyeX: 0.05 }), matrix: ID },
  ];
  const out = await eng.cloneFromVideo(frames);
  assert.ok(out.recognition, 'recognition reported');
  assert.equal(out.recognition.recognizedFrames, 6, 'keeps the 6 consistent frames');
  assert.equal(out.recognition.droppedFrames, 2, 'drops the 2 outlier frames');
});

await test('expressions: cloned face emotes (smile up, frown down), originals intact', () => {
  assert.ok(EXPRESSION_LABELS.includes('happy') && EXPRESSION_LABELS.includes('sad'));
  const base = face();
  const y0 = base[291].y;
  const happy = applyExpression(base, { label: 'happy', intensity: 0.9 });
  const sad = applyExpression(base, 'sad');
  assert.ok(happy.landmarks[291].y < y0, 'happy lifts mouth corner');
  assert.ok(sad.landmarks[291].y > y0, 'sad drops mouth corner');
  assert.equal(base[291].y, y0, 'originals untouched');
  assert.equal(applyExpression(base, 'nonsense').label, 'neutral'); // unknown → neutral
});

await test('persona print binds FACE (+VOICE), deterministic + registerable', async () => {
  const fp = await measureFaceprint(proportions(face()), { confidence: 0.9 });
  const voice = { hash: '0xVOICE', measuresStr: ['1000000000000000000'], precisionScore: '900000000000000000' };
  const full = await personaPrint({ face: fp, voice, label: 'p' });
  assert.match(full.hash, /^0x[0-9a-f]{64}$/);
  assert.deepEqual(full.modalities, ['face', 'voice']);
  assert.equal(full.registerArgs.m.length, FACEPRINT_MEASURES.length + 1); // face + voice measures
  const full2 = await personaPrint({ face: fp, voice, label: 'p' });
  assert.equal(full.hash, full2.hash, 'deterministic');
  const faceOnly = await personaPrint({ face: fp });
  assert.deepEqual(faceOnly.modalities, ['face']);
  assert.notEqual(faceOnly.hash, full.hash, 'face-only differs from face+voice');
  assert.equal(personaMatch(full, full2).hash, true);
});

await test('animate: blendshapes → morphs, audio → mouth, lip displaces', () => {
  const m = blendshapesToMorphs([
    { categoryName: 'jawOpen', score: 0.8 },
    { categoryName: 'mouthSmileLeft', score: 0.6 }, { categoryName: 'mouthSmileRight', score: 0.6 },
    { categoryName: 'eyeBlinkLeft', score: 0.9 },
  ]);
  assert.ok(Math.abs(m.mouthOpen - 0.8) < 1e-9 && Math.abs(m.smile - 0.6) < 1e-9);
  assert.equal(morphsToEngine(m).mouth_open, 0.8);
  assert.equal(audioMouth(0.005), 0, 'silence → closed mouth');
  assert.ok(audioMouth(0.15) > 0.5, 'loud → open mouth');
  // applyMouthOpen lowers the bottom lip, originals intact
  const f = new Array(478).fill(0).map(() => ({ x: 0.5, y: 0.5, z: 0 }));
  f[LM.eyeInR] = { x: 0.43, y: 0.42 }; f[LM.eyeInL] = { x: 0.57, y: 0.42 }; f[LM.lipBot] = { x: 0.5, y: 0.74 };
  const o = applyMouthOpen(f, 1.0);
  assert.ok(o[LM.lipBot].y > 0.74, 'mouth opens (lower lip drops)');
  assert.equal(f[LM.lipBot].y, 0.74, 'originals untouched');
});

await test('themes: wireframe is the default, plus new themes', () => {
  assert.equal(FACE_THEMES[0], 'wireframe');
  assert.ok(FACE_THEMES.includes('neon') && FACE_THEMES.includes('dots') && FACE_THEMES.includes('mesh'));
  assert.ok(FACE_THEMES.length >= 5);
});

console.log(`\n${passed} passed`);
