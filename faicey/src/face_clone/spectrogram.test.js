/**
 * spectrogram.test.js — the waterfall display model: dB scaling, colormap,
 * axis mapping, and the rolling buffer. Pure, so every claim is proven.
 * Run: node src/face_clone/spectrogram.test.js
 */
import { strict as assert } from 'assert';
import {
  dbNorm, magnitudesToDb, inferno, magma, logBinForX, linBinForX, Spectrogram,
} from './spectrogram.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

test('dbNorm maps the reference to 1, −45 dB to ~0.5, and the floor to 0', () => {
  assert.ok(Math.abs(dbNorm(1, 1) - 1) < 1e-6, 'ref → 1');
  assert.ok(Math.abs(dbNorm(Math.pow(10, -45 / 20), 1) - 0.5) < 1e-3, '−45 dB → 0.5');
  assert.ok(dbNorm(1e-9, 1) < 1e-3, 'far below floor → 0');
  assert.equal(dbNorm(1, 0), 0, 'no reference → 0');
});

test('magnitudesToDb: the peak bin is 1, a −60 dB bin sits at ~1/3', () => {
  const mags = new Float32Array([1, Math.pow(10, -60 / 20), 0]);
  const d = magnitudesToDb(mags, { floorDb: -90, refMax: 1 });
  assert.ok(Math.abs(d[0] - 1) < 1e-6);
  assert.ok(Math.abs(d[1] - (1 - 60 / 90)) < 1e-3, '−60 dB over a −90 floor');
  assert.ok(d[2] < 1e-3);
});

test('inferno goes dark→bright, monotonic in luminance, endpoints correct', () => {
  const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  assert.ok(lum(inferno(0)) < 20, '0 → near-black');
  assert.ok(lum(inferno(1)) > 200, '1 → bright');
  let prev = -1, ok = true;
  for (let t = 0; t <= 1.0001; t += 0.1) { const l = lum(inferno(t)); if (l < prev - 8) ok = false; prev = l; }
  assert.ok(ok, 'luminance rises monotonically');
  for (const c of inferno(0.5)) assert.ok(c >= 0 && c <= 255, 'channels in range');
});

test('magma is also a valid dark→bright ramp', () => {
  const lum = (c) => c[0] + c[1] + c[2];
  assert.ok(lum(magma(0)) < lum(magma(1)));
});

test('logBinForX is monotonic and hits its endpoints', () => {
  const W = 300, fmin = 60, fmax = 8000, binHz = 43;
  assert.equal(logBinForX(0, W, fmin, fmax, binHz), Math.round(fmin / binHz));
  assert.equal(logBinForX(W - 1, W, fmin, fmax, binHz), Math.round(fmax / binHz));
  let prev = -1, ok = true;
  for (let x = 0; x < W; x += 10) { const b = logBinForX(x, W, fmin, fmax, binHz); if (b < prev) ok = false; prev = b; }
  assert.ok(ok, 'bins increase with x');
});

test('linBinForX spans 0..fmax linearly', () => {
  const W = 300, fmax = 8000, binHz = 43;
  assert.equal(linBinForX(0, W, fmax, binHz), 0);
  assert.ok(Math.abs(linBinForX(W, W, fmax, binHz) - Math.round(fmax / binHz)) <= 1);
  assert.ok(linBinForX(W / 2, W, fmax, binHz) < linBinForX(W, W, fmax, binHz));
});

test('Spectrogram rolls: it keeps the last `rows` frames, newest last', () => {
  const sg = new Spectrogram(3);
  for (let i = 0; i < 5; i++) sg.push(Float32Array.of(i));
  assert.equal(sg.length, 3, 'capped at rows');
  assert.deepEqual([...sg.latest()], [4], 'newest frame');
  assert.deepEqual(sg.frames().map((f) => f[0]), [2, 3, 4], 'oldest dropped');
  sg.clear(); assert.equal(sg.length, 0);
});

test('Spectrogram accepts plain arrays and stores Float32Array copies', () => {
  const sg = new Spectrogram(2);
  const src = [0.1, 0.2, 0.3];
  sg.push(src); src[0] = 9;
  assert.ok(Math.abs(sg.latest()[0] - 0.1) < 1e-6, 'a copy was stored, not a reference');
  assert.ok(sg.latest() instanceof Float32Array);
});

console.log(`\nspectrogram: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
