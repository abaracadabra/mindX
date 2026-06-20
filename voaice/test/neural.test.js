/**
 * neural.test.js — NeuralVoiceEngine + WAV codec, dependency-free.
 *
 * Runs with zero model weights and no onnxruntime-node: exercises the fallback path so the
 * whole pipeline is verifiable offline / in CI. When real weights are present the same calls
 * transparently use the neural backend (asserted via `.backend`). Pure node:assert, no deps.
 *
 *   node test/neural.test.js   (or: npm test)
 */

import assert from 'node:assert/strict';
import {
  loadNeuralVoiceEngine,
  encodeWav,
  decodeWav,
  integratedLoudness,
  normalizeToLufs,
  trimSilence,
  voicedRatio,
  fanOut,
  toVoiceParams,
  toFace,
  extractTags,
  EMOTION_LABELS,
} from '../src/index.js';
import { FormantTTS } from '../src/tts/formant.js';
import { VoiceAnalyzer } from '../src/VoiceAnalyzer.js';

/** Build a mono sine of `seconds` at `freq`/`amp`. */
function tone(seconds, sr = 24000, freq = 220, amp = 0.5) {
  const n = Math.round(seconds * sr);
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = amp * Math.sin((2 * Math.PI * freq * i) / sr);
  return x;
}

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`  ok   ${name}`);
  } catch (err) {
    console.error(`  FAIL ${name}\n       ${err.message}`);
    process.exitCode = 1;
  }
}

console.log('voaice neural engine');

await test('WAV round-trips Float32 through PCM16', () => {
  const n = 2400;
  const sig = new Float32Array(n);
  for (let i = 0; i < n; i++) sig[i] = Math.sin((2 * Math.PI * 220 * i) / 24000);
  const buf = encodeWav(sig, 24000);
  assert.equal(buf.toString('ascii', 0, 4), 'RIFF');
  const { samples, sampleRate } = decodeWav(buf);
  assert.equal(sampleRate, 24000);
  assert.equal(samples.length, n);
  // PCM16 quantisation error is bounded by ~1 LSB
  let maxErr = 0;
  for (let i = 0; i < n; i++) maxErr = Math.max(maxErr, Math.abs(samples[i] - sig[i]));
  assert.ok(maxErr < 1e-3, `quantisation error too high: ${maxErr}`);
});

await test('loadNeuralVoiceEngine() loads and init() reports capability', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = new NeuralVoiceEngine({ voiceId: 'jaimla' });
  let announced = null;
  eng.on('initialized', (e) => (announced = e));
  await eng.init();
  assert.ok(announced, 'initialized event not emitted');
  assert.equal(typeof eng.capability.ort, 'boolean');
  assert.equal(typeof eng.capability.base, 'boolean');
  assert.equal(typeof eng.capability.clone, 'boolean');
});

await test('synthesize() returns non-empty WAV at the engine sample rate', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = new NeuralVoiceEngine({ voiceId: 'jaimla' });
  await eng.init();
  const out = await eng.synthesize({ text: 'hello, I am jaimla', write: false });
  assert.ok(out.buffer.length > 44, 'WAV has no audio payload');
  assert.equal(out.sampleRate, eng.sampleRate);
  assert.ok(out.samples.length > 0);
  assert.ok(typeof out.backend === 'string' && out.backend.length > 0);
  // decodes back to a valid WAV
  const { samples } = decodeWav(out.buffer);
  assert.ok(samples.length > 0);
});

await test('synthesize() is persona-differentiated (jaimla vs professor pitch)', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = new NeuralVoiceEngine();
  await eng.init();
  // only assert differentiation when running the deterministic fallback source
  if (eng.capability.base) return;
  const a = await eng.synthesize({ text: 'one two three', voiceId: 'jaimla', write: false });
  const b = await eng.synthesize({ text: 'one two three', voiceId: 'professor', write: false });
  assert.notDeepEqual(Array.from(a.samples.subarray(0, 256)), Array.from(b.samples.subarray(0, 256)));
});

await test('cloneFromReference() returns an 18-dp forensic voiceprint', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = new NeuralVoiceEngine();
  await eng.init();
  // synthesise a reference clip, then clone from it
  const ref = await eng.synthesize({ text: 'clone my voice please', voiceId: 'jaimla', write: false });
  const clone = await eng.cloneFromReference({ buffer: ref.buffer });
  assert.ok(clone.voiceprint, 'no voiceprint');
  assert.match(clone.voiceprint.hash, /^0x[0-9a-f]{64}$/);
  assert.equal(clone.voiceprint.measures.length, 6);
  for (const m of clone.voiceprint.measures) assert.equal(typeof m, 'bigint');
  // embedding/embeddingId only when tone-color weights are present
  if (eng.capability.clone) {
    assert.ok(clone.embeddingId && clone.embeddingId.startsWith('0x'));
    assert.ok(clone.embedding instanceof Float32Array);
  } else {
    assert.equal(clone.backend, 'voiceprint-only');
  }
});

