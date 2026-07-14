/**
 * v3.test.js — the v3 stack: STT (in), noise (signal vs noise), TTS (out),
 * VoiceShaper (voice character). Synthetic signals only, no models, no network.
 */
import assert from 'node:assert/strict';
import {
  STT,
  TTS,
  nativeEngines,
  VoiceShaper,
  pitchShift,
  timeStretch,
  formantShift,
  eq,
  compress,
  deEss,
  snr,
  denoise,
  gate,
  noiseProfile,
  spectralFlatness,
} from '../src/index.js';

let pass = 0;
let fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

const SR = 24000;
/** Voiced harmonic stack (a glottal-source model). */
const voice = (f0, sec, a = 0.35, harm = 12) => {
  const n = Math.round(sec * SR);
  const s = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    let x = 0;
    for (let h = 1; h <= harm; h++) x += Math.sin(2 * Math.PI * f0 * h * t) / h;
    s[i] = (a * x) / 1.6;
  }
  return s;
};
/** speech · silence · speech — what a real utterance stream looks like. */
const utterances = (noiseAmp = 0) => {
  const parts = [voice(120, 1.0), new Float32Array(Math.round(0.6 * SR)), voice(150, 0.8)];
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Float32Array(total);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  if (noiseAmp) for (let i = 0; i < out.length; i++) out[i] += noiseAmp * (Math.random() * 2 - 1);
  return { samples: out, sampleRate: SR };
};
const dominantHz = (s) => {
  // crude zero-crossing pitch estimate — enough to prove a shift happened
  let zc = 0;
  for (let i = 1; i < s.length; i++) if ((s[i - 1] < 0) !== (s[i] < 0)) zc++;
  return (zc / 2) * (SR / s.length);
};

// ── noise: signal vs noise ───────────────────────────────────────────────
await test('snr separates speech from noise and grades the clip', () => {
  const clean = utterances(0);
  const dirty = utterances(0.05);
  const a = snr(clean.samples, SR);
  const b = snr(dirty.samples, SR);
  assert.ok(a.snrDb > b.snrDb, `clean SNR ${a.snrDb.toFixed(1)} > noisy ${b.snrDb.toFixed(1)}`);
  assert.ok(a.frames.voiced > 0 && a.frames.silent > 0, 'finds both speech and silence');
  assert.ok(['clean', 'usable'].includes(a.verdict), `clean clip verdict: ${a.verdict}`);
  assert.ok(b.snrDb < a.snrDb - 10, 'added noise is visible in dB');
});

await test('noiseProfile learns from silence; denoise raises SNR', () => {
  const dirty = utterances(0.04);
  const profile = noiseProfile(dirty.samples, SR);
  assert.ok(profile && profile.spectrum.length > 0, 'profile learned from the silent frames');
  const res = denoise(dirty.samples, SR);
  assert.equal(res.profileUsed, true);
  assert.ok(res.snrAfter.snrDb > res.snrBefore.snrDb, `SNR improved ${res.snrBefore.snrDb.toFixed(1)} → ${res.snrAfter.snrDb.toFixed(1)}`);
  assert.equal(res.samples.length, dirty.samples.length, 'length preserved');
});

await test('denoise refuses to invent a profile when there is no silence', () => {
  const noSilence = voice(120, 1.5); // wall-to-wall speech
  const res = denoise(noSilence, SR);
  assert.equal(res.profileUsed, false);
  assert.match(res.note, /no silent frames/);
  assert.deepEqual(Array.from(res.samples.slice(0, 5)), Array.from(noSilence.slice(0, 5)), 'input returned unchanged');
});

await test('gate silences the floor; flatness separates tone from noise', () => {
  const dirty = utterances(0.02);
  const gated = gate(dirty.samples, SR, { thresholdDb: -35 });
  const silentRegion = (s) => {
    let acc = 0;
    const from = Math.round(1.2 * SR);
    const to = Math.round(1.5 * SR);
    for (let i = from; i < to; i++) acc += s[i] * s[i];
    return Math.sqrt(acc / (to - from));
  };
  assert.ok(silentRegion(gated) < silentRegion(dirty.samples), 'gate quiets the gap');
  const noise = new Float32Array(4096).map(() => Math.random() * 2 - 1);
  assert.ok(spectralFlatness(noise) > spectralFlatness(voice(120, 0.2)), 'noise is flatter than voice');
});

// ── STT ──────────────────────────────────────────────────────────────────
await test('STT reports availability honestly', async () => {
  const stt = new STT();
  const cap = await stt.available();
  assert.equal(typeof cap.any, 'boolean');
  assert.equal(cap.segmentation, true, 'segmentation always available');
  if (!cap.any) assert.ok(cap.hints.length >= 1, 'tells you how to install a recogniser');
});

await test('STT REFUSES to invent a transcript when no recogniser exists', async () => {
  const stt = new STT();
  const cap = await stt.available();
  if (!cap.any) {
    await assert.rejects(() => stt.transcribe(utterances()), /refusing to invent a transcript/);
  } else {
    console.log('   (a recogniser is installed here — refusal path not exercised)');
  }
});

await test('STT segments utterances with timings, energy and SNR', () => {
  const stt = new STT();
  const res = stt.segment(utterances());
  assert.equal(res.segments.length, 2, 'two utterances around one gap');
  assert.ok(res.segments[0].endSec < res.segments[1].startSec, 'ordered, non-overlapping');
  assert.ok(res.segments[0].durationSec > 0.5);
  assert.ok(res.speechSec < res.totalSec, 'speech is less than the whole clip');
  assert.match(res.note, /not a transcript/, 'never claims to be transcription');
});

