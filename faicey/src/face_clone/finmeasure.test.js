/**
 * finmeasure.test.js — quant-finance estimation applied to voice measurement.
 * Every accuracy claim is proven against series with known statistics.
 * Run: node src/face_clone/finmeasure.test.js
 */
import { strict as assert } from 'assert';
import {
  mean, variance, stddev, skewness, kurtosis, ewma, ewmaVol,
  standardError, confidenceInterval, Kalman, jitter, shimmer,
  relativePerturbation, bollinger, zScore, outliers, autocorr,
  toFixed18, toFixed18Str, fromFixed18, accuracy18, ONE18,
} from './finmeasure.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

// deterministic pseudo-normal series (Box–Muller on a LCG — no Math.random)
function normalSeries(n, mu = 0, sigma = 1, seed = 12345) {
  const out = [], u = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  for (let i = 0; i < n; i += 2) {
    const a = Math.max(1e-9, u()), b = u();
    const r = Math.sqrt(-2 * Math.log(a));
    out.push(mu + sigma * r * Math.cos(2 * Math.PI * b));
    if (i + 1 < n) out.push(mu + sigma * r * Math.sin(2 * Math.PI * b));
  }
  return out;
}

test('mean/variance/stddev match a known series', () => {
  const x = [2, 4, 4, 4, 5, 5, 7, 9];
  assert.equal(mean(x), 5);
  assert.ok(Math.abs(variance(x, false) - 4) < 1e-9, 'population variance = 4');
  assert.ok(Math.abs(stddev(x, false) - 2) < 1e-9, 'population sd = 2');
});

test('skewness ~0 for a symmetric normal, kurtosis ~3', () => {
  const x = normalSeries(4000, 0, 1);
  assert.ok(Math.abs(skewness(x)) < 0.2, `skew ${skewness(x).toFixed(3)}`);
  assert.ok(Math.abs(kurtosis(x) - 3) < 0.4, `kurtosis ${kurtosis(x).toFixed(3)}`);
});

test('a right-skewed series reads positive skew', () => {
  const x = [1, 1, 1, 1, 2, 2, 3, 10];
  assert.ok(skewness(x) > 0.5);
});

test('EWMA tracks the level; ewmaVol is ~0 for a flat series and rises with jumps', () => {
  assert.ok(Math.abs(ewma([5, 5, 5, 5]) - 5) < 1e-9);
  assert.ok(ewmaVol([5, 5, 5, 5]) < 1e-9, 'flat → no volatility');
  assert.ok(ewmaVol([1, 5, 1, 5, 1]) > 1, 'jumps → volatility');
});

test('standard error shrinks like 1/√n; the CI brackets the true mean', () => {
  const small = normalSeries(25, 10, 2, 7), big = normalSeries(400, 10, 2, 7);
  assert.ok(standardError(big) < standardError(small), 'more samples → tighter SE');
  const ci = confidenceInterval(big);
  assert.ok(ci.lo < 10 && ci.hi > 10, '95% CI contains the true mean 10');
});

test('Kalman converges to a constant under noise and shrinks its variance', () => {
  const kf = new Kalman({ q: 1e-5, r: 0.25 });
  const noise = normalSeries(200, 0, 0.5, 99);
  let last;
  for (let i = 0; i < noise.length; i++) last = kf.update(7 + noise[i]);
  assert.ok(Math.abs(last.x - 7) < 0.2, `estimate ${last.x.toFixed(3)} ≈ 7`);
  assert.ok(last.p < 0.25, 'estimate variance fell below the measurement noise');
});

test('Kalman-smoothed track is tighter than the raw measurements (accuracy gain)', () => {
  const truth = 220, noise = normalSeries(300, 0, 6, 3);
  const kf = new Kalman({ q: 1e-3, r: 6 });
  const raw = [], smooth = [];
  for (let i = 0; i < noise.length; i++) { const z = truth + noise[i]; raw.push(z); smooth.push(kf.update(z).x); }
  // compare error variance of the second half (after convergence)
  const err = (a) => variance(a.slice(150).map((v) => v - truth), false);
  assert.ok(err(smooth) < err(raw), `smoothed error var ${err(smooth).toFixed(2)} < raw ${err(raw).toFixed(2)}`);
});

test('jitter/shimmer are ~0 for a perfectly steady track and rise with perturbation', () => {
  assert.ok(jitter([200, 200, 200, 200]) < 1e-9, 'steady pitch → no jitter');
  assert.ok(jitter([200, 203, 199, 202, 198]) > 0, 'wobbling pitch → jitter');
  assert.ok(shimmer([0.5, 0.5, 0.5]) < 1e-9);
  assert.ok(relativePerturbation([1, 1.1, 0.9, 1.05]) > 0);
});

test('Bollinger bands centre on the mean and widen with volatility', () => {
  const calm = bollinger([10, 10, 10, 10], 2), wild = bollinger([10, 14, 6, 13, 7], 2);
  assert.ok(Math.abs(calm.mid - 10) < 1e-6 && calm.width < 1e-6, 'flat → zero-width band');
  assert.ok(wild.width > calm.width, 'volatile → wider band');
  assert.ok(wild.upper > wild.mid && wild.lower < wild.mid);
});

test('z-score + outliers flag a spliced-in anomaly', () => {
  const x = [1, 1.1, 0.9, 1.05, 0.95, 1.0, 9.0, 1.1, 0.9]; // index 6 is the splice
  assert.ok(Math.abs(zScore(9, mean(x), stddev(x))) > 2);
  assert.deepEqual(outliers(x, 2), [6]);
  assert.deepEqual(outliers([1, 1, 1, 1], 3), [], 'no variance → no outliers');
});

test('autocorrelation is high for a smooth ramp and ~0 for alternating noise', () => {
  const ramp = Array.from({ length: 64 }, (_, i) => i);
  assert.ok(autocorr(ramp, 1) > 0.9, 'persistent series');
  const alt = Array.from({ length: 64 }, (_, i) => (i % 2 ? 1 : -1));
  assert.ok(autocorr(alt, 1) < 0, 'anti-correlated at lag 1');
});

test('EVM 18-dp: strings carry exactly 18 fractional digits, sign preserved, carry-safe', () => {
  assert.equal(toFixed18Str(220.14), '220.140000000000000000');
  assert.equal(toFixed18Str(-0.5), '-0.500000000000000000');
  assert.equal(toFixed18Str(0), '0.000000000000000000');
  assert.equal(toFixed18Str(0.9999999999), '1.000000000000000000', 'rounds up with carry into the whole');
  for (const s of ['220.140000000000000000', '-0.500000000000000000']) {
    const [, frac] = s.replace('-', '').split('.'); assert.equal(frac.length, 18, 'always 18 decimals');
  }
});

test('toFixed18 matches the faceprint convention and round-trips', () => {
  assert.equal(toFixed18(1), ONE18, '1.0 → 1e18');
  assert.ok(Math.abs(fromFixed18(toFixed18(3.14159)) - 3.14159) < 1e-6, 'round-trips to ~9 decimals');
  assert.equal(toFixed18(-5), 0n, 'clamps negatives like faceprint');
});

test('accuracy18 bundles the readout at 18-dp with the sign kept', () => {
  const a = accuracy18({ f0: 220.14, ci: 0.83, jitter: 0.012, shimmer: 0.04, clarity: 0.91 });
  assert.equal(a.f0_hz, '220.140000000000000000');
  assert.equal(a.ci95_hz, '0.830000000000000000');
  assert.equal(a.jitter_pct, '1.200000000000000000');
  assert.equal(a.precision_decimals, 18);
});

console.log(`\nfinmeasure: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