await test('torch-free invariant: no module imports torch/transformers/python deps', async () => {
  // The neural engine must never IMPORT torch/transformers/python bindings (CPU/ONNX only).
  // Inspect import specifiers across the neural source — ignore prose/comments.
  const { readFileSync, readdirSync } = await import('node:fs');
  const forbidden = /^(torch|transformers|onnxruntime-web|python-shell|pythonia)/i;
  const files = [
    '../src/NeuralVoiceEngine.js',
    '../src/g2p.js',
    ...readdirSync(new URL('../src/audio/', import.meta.url)).map((f) => `../src/audio/${f}`),
    ...readdirSync(new URL('../src/onnx/', import.meta.url)).map((f) => `../src/onnx/${f}`),
  ];
  for (const rel of files) {
    const src = readFileSync(new URL(rel, import.meta.url), 'utf8');
    const specs = [...src.matchAll(/(?:^|\n)\s*import[^'"]*['"]([^'"]+)['"]/g)].map((m) => m[1]);
    for (const s of specs) {
      assert.ok(!forbidden.test(s), `forbidden import "${s}" in ${rel}`);
    }
  }
});

await test('LUFS: normalizeToLufs converges to the target', () => {
  const sr = 24000;
  const x = tone(2, sr, 220, 0.5);
  const before = integratedLoudness(x, sr);
  assert.ok(isFinite(before), 'loudness should be finite for a tone');
  const norm = normalizeToLufs(x, sr, -23);
  const after = integratedLoudness(norm, sr);
  assert.ok(Math.abs(after - -23) < 0.5, `expected ~-23 LUFS, got ${after.toFixed(2)}`);
});

await test('VAD: trimSilence removes lead/trail silence and raises voiced ratio', () => {
  const sr = 24000;
  const sil = new Float32Array(sr / 2); // 0.5s silence each side
  const speech = tone(1, sr, 180, 0.4);
  const y = new Float32Array(sil.length + speech.length + sil.length);
  y.set(speech, sil.length);
  const t = trimSilence(y, sr);
  assert.ok(t.trimmed, 'should report trimming');
  assert.ok(t.samples.length < y.length, 'trimmed clip should be shorter');
  assert.ok(voicedRatio(t.samples, sr) > voicedRatio(y, sr), 'voiced ratio should increase');
});

await test('output is loudness-normalised to the engine target', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = new NeuralVoiceEngine({ voiceId: 'jaimla', targetLufs: -20 });
  await eng.init();
  const out = await eng.synthesize({ text: 'level check one two', write: false });
  const lufs = integratedLoudness(out.samples, out.sampleRate);
  // fallback tone is long/steady enough to gate; neural backends also pass through normalize
  if (isFinite(lufs)) assert.ok(Math.abs(lufs - -20) < 1.0, `expected ~-20 LUFS, got ${lufs.toFixed(2)}`);
});

await test('capability exposes the resolved backend', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = await new NeuralVoiceEngine().init();
  assert.ok(['sherpa', 'onnx', 'fallback'].includes(eng.capability.backend));
  assert.equal(typeof eng.capability.sherpa, 'boolean');
  // with no weights present here, backend must resolve to fallback
  if (!eng.capability.base && !eng.capability.clone) {
    assert.equal(eng.capability.backend, 'fallback');
  }
});

await test('clone stores a profile and reports needsText honestly', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = await new NeuralVoiceEngine().init();
  const ref = await eng.synthesize({ text: 'reference clip for cloning', voiceId: 'jaimla', write: false });
  const clone = await eng.cloneFromReference({ buffer: ref.buffer, text: 'reference clip for cloning' });
  assert.match(clone.voiceprint.hash, /^0x[0-9a-f]{64}$/);
  assert.equal(typeof clone.needsText, 'boolean');
  // no clone weights here → voiceprint-only, null id, never demands a transcript
  if (clone.backend === 'voiceprint-only') {
    assert.equal(clone.embeddingId, null);
    assert.equal(clone.needsText, false);
  }
});

