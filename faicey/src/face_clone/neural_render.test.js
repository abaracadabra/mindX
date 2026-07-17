/**
 * neural_render.test.js — the neural seam + the fidelity gate.
 * The gate is the doctrine: hyperreal must be EARNED by a neural render that
 * measures through, and NOTHING else can claim it. These tests lock that.
 * Run: node src/face_clone/neural_render.test.js
 */
import { strict as assert } from 'assert';
import {
  NeuralRenderer, gradeFidelity, identityConsistency, structuralSimilarity,
  renderCoverage, FIDELITY,
} from './neural_render.js';

let pass = 0, fail = 0;
const test = async (name, fn) => { try { await fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

// ── the gate: hyperreal is earned, and only by a neural render ──────────────
await test('a neural render that clears every threshold is stamped hyperreal', () => {
  const g = gradeFidelity({ backend: 'neural', identity: 0.97, structural: 0.95, coverage: 0.9, hasTexture: true });
  assert.equal(g.verdict, 'hyperreal');
  assert.equal(g.hyperreal, true);
});

await test('a neural render that misses a threshold is NOT hyperreal — capped honestly with a reason', () => {
  const g = gradeFidelity({ backend: 'neural', identity: 0.80, structural: 0.95, coverage: 0.9, hasTexture: true });
  assert.equal(g.hyperreal, false);
  assert.equal(g.verdict, 'realism', 'has texture → realism, not hyperreal');
  assert.ok(g.reasons.some((r) => r.includes('identity')), 'the failing measure is named');
  assert.ok(g.reasons.some((r) => r.includes('did not measure up')));
});

await test('the affine/classical backend can NEVER earn hyperreal, even at perfect scores', () => {
  const g = gradeFidelity({ backend: 'affine', identity: 1, structural: 1, coverage: 1, hasTexture: true });
  assert.equal(g.hyperreal, false);
  assert.equal(g.verdict, 'realism');
  assert.ok(g.reasons.some((r) => r.includes('only a neural render')), 'the boundary is stated');
});

await test('no backend + texture → realism; no backend + no texture → surface', () => {
  assert.equal(gradeFidelity({ backend: null, hasTexture: true }).verdict, 'realism');
  assert.equal(gradeFidelity({ backend: null, hasTexture: false }).verdict, 'surface');
  assert.equal(gradeFidelity({}).hyperreal, false);
});

await test('the thresholds are the published constants (no silent relaxation)', () => {
  // right at the line passes; a hair under fails — proves the gate uses >=
  const atLine = gradeFidelity({ backend: 'neural', identity: FIDELITY.IDENTITY_MIN, structural: FIDELITY.STRUCTURAL_MIN, coverage: FIDELITY.COVERAGE_MIN, hasTexture: true });
  assert.equal(atLine.hyperreal, true);
  const under = gradeFidelity({ backend: 'neural', identity: FIDELITY.IDENTITY_MIN - 1e-6, structural: FIDELITY.STRUCTURAL_MIN, coverage: FIDELITY.COVERAGE_MIN, hasTexture: true });
  assert.equal(under.hyperreal, false);
});

// ── the metrics the gate rests on ───────────────────────────────────────────
await test('identityConsistency is 1 for the same print and falls as it drifts', () => {
  const v = [0.5, 1.2, 0.8, 0.33, 2.1];
  assert.ok(Math.abs(identityConsistency(v, v) - 1) < 1e-9, 'identical → 1');
  const near = v.map((x) => x * 1.02);
  const far = v.map((x) => x * 1.4);
  assert.ok(identityConsistency(v, near) > identityConsistency(v, far), 'more drift → lower');
  assert.ok(identityConsistency(v, far) < 1);
  assert.equal(identityConsistency(v, [1, 2]), 0, 'mismatched length → 0');
});

await test('structuralSimilarity is ~1 for identical images and lower for noise', () => {
  const a = Array.from({ length: 256 }, (_, i) => (i % 16) / 16);
  const noise = a.map((x, i) => Math.min(1, Math.max(0, x + ((i * 37) % 13) / 13 - 0.5)));
  assert.ok(structuralSimilarity(a, a) > 0.999, 'identical → ~1');
  assert.ok(structuralSimilarity(a, noise) < structuralSimilarity(a, a), 'noise lowers SSIM');
  assert.equal(structuralSimilarity([], []), 0);
});

await test('renderCoverage is the filled fraction of the face mask', () => {
  assert.equal(renderCoverage(new Uint8Array([1, 1, 0, 0])), 0.5);
  assert.equal(renderCoverage(new Uint8Array([1, 1, 1, 1])), 1);
  assert.equal(renderCoverage(null), 0);
});

// ── the backend: dormant by default, honest passthrough ─────────────────────
await test('a fresh NeuralRenderer is dormant and reports it honestly', async () => {
  const nr = new NeuralRenderer();
  const d = nr.describe();
  assert.equal(d.available, false);
  assert.equal(d.backend, null);
  assert.ok(/not loaded|dormant/.test(d.reason));
});

await test('load without a runtime or weights stays dormant (no pretending)', async () => {
  const nr = new NeuralRenderer();
  const d = await nr.load({ modelPath: null });
  assert.equal(d.available, false);
  assert.ok(/dormant/.test(d.reason));
});

await test('refine on a dormant renderer passes the frame through, neural:false', async () => {
  const nr = new NeuralRenderer();
  const frame = { data: new Uint8ClampedArray([10, 20, 30, 255]), width: 1, height: 1 };
  const out = await nr.refine(frame);
  assert.equal(out.neural, false);
  assert.equal(out.backend, null);
  assert.equal(out.image, frame, 'the exact same frame, untouched');
});

await test('an injected session activates the neural path and runs inference', async () => {
  // a stand-in ONNX session: brightens the image (proves the tensor round-trip)
  const fakeSession = {
    inputNames: ['input'], outputNames: ['output'],
    async run(feeds) {
      const t = feeds.input; const d = t.data.map((v) => Math.min(1, v + 0.1));
      return { output: { data: d, dims: t.dims } };
    },
  };
  const nr = new NeuralRenderer();
  const d = await nr.load({ session: fakeSession });
  assert.equal(d.available, true);
  assert.equal(d.backend, 'neural');
  const frame = { data: new Uint8ClampedArray([100, 100, 100, 255]), width: 1, height: 1 };
  const out = await nr.refine(frame);
  assert.equal(out.neural, true);
  assert.ok(out.image.data[0] > 100, 'the neural backend actually transformed the pixels');
  // and now the gate CAN grade it hyperreal if it measures through
  const g = gradeFidelity({ backend: out.backend, identity: 0.95, structural: 0.93, coverage: 0.9, hasTexture: true });
  assert.equal(g.hyperreal, true, 'a real neural render that measures up earns hyperreal');
});

console.log(`\nneural_render: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