// ── TTS ──────────────────────────────────────────────────────────────────
await test('TTS capability lists real paths; formant floor always present', async () => {
  const tts = new TTS();
  const cap = await tts.capability();
  assert.equal(cap.formant, true, 'the in-house floor is unconditional');
  assert.ok(Array.isArray(cap.native));
  assert.ok(cap.resolved, `resolves to something: ${cap.resolved}`);
  assert.deepEqual(cap.native, nativeEngines().map((e) => e.name));
});

await test('TTS always speaks — even with no engine on the host', async () => {
  const tts = new TTS({ engine: 'formant', sampleRate: SR });
  const clip = await tts.speak('the machine speaks for itself');
  assert.ok(clip.samples.length > 0, 'produced audio');
  assert.equal(clip.sampleRate, SR);
  assert.equal(clip.engine, 'formant', 'and says which engine made it');
  let peak = 0;
  for (const v of clip.samples) peak = Math.max(peak, Math.abs(v));
  assert.ok(peak > 0.001, 'audible, not a silent buffer');
});

await test('TTS rejects empty text rather than emitting silence', async () => {
  await assert.rejects(() => new TTS().speak('   '), /nothing to speak/);
});

// ── VoiceShaper ──────────────────────────────────────────────────────────
await test('pitchShift moves pitch and preserves duration', () => {
  const clip = { samples: voice(120, 1.0), sampleRate: SR };
  const up = pitchShift(clip, 7); // a fifth up
  assert.ok(Math.abs(up.samples.length - clip.samples.length) <= 2, 'duration held');
  assert.ok(dominantHz(up.samples) > dominantHz(clip.samples) * 1.2, 'pitch clearly rose');
  const down = pitchShift(clip, -7);
  assert.ok(dominantHz(down.samples) < dominantHz(clip.samples) * 0.9, 'pitch clearly fell');
});

await test('timeStretch changes duration and preserves pitch', () => {
  const clip = { samples: voice(120, 1.0), sampleRate: SR };
  const slow = timeStretch(clip, 1.5);
  assert.ok(Math.abs(slow.samples.length / clip.samples.length - 1.5) < 0.05, 'duration ×1.5');
  const before = dominantHz(clip.samples);
  const after = dominantHz(slow.samples);
  assert.ok(Math.abs(after - before) / before < 0.25, `pitch held (${before.toFixed(0)} → ${after.toFixed(0)} Hz)`);
});

await test('formantShift changes timbre without changing duration', () => {
  const clip = { samples: voice(120, 1.0), sampleRate: SR };
  const bigger = formantShift(clip, 1.15);
  assert.equal(bigger.samples.length, clip.samples.length, 'length identical');
  let diff = 0;
  for (let i = 0; i < clip.samples.length; i++) diff += Math.abs(bigger.samples[i] - clip.samples[i]);
  assert.ok(diff / clip.samples.length > 1e-4, 'the timbre actually moved');
});

await test('eq shapes the spectrum; compress evens the dynamics', () => {
  const clip = { samples: voice(120, 0.5), sampleRate: SR };
  const cut = eq(clip, { type: 'lowpass', freq: 300, q: 0.707 });
  const energy = (s) => s.reduce((a, v) => a + v * v, 0);
  assert.ok(energy(cut.samples) < energy(clip.samples), 'lowpass removes harmonic energy');
  const boosted = eq(clip, { type: 'peaking', freq: 3000, gainDb: 9, q: 1 });
  assert.ok(energy(boosted.samples) > energy(cut.samples), 'peaking adds where it is aimed');

  const loud = { samples: Float32Array.from(voice(120, 0.5), (v, i) => v * (i < 6000 ? 2.4 : 0.15)), sampleRate: SR };
  const comp = compress(loud, { thresholdDb: -20, ratio: 4 });
  const seg = (s, a, b) => Math.sqrt(s.slice(a, b).reduce((x, v) => x + v * v, 0) / (b - a));
  const before = seg(loud.samples, 0, 5000) / (seg(loud.samples, 8000, 11000) + 1e-9);
  const after = seg(comp.samples, 0, 5000) / (seg(comp.samples, 8000, 11000) + 1e-9);
  assert.ok(after < before, `dynamic range reduced (${before.toFixed(1)} → ${after.toFixed(1)})`);
});

await test('deEss tames the sibilance band', () => {
  const base = voice(120, 0.5);
  const sibilant = Float32Array.from(base, (v, i) => v + 0.25 * Math.sin(2 * Math.PI * 7000 * (i / SR)));
  const tamed = deEss({ samples: sibilant, sampleRate: SR }, { amount: 0.8 });
  const hf = (s) => {
    const f = eq({ samples: s, sampleRate: SR }, { type: 'highpass', freq: 6000, q: 0.707 });
    return f.samples.reduce((a, v) => a + v * v, 0);
  };
  assert.ok(hf(tamed.samples) < hf(sibilant), 'sibilance reduced');
});

await test('VoiceShaper chains and undoes', () => {
  const s = new VoiceShaper({ samples: voice(120, 0.5), sampleRate: SR });
  const base = dominantHz(s.clip.samples);
  s.pitchShift(-4).formantShift(0.95).compress({ thresholdDb: -18, ratio: 3 });
  assert.ok(dominantHz(s.clip.samples) < base, 'chain applied');
  s.undo().undo().undo();
  assert.ok(Math.abs(dominantHz(s.clip.samples) - base) < 1, 'back to the original');
  assert.ok(s.canRedo);
  s.redo();
  assert.ok(s.canUndo);
});

console.log(`\nv3 suite: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
