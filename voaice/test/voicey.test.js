/**
 * voicey.test.js — FAST suite for the forensic / editor / exporter layer.
 * Synthetic signals only: no models, no network, no onnxruntime. Runs in
 * well under a second — this is the default `npm run test:fast`.
 */
import assert from 'node:assert/strict';
import { unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  Forensic,
  AudioEditor,
  slice,
  concat,
  gain,
  normalize,
  resample,
  exportClip,
  toWav,
  QUALITY,
  oggAvailable,
  decodeWav,
  encodeWav,
} from '../src/index.js';

let passed = 0;
let failed = 0;
const test = async (name, fn) => {
  try {
    await fn();
    passed++;
    console.log(`✅ ${name}`);
  } catch (e) {
    failed++;
    console.error(`❌ ${name}: ${e.message}`);
  }
};

const SR = 24000;
/** Voiced-ish test tone: fundamental + harmonics + vibrato, amplitude a. */
const voice = (f0, seconds = 1.2, a = 0.4) => {
  const n = Math.round(seconds * SR);
  const s = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const vib = 1 + 0.005 * Math.sin(2 * Math.PI * 5 * t);
    s[i] =
      a *
      (Math.sin(2 * Math.PI * f0 * vib * t) +
        0.5 * Math.sin(2 * Math.PI * 2 * f0 * vib * t) +
        0.25 * Math.sin(2 * Math.PI * 3 * f0 * vib * t)) / 1.75;
  }
  return s;
};

// ── forensic ────────────────────────────────────────────────────────────
await test('voiceprint is reproducible and 18-dp registered', () => {
  const f = new Forensic({ sampleRate: SR });
  const a = f.voiceprint(voice(120));
  const b = f.voiceprint(voice(120));
  assert.equal(a.hash, b.hash, 'same signal → same print hash');
  assert.equal(a.measuresStr.length, 6, 'six 18-dp registers');
  assert.ok(a.framesUsed > 4, 'aggregates over multiple frames');
});

await test('compare: same voice matches, different voice does not', () => {
  const f = new Forensic({ sampleRate: SR });
  const a = f.voiceprint(voice(120));
  const a2 = f.voiceprint(voice(122)); // tiny pitch drift, same speaker-ish
  const b = f.voiceprint(voice(340, 1.2, 0.15)); // very different voice
  const same = Forensic.compare(a, a2);
  const diff = Forensic.compare(a, b);
  assert.ok(same.similarity > diff.similarity, 'similar > different');
  assert.ok(same.similarity >= 0.75, `same-ish verdict band (got ${same.similarity.toFixed(3)})`);
});

await test('integrity: clean tone is clean, spliced tone is flagged', () => {
  const f = new Forensic({ sampleRate: SR });
  const clean = f.integrity(voice(120));
  assert.equal(clean.verdict, 'clean');
  // splice: hard amplitude jump mid-signal
  const spliced = voice(120);
  for (let i = Math.floor(spliced.length / 2); i < spliced.length; i++) spliced[i] *= 0.05;
  const rep = f.integrity(spliced);
  assert.ok(rep.events.length >= 1, 'discontinuity event detected');
  assert.equal(rep.verdict, 'review');
});

await test('custody records chain by hash', () => {
  const f = new Forensic({ sampleRate: SR });
  const r1 = f.custody(voice(120), { note: 'capture' });
  const r2 = f.custody(voice(120), { note: 'after-edit', prev: r1.recordHash });
  assert.ok(r1.contentHash.startsWith('0x') && r1.recordHash.startsWith('0x'));
  assert.equal(r2.prev, r1.recordHash, 'chain links');
});

// ── editor ──────────────────────────────────────────────────────────────
await test('editor: trim/cut/concat/gain/normalize/resample are sane', () => {
  const clip = { samples: voice(120, 2.0), sampleRate: SR };
  assert.equal(Math.round(slice(clip, 0.5, 1.5).samples.length / SR * 10), 10, 'trim → 1.0s');
  const g = gain(clip, -6);
  assert.ok(Math.abs(g.samples[1000]) < Math.abs(clip.samples[1000]), 'gain attenuates');
  const n = normalize(clip, { mode: 'peak', peakDb: -1 });
  const peakVal = Math.max(...n.samples.map(Math.abs));
  assert.ok(Math.abs(peakVal - 10 ** (-1 / 20)) < 0.01, 'peak lands on target');
  const r = resample(clip, 48000);
  assert.equal(r.sampleRate, 48000);
  assert.ok(Math.abs(r.samples.length - clip.samples.length * 2) < 4, 'length scales');
  const joined = concat([clip, r]);
  assert.equal(joined.sampleRate, SR, 'concat resamples to first rate');
});

await test('editor session: chain + undo/redo', () => {
  const ed = new AudioEditor({ samples: voice(120, 2.0), sampleRate: SR });
  const len0 = ed.clip.samples.length;
  ed.trim(0, 1.0).fadeIn(0.05).fadeOut(0.05).gain(-3);
  assert.ok(ed.clip.samples.length < len0, 'edits applied');
  assert.equal(ed.clip.samples[0], 0, 'fadeIn zeroes the first sample');
  const afterLen = ed.clip.samples.length;
  ed.undo().undo();
  assert.ok(ed.canRedo, 'redo available after undo');
  ed.redo().redo();
  assert.equal(ed.clip.samples.length, afterLen, 'redo restores');
});

// ── exporter ────────────────────────────────────────────────────────────
await test('wav export honors quality tiers and roundtrips', () => {
  const clip = { samples: voice(120), sampleRate: SR };
  for (const tier of Object.keys(QUALITY)) {
    const { buffer, settings } = toWav(clip, { quality: tier });
    const dec = decodeWav(buffer);
    assert.equal(dec.sampleRate, settings.sampleRate, `${tier}: sample rate in header`);
    assert.ok(dec.samples.length > 0, `${tier}: decodes`);
  }
  // 24-bit roundtrip precision beats 16-bit
  const b16 = decodeWav(encodeWav(clip.samples, SR, { bitDepth: 16 })).samples;
  const b24 = decodeWav(encodeWav(clip.samples, SR, { bitDepth: 24 })).samples;
  const err = (dec) => {
    let e = 0;
    for (let i = 0; i < 2000; i++) e += Math.abs(dec[i] - clip.samples[i]);
    return e;
  };
  assert.ok(err(b24) < err(b16), '24-bit quantisation error < 16-bit');
});

await test('exportClip writes a wav file', async () => {
  const path = join(tmpdir(), `voaice-test-${process.pid}.wav`);
  const out = await exportClip({ samples: voice(120), sampleRate: SR }, { format: 'wav', quality: 'medium', path });
  assert.equal(out.format, 'wav');
  assert.ok(out.bytes > 44, 'non-trivial bytes');
  await unlink(path);
});

await test('ogg export works when ffmpeg is present (else honest error)', async () => {
  const clip = { samples: voice(120, 0.5), sampleRate: SR };
  if (oggAvailable()) {
    const out = await exportClip(clip, { format: 'ogg', quality: 'medium' });
    assert.equal(out.buffer.toString('ascii', 0, 4), 'OggS', 'OGG magic');
  } else {
    await assert.rejects(() => exportClip(clip, { format: 'ogg' }), /ffmpeg not found/);
    console.log('   (ffmpeg absent — verified the honest error path)');
  }
});

console.log(`\nvoicey suite: ${passed} passed, ${failed} failed`);
if (failed) process.exit(1);