await test('emotion: fan-out scales exaggeration by intensity (Chatterbox-shaped)', () => {
  assert.ok(EMOTION_LABELS.includes('happy') && EMOTION_LABELS.includes('angry'));
  // neutral at any intensity → 0.5 exaggeration baseline
  assert.ok(Math.abs(toVoiceParams({ label: 'neutral', intensity: 1 }).exaggeration - 0.5) < 1e-9);
  // intensity 0 collapses any emotion to neutral exaggeration
  assert.ok(Math.abs(toVoiceParams({ label: 'angry', intensity: 0 }).exaggeration - 0.5) < 1e-9);
  // higher intensity → more exaggeration for an intense emotion
  const lo = toVoiceParams({ label: 'angry', intensity: 0.4 }).exaggeration;
  const hi = toVoiceParams({ label: 'angry', intensity: 0.9 }).exaggeration;
  assert.ok(hi > lo && hi <= 1.2, `angry exaggeration should rise with intensity (${lo}→${hi})`);
});

await test('emotion: toFace maps to a faicey expression + weight', () => {
  const f = toFace({ label: 'sad', intensity: 0.7 });
  assert.equal(f.expression, 'sad');         // matches faicey vocabulary
  assert.ok(Math.abs(f.weight - 0.7) < 1e-9);
  assert.equal(typeof f.hue, 'number');
  assert.equal(toFace('happy').expression, 'happy');
  assert.equal(toFace('nonsense').expression, 'neutral'); // unknown → neutral
});

await test('emotion: extractTags pulls paralinguistic tags, cleans text', () => {
  const { clean, tags } = extractTags('That is so funny! [laugh] ahem [cough] [bogus]');
  assert.equal(tags.length, 2);
  assert.deepEqual(tags.map(t => t.tag), ['laugh', 'cough']);
  assert.ok(!/\[laugh\]|\[cough\]/.test(clean));
  assert.match(clean, /\[bogus\]/);          // non-paralinguistic brackets are left untouched
});

await test('synthesize attaches the emotion fan-out + emits speechGenerated', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = await new NeuralVoiceEngine({ voiceId: 'jaimla' }).init();
  let evt = null;
  eng.on('speechGenerated', (e) => (evt = e));
  const out = await eng.synthesize({ text: 'wonderful news [laugh]', emotion: { label: 'happy', intensity: 0.9 }, write: false });
  assert.equal(out.emotion.label, 'happy');
  assert.equal(out.emotion.face.expression, 'happy');
  assert.ok(out.emotion.voice.exaggeration > 0.5); // happy raises exaggeration
  assert.equal(out.tags.length, 1);
  assert.equal(out.tags[0].tag, 'laugh');
  assert.ok(evt && evt.emotion.face.expression === 'happy', 'speechGenerated should carry the emotion');
  assert.equal(typeof evt.duration, 'number');
});

await test('formant TTS: model-free real speech (varied + tonal formant structure)', () => {
  const tts = new FormantTTS({ sampleRate: 24000, f0: 120 });
  const hello = tts.synthesize('hello world');
  assert.ok(hello.length > 24000 * 0.3, 'utterance has plausible duration');
  let e = 0; for (let i = 0; i < hello.length; i++) e += hello[i] * hello[i];
  assert.ok(Math.sqrt(e / hello.length) > 0.05, 'has audible energy');
  // distinct words → distinct signals (not a fixed tone)
  const a = tts.synthesize('hello'), b = tts.synthesize('different');
  let diff = 0, n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) diff += Math.abs(a[i] - b[i]);
  assert.ok(diff / n > 0.02, 'distinct words produce distinct audio');
  // a sustained vowel is tonal (low spectral flatness) — formant, not noise/tone-flat
  const va = new VoiceAnalyzer({ sampleRate: 24000, fftSize: 2048 });
  const f = va.analyze(tts.synthesize('aaaa').subarray(2000, 4048));
  assert.ok(f.flatness < 0.2, `vowel should be tonal/formant (flatness ${f.flatness.toFixed(3)})`);
});

await test('engine speaks via formant (real speech) when no neural model present', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = await new NeuralVoiceEngine({ voiceId: 'jaimla' }).init();
  assert.equal(eng.capability.formant, true);
  if (!eng.capability.base) {
    assert.equal(eng.capability.backend, 'formant', 'model-free path should be formant, not the tone fallback');
    const out = await eng.synthesize({ text: 'speak for real', write: false });
    assert.equal(out.backend, 'formant');
    assert.ok(out.samples.length > 24000 * 0.2);
  }
});

await test('formant honors persona pitch (jaimla vs professor differ)', async () => {
  const NeuralVoiceEngine = await loadNeuralVoiceEngine();
  const eng = await new NeuralVoiceEngine().init();
  if (eng.capability.backend !== 'formant') return;
  const j = await eng.synthesize({ text: 'one two three', voiceId: 'jaimla', write: false });
  const p = await eng.synthesize({ text: 'one two three', voiceId: 'professor', write: false });
  assert.notDeepEqual(Array.from(j.samples.subarray(2000, 2050)), Array.from(p.samples.subarray(2000, 2050)));
});

console.log(`\n${passed} passed`);
