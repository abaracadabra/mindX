/**
 * neutral_face.test.js — the procedural face is anatomically sane and drives
 * the expression system. Pure Node, no DOM. Run: node src/face_clone/neutral_face.test.js
 */
import { strict as assert } from 'assert';
import { neutralFace, placedIndices } from './neutral_face.js';
import { applyExpression } from './expressions.js';
import { LM, proportions } from './geometry.js';
import { measureFaceprint } from './faceprint.js';
import { personaPrint } from './persona.js';

let pass = 0, fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

const F = neutralFace();

await test('every canonical feature index is placed (no blob holes)', () => {
  assert.equal(F.length, 478);
  for (const i of placedIndices()) {
    assert.ok(F[i], `index ${i} placed`);
    assert.ok(Number.isFinite(F[i].x) && Number.isFinite(F[i].y), `index ${i} finite`);
  }
});

await test('the face has real anatomical layout — brows above eyes above nose above mouth', () => {
  const browY = F[LM.browR].y, eyeY = F[LM.eyeTopR].y, noseTipY = F[LM.noseTip].y, mouthY = F[LM.lipTop].y, chinY = F[LM.chin].y;
  assert.ok(browY < eyeY, 'brow above eye');
  assert.ok(eyeY < noseTipY, 'eye above nose tip');
  assert.ok(noseTipY < mouthY, 'nose above mouth');
  assert.ok(mouthY < chinY, 'mouth above chin');
  assert.ok(F[LM.faceTop].y < browY, 'forehead above brows');
});

await test('the face is two-eyed and symmetric — left/right features mirror', () => {
  const cx = (F[LM.eyeInR].x + F[LM.eyeInL].x) / 2;
  assert.ok(F[LM.eyeOutR].x < F[LM.eyeInR].x, 'right eye outer is left of inner');
  assert.ok(F[LM.eyeOutL].x > F[LM.eyeInL].x, 'left eye outer is right of inner');
  // mirror symmetry about the centre line
  assert.ok(Math.abs((cx - F[LM.eyeOutR].x) - (F[LM.eyeOutL].x - cx)) < 0.02, 'eyes mirror');
  assert.ok(Math.abs((cx - F[LM.mouthR].x) - (F[LM.mouthL].x - cx)) < 0.02, 'mouth mirrors');
});

await test('the nose actually protrudes in z (it is a face, not a plane)', () => {
  assert.ok(F[LM.noseTip].z > F[LM.faceTop].z, 'nose tip forward of forehead');
  assert.ok(F[LM.noseTip].z > 0.05, 'nose tip has real depth');
});

await test('expressions displace the real face — happy raises mouth corners vs neutral', () => {
  const neutral = applyExpression(F, 'neutral');
  const happy = applyExpression(F, 'happy', 1);
  const sad = applyExpression(F, 'sad', 1);
  // +y is down; a smile raises the corners (smaller y)
  assert.ok(happy.landmarks[LM.mouthR].y < neutral.landmarks[LM.mouthR].y, 'happy raises the corner');
  assert.ok(sad.landmarks[LM.mouthR].y > neutral.landmarks[LM.mouthR].y, 'sad drops the corner');
  assert.notEqual(happy.hue, sad.hue, 'emotions carry distinct hues');
});

await test('surprised opens the mouth and widens the eyes', () => {
  const neutral = applyExpression(F, 'neutral');
  const surprised = applyExpression(F, 'surprised', 1);
  const gap = (l) => Math.abs(l[LM.lipBot].y - l[LM.lipTop].y);
  assert.ok(gap(surprised.landmarks) > gap(neutral.landmarks), 'jaw drops open');
  assert.ok(surprised.landmarks[LM.eyeTopR].y < neutral.landmarks[LM.eyeTopR].y, 'eyes widen');
});

await test('recentre/rescale keeps the face intact', () => {
  const big = neutralFace({ scale: 1.5 });
  const w0 = Math.abs(F[LM.cheekL].x - F[LM.cheekR].x);
  const w1 = Math.abs(big[LM.cheekL].x - big[LM.cheekR].x);
  assert.ok(w1 > w0 * 1.4, 'scale widens the face');
});

await test('the neutral face yields a VALID faceprint — every proportion finite & positive', () => {
  const p = proportions(F);
  for (const [k, v] of Object.entries(p)) {
    assert.ok(Number.isFinite(v), `${k} is finite`);
    assert.ok(v > 0, `${k} is positive (got ${v}) — a zero proportion means an unplaced landmark`);
  }
});

await test('the neutral face binds into a valid persona (create flow, face-only)', async () => {
  const face = await measureFaceprint(proportions(F), { confidence: 1, symmetry: 1, frontality: 1 });
  assert.ok(face.hash.startsWith('0x'), 'faceprint hash');
  const persona = await personaPrint({ face, label: 'Neutral' });
  assert.ok(persona.hash.startsWith('0x'), 'persona hash');
  assert.deepEqual(persona.modalities, ['face'], 'face-only persona');
  // deterministic — the demo's create flow must reproduce the same identity
  const again = await personaPrint({ face, label: 'Neutral' });
  assert.equal(persona.hash, again.hash, 'same face → same persona');
});

console.log(`\nneutral_face: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
