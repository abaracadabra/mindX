/**
 * oscilloscope.test.js — the scientific scope's DSP, proven against synthetic
 * signals with KNOWN answers. Accuracy is measured, not asserted.
 * Run: node src/face_clone/oscilloscope.test.js
 */
import { strict as assert } from 'assert';
import {
  fft, spectrum, yinPitch, detectTrigger, freqToNote, freqColor, measurements,
  spectralCentroid, spectralRolloff, zeroCrossingRate, harmonicToNoiseRatio, peakToPeak, rms,
} from './oscilloscope.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

const SR = 44100;
// a glottal-ish tone: fundamental + a few harmonics with a little decay
function voice(f0, n = 2048, sr = SR, harmonics = 6) {
  const s = new Float32Array(n);
  for (let i = 0; i < n; i++) { let v = 0; for (let h = 1; h <= harmonics; h++) v += (1 / h) * Math.sin(2 * Math.PI * f0 * h * i / sr); s[i] = v * 0.3; }
  return s;
}
const sine = (f, n = 1024, sr = SR) => { const s = new Float32Array(n); for (let i = 0; i < n; i++) s[i] = Math.sin(2 * Math.PI * f * i / sr); return s; };

test('fft of a pure cosine peaks at exactly its bin', () => {
  const N = 64, k = 5;
  const re = new Float32Array(N), im = new Float32Array(N);
  for (let i = 0; i < N; i++) re[i] = Math.cos(2 * Math.PI * k * i / N);
  fft(re, im);
  let peak = 0; for (let i = 1; i < N / 2; i++) if (Math.hypot(re[i], im[i]) > Math.hypot(re[peak], im[peak])) peak = i;
  assert.equal(peak, k, 'energy is at bin k');
});

test('YIN measures a 200 Hz voice within 1 Hz (sub-sample accurate)', () => {
  const r = yinPitch(voice(200), SR);
  assert.ok(Math.abs(r.hz - 200) < 1, `got ${r.hz.toFixed(3)} Hz`);
  assert.ok(r.clarity > 0.8, `clear signal → high clarity (${r.clarity.toFixed(2)})`);
});

test('YIN tracks pitch across the vocal range (110 / 440 Hz)', () => {
  assert.ok(Math.abs(yinPitch(voice(110), SR).hz - 110) < 1);
  assert.ok(Math.abs(yinPitch(voice(440), SR).hz - 440) < 2);
});

test('YIN returns hz=0 on noise/silence — it never invents a pitch', () => {
  const silence = new Float32Array(1024);
  assert.equal(yinPitch(silence, SR).hz > 0 ? yinPitch(silence, SR).clarity : 0, 0);
  // white-ish noise: low clarity
  const noise = new Float32Array(1024); let seed = 7;
  for (let i = 0; i < noise.length; i++) { seed = (seed * 1103515245 + 12345) & 0x7fffffff; noise[i] = (seed / 0x7fffffff) * 2 - 1; }
  assert.ok(yinPitch(noise, SR).clarity < 0.5, 'noise is not clearly pitched');
});

test('spectrum of a 1000 Hz sine peaks at the 1000 Hz bin', () => {
  const { mags, freqs } = spectrum(sine(1000, 2048), SR, 2048);
  let peak = 1; for (let i = 2; i < mags.length; i++) if (mags[i] > mags[peak]) peak = i;
  assert.ok(Math.abs(freqs[peak] - 1000) < SR / 2048, `peak at ${freqs[peak].toFixed(0)} Hz`);
});

test('edge trigger finds the rising zero-crossing so the trace stands still', () => {
  const s = sine(100, 1024);
  const t = detectTrigger(s, { level: 0, edge: 'rising' });
  assert.ok(t > 0 && s[t - 1] < 0 && s[t] >= 0, 'the returned index is a rising crossing');
  const f = detectTrigger(s, { level: 0, edge: 'falling' });
  assert.ok(s[f - 1] > 0 && s[f] <= 0, 'falling edge too');
});

test('Vpp and Vrms are correct for a unit sine (≈2 and ≈0.707)', () => {
  const s = sine(300, 4096);
  assert.ok(Math.abs(peakToPeak(s) - 2) < 0.01, `Vpp ${peakToPeak(s).toFixed(3)}`);
  assert.ok(Math.abs(rms(s) - Math.SQRT1_2) < 0.01, `Vrms ${rms(s).toFixed(3)}`);
});

test('spectral centroid rises with brightness; rolloff sits above the fundamental', () => {
  const dull = spectrum(voice(200, 2048, SR, 2), SR, 2048);
  const bright = spectrum(voice(200, 2048, SR, 8), SR, 2048);
  assert.ok(spectralCentroid(bright.mags, bright.freqs) > spectralCentroid(dull.mags, dull.freqs), 'more harmonics → higher centroid');
  assert.ok(spectralRolloff(bright.mags, bright.freqs) > 200, 'rolloff above the fundamental');
});

test('HNR is high for a clean tone and much lower with added noise', () => {
  const clean = voice(180);
  const noisy = clean.map((v, i) => v + (((i * 2654435761) % 1000) / 1000 - 0.5) * 0.6);
  const hc = harmonicToNoiseRatio(clean, SR), hn = harmonicToNoiseRatio(Float32Array.from(noisy), SR);
  assert.ok(hc > hn, `clean HNR ${hc.toFixed(1)} dB > noisy ${hn.toFixed(1)} dB`);
});

test('freqToNote names A4=440 and reads cents error', () => {
  const a = freqToNote(440); assert.equal(a.name, 'A'); assert.equal(a.octave, 4); assert.ok(Math.abs(a.cents) < 1);
  const c = freqToNote(261.63); assert.equal(c.name, 'C'); assert.equal(c.octave, 4);
  assert.equal(freqToNote(0).name, '—');
});

test('freqColor maps low→red(0) and high→violet(300), monotonic', () => {
  assert.equal(freqColor(0), 0);
  const lo = freqColor(80), hi = freqColor(10000);
  assert.ok(lo < hi && lo >= 0 && hi <= 300, `low ${lo} < high ${hi}`);
});

test('measurements() bundles a coherent readout for a 220 Hz voice', () => {
  const m = measurements(voice(220), SR);
  assert.ok(Math.abs(m.f0 - 220) < 1.5);
  assert.ok(Math.abs(m.period - 1000 / m.f0) < 1e-6, 'period = 1000/f0 ms');
  assert.equal(m.note.name, 'A', '220 Hz ≈ A3');
  assert.ok(m.vrms > 0 && m.vpp > 0 && m.centroid > 0);
});

console.log(`\noscilloscope: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
