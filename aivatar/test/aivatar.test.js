/**
 * aivatar.test.js — the doctrine under test.
 *
 * These tests exist to prove the ONE claim the whole package rests on: a
 * persona carries the tier it EARNED, never the tier it was asked for. If any
 * of these fail, the tool is lying, and a lying provenance tool is worse than
 * no tool at all.
 *
 * Runs offline, no models: synthetic landmarks + synthetic audio.
 */
import assert from 'node:assert/strict';
import { unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  PersonaStudio,
  MODES,
  grade,
  resolveMode,
  validate,
  upgrade,
  consent,
  manifest,
  signManifest,
  appendCustody,
  verify,
  faceRmse,
} from '../src/index.js';

let pass = 0;
let fail = 0;
const test = async (name, fn) => {
  try {
    await fn();
    pass++;
    console.log(`✅ ${name}`);
  } catch (e) {
    fail++;
    console.error(`❌ ${name}: ${e.message}`);
  }
};

// ── fixtures ────────────────────────────────────────────────────────────
const SR = 24000;
/**
 * A voiced-speech model: a harmonic stack (1/h rolloff), which is what a glottal
 * source actually looks like. `harm: 2` is a poor, breathy-measuring voice; 12 is
 * a clean, richly-voiced one. The tier gates are calibrated for real voice, so the
 * fixture has to BE one — we do not relax gates to fit a bad fixture.
 */
const tone = (f0, sec = 40, a = 0.35, harm = 12) => {
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
const clip = (f0, sec, harm) => ({ samples: tone(f0, sec, 0.35, harm), sampleRate: SR });

/**
 * A REAL capture: speech with pauses, over a low room floor. The pauses matter —
 * they are the only place a noise floor can be measured, which is why a clip
 * trimmed of all silence reports its SNR as *unmeasurable* rather than perfect.
 */
const capture = (f0, sec, { floor = 0.0008, harm = 12 } = {}) => {
  const n = Math.round(sec * SR);
  const s = new Float32Array(n);
  const speech = tone(f0, sec, 0.35, harm);
  const period = Math.round(3.2 * SR);   // ~2.4 s of speech, ~0.8 s of pause
  const speakFor = Math.round(2.4 * SR);
  for (let i = 0; i < n; i++) {
    const inSpeech = i % period < speakFor;
    s[i] = (inSpeech ? speech[i] : 0) + floor * (Math.random() * 2 - 1);
  }
  return { samples: s, sampleRate: SR };
};
const lms = (n = 478, jitter = 0) =>
  Array.from({ length: n }, (_, i) => ({
    x: Math.cos(i) * 0.3 + (jitter ? (Math.sin(i * 7.1) * jitter) : 0),
    y: Math.sin(i) * 0.4 + (jitter ? (Math.cos(i * 3.7) * jitter) : 0),
    z: Math.sin(i * 0.5) * 0.1,
  }));
const faceprint = (h) => ({ hash: h, measuresStr: ['1', '2', '3'], precisionScore: '900000000000000000' });

// ── modes + grading ─────────────────────────────────────────────────────
await test('modes resolve; scientific carries both realism levels', () => {
  assert.equal(resolveMode('basic').gates, null);
  const r = resolveMode('scientific', 'realism');
  const h = resolveMode('scientific', 'hyperrealism');
  assert.ok(h.gates.voiceSimilarity > r.gates.voiceSimilarity, 'hyperrealism is strictly harder');
  assert.ok(h.gates.faceRmse < r.gates.faceRmse);
  assert.equal(MODES.scientific.provenance.consent, 'required');
});

await test('grade earns the tier — hyperreal measurements earn hyperrealism', () => {
  const g = grade({
    faceRmse: 0.003, faceFrames: 40, voiceSimilarity: 0.98, voicePrecision: 0.9,
    voicedRatio: 0.7, referenceSeconds: 180, referenceSnrDb: 42,
    spectralDistance: 0.05, integrityClean: true,
  });
  assert.equal(g.mode, 'scientific');
  assert.equal(g.realism, 'hyperrealism');
  assert.equal(g.failed.length, 0);
});

await test('grade REFUSES to flatter — near-miss falls to the tier below', () => {
  const g = grade({
    faceRmse: 0.008, faceFrames: 20, voiceSimilarity: 0.94, voicePrecision: 0.8,
    voicedRatio: 0.6, referenceSeconds: 60, referenceSnrDb: 27,
    spectralDistance: 0.15, integrityClean: true,
  });
  assert.equal(g.realism, 'realism', 'misses hyperrealism gates → realism');
  const weak = grade({ faceFrames: 3, voiceSimilarity: 0.86, voicePrecision: 0.65, voicedRatio: 0.5, referenceSeconds: 10, referenceSnrDb: 22, faceRmse: 0.015 });
  assert.equal(weak.mode, 'professional');
  const nothing = grade({});
  assert.equal(nothing.mode, 'basic', 'unmeasured earns nothing');
});

await test('unmeasured ≠ passed', () => {
  const g = grade({ faceFrames: 40, voiceSimilarity: 0.99, voicePrecision: 0.9, voicedRatio: 0.7, referenceSeconds: 200, referenceSnrDb: 40, spectralDistance: 0.05, integrityClean: true });
  assert.notEqual(g.realism, 'hyperrealism', 'missing faceRmse must not pass');
  assert.ok(g.failed.some((f) => f.includes('faceRmse')));
});

await test('faceRmse is scale-invariant and rises with distortion', () => {
  const src = lms();
  assert.ok(faceRmse(src, src) < 1e-9, 'identical → ~0');
  const scaled = src.map((p) => ({ x: p.x * 2, y: p.y * 2, z: p.z * 2 }));
  assert.ok(faceRmse(scaled, src) < 1e-9, 'pure scale is not error');
  assert.ok(faceRmse(lms(478, 0.05), src) > faceRmse(lms(478, 0.01), src), 'more jitter, more error');
});

// ── provenance ──────────────────────────────────────────────────────────
await test('provenance: manifest + custody verify, tampering fails loudly', () => {
  const c = consent({ kind: 'self', subject: 'codephreak' });
  let chain = appendCustody([], { action: 'capture', contentHash: '0xaa' });
  chain = appendCustody(chain, { action: 'clone-voice', contentHash: '0xbb' });
  const man = manifest({ persona: { hash: '0xp', label: 'test' }, mode: 'professional', consent: c, custody: chain });
  const v = verify(man, chain);
  assert.ok(v.ok, `clean chain verifies: ${v.errors.join(',')}`);
  assert.equal(v.signed, false, 'unsigned reported honestly');

  const tampered = { ...man, declaration: 'AUTHENTIC RECORDING' }; // the exact lie we must catch
  assert.equal(verify(tampered, chain).ok, false, 'tampered manifest must fail');

  const brokenChain = [...chain];
  brokenChain[1] = { ...brokenChain[1], contentHash: '0xcc' };
  assert.equal(verify(man, brokenChain).ok, false, 'broken custody must fail');
});

await test('signed manifest reports its signer', async () => {
  const man = manifest({ persona: { hash: '0xp' }, mode: 'scientific', realism: 'realism' });
  const signed = await signManifest(man, (h) => '0xsig' + h.slice(2, 10), '0xbankon');
  assert.ok(signed.signature.startsWith('0xsig'));
  const v = verify(signed, []);
  assert.ok(v.ok && v.signed && v.signer === '0xbankon');
});

// ── schema ──────────────────────────────────────────────────────────────
await test('v1 cognitive .persona upgrades to v2 without loss', () => {
  const v1 = {
    name: 'CEO', agent_id: 'ceo_main', role: 'executive',
    behavioral_traits: ['decisive'], beliefs: { code_is_law: true },
    inference: { local_model: 'qwen3:0.6b' }, authority: { tier: 'sovereign' },
  };
  const p = upgrade(v1);
  assert.equal(p.kind, 'aivatar-persona');
  assert.equal(p.identity.name, 'CEO');
  assert.deepEqual(p.cognition.beliefs, { code_is_law: true });
  assert.equal(p.cognition.inference.local_model, 'qwen3:0.6b');
  assert.equal(p.cognition.authority.tier, 'sovereign');
});

await test('validate rejects an unearned claim and a missing consent', () => {
  const p = upgrade({ name: 'Liar' });
  p.fidelity = { mode: 'scientific', realism: 'hyperrealism', measured: {}, graded: { mode: 'basic', realism: null, failed: ['faceRmse'] } };
  p.embodiment.face = { faceprint: faceprint('0xf') };
  const v = validate(p);
  assert.equal(v.ok, false);
  assert.ok(v.errors.some((e) => e.includes('was not earned')), 'unearned tier rejected');
  assert.ok(v.errors.some((e) => e.includes('consent')), 'missing consent rejected');
});

// ── studio end-to-end ───────────────────────────────────────────────────
await test('studio: synthetic persona, basic tier, no consent theatre', async () => {
  const s = new PersonaStudio({ mode: 'basic' });
  s.identity({ name: 'Jaimla', description: 'I am the machine learning agent.', behavioral_traits: ['curious'] })
    .consent({ kind: 'synthetic' })
    .face({ faceprint: faceprint('0xface'), landmarks: lms(), frames: 1, source: 'single' });
  await s.voice({ referenceClip: clip(120, 3) });
  s.rig();
  const { persona, graded, downgraded } = await s.stamp();
  assert.equal(graded.mode, 'basic');
  assert.equal(downgraded, false, 'basic was requested and basic was earned');
  assert.ok(persona.hash?.startsWith('0x'));
  assert.equal(validate(persona).ok, true);
  assert.deepEqual(persona.cognition.behavioral_traits, ['curious']);
});

await test('studio DOWNGRADES an over-claimed scientific request', async () => {
  const s = new PersonaStudio({ mode: 'scientific', realism: 'hyperrealism', sign: (h) => '0xsig', signer: '0xbankon' });
  s.identity({ name: 'Overclaim' })
    .consent({ kind: 'self', subject: 'codephreak' })
    .face({ faceprint: faceprint('0xf2'), landmarks: lms(478, 0.05), sourceLandmarks: lms(), frames: 2 });
  await s.voice({ referenceClip: clip(120, 2), clonedClip: clip(300, 2, 2) }); // wrong voice, tiny reference
  const { persona, graded, requested, downgraded } = await s.stamp();
  assert.equal(requested.realism, 'hyperrealism');
  assert.notEqual(graded.mode, 'scientific');
  assert.equal(downgraded, true, 'the tool must report the downgrade');
  assert.equal(persona.fidelity.mode, graded.mode, 'the FILE carries the earned tier');
  assert.ok(graded.failed.length > 0, 'and names what failed');
});

await test('a SUPPLIED measurement can never override a COMPUTED one', async () => {
  const s = new PersonaStudio({ mode: 'professional' });
  s.identity({ name: 'Cheat' })
    .consent({ kind: 'self', subject: 'codephreak' })
    .face({ faceprint: faceprint('0xf6'), landmarks: lms(478, 0.08), sourceLandmarks: lms(), frames: 1 });
  await s.voice({ referenceClip: clip(120, 2), clonedClip: clip(400, 2, 2) });
  // Try to inject flattering numbers over measurements the tool actually took.
  const m = await s.measure({ faceRmse: 0.0001, voiceSimilarity: 0.999, faceFrames: 99 });
  assert.ok(m.faceRmse > 0.0001, 'computed faceRmse survives the injection attempt');
  assert.ok(m.voiceSimilarity < 0.999, 'computed similarity survives');
  assert.equal(s.persona.fidelity.measuredSource.faceRmse, 'computed');
  // An axis this host genuinely cannot compute MAY be filled — and is labelled.
  const m2 = await s.measure({ mos: 4.6 });
  assert.equal(s.persona.fidelity.measuredSource.mos, 'supplied');
  assert.equal(m2.mos, 4.6);
});

await test('scientific tier without a signer is REFUSED, not silently downgraded', async () => {
  const s = new PersonaStudio({ mode: 'scientific' }); // no sign
  s.identity({ name: 'Unsigned' })
    .consent({ kind: 'self', subject: 'codephreak' })
    .face({ faceprint: faceprint('0xf3'), landmarks: lms(), sourceLandmarks: lms(), frames: 40 });
  const ref = capture(117.1875, 200); // a real capture: pauses, quiet room, long enough
  await s.voice({ referenceClip: ref, clonedClip: ref });
  await assert.rejects(() => s.stamp(), /requires a SIGNED manifest/);
});

await test('scientific tier: earned, signed, verifiable end-to-end', async () => {
  const s = new PersonaStudio({
    mode: 'scientific', realism: 'hyperrealism',
    sign: (h) => '0xsig' + h.slice(2, 12), signer: '0xbankon.eth',
  });
  s.identity({ name: 'Codephreak', description: 'the architect' })
    .consent({ kind: 'self', subject: 'codephreak', subjectAddress: '0xbankon.eth' })
    .face({ faceprint: faceprint('0xf4'), landmarks: lms(), sourceLandmarks: lms(), frames: 40 });
  const ref = capture(117.1875, 200);
  await s.voice({ referenceClip: ref, clonedClip: ref }); // a perfect clone of a real capture
  s.rig();
  const { persona, graded, downgraded, validation } = await s.stamp();
  assert.equal(graded.mode, 'scientific');
  assert.equal(graded.realism, 'hyperrealism', `earned hyperrealism (failed: ${graded.failed})`);
  assert.equal(downgraded, false);
  assert.ok(validation.ok, `valid: ${validation.errors.join(', ')}`);
  assert.ok(persona.provenance.manifest.signature, 'signed');
  assert.ok(persona.provenance.custody.length >= 3, 'custody chain recorded');
  assert.match(persona.provenance.manifest.declaration, /SYNTHETIC/);
  const v = verify(persona.provenance.manifest, persona.provenance.custody);
  assert.ok(v.ok && v.signed, `provenance verifies: ${v.errors.join(',')}`);
});

await test('save → load roundtrip verifies provenance and cognitive projection', async () => {
  const path = join(tmpdir(), `aivatar-test-${process.pid}.persona`);
  const s = new PersonaStudio({ mode: 'basic' });
  s.identity({ name: 'Roundtrip', agent_id: 'rt_1', beliefs: { honest: true } })
    .consent({ kind: 'synthetic' })
    .face({ faceprint: faceprint('0xf5'), frames: 1 });
  await s.voice({ referenceClip: clip(140, 2) });
  await s.save(path);
  const { persona, validation, provenance } = await PersonaStudio.load(path);
  assert.ok(validation.ok, validation.errors.join(','));
  assert.ok(provenance.ok);
  assert.equal(persona.identity.agent_id, 'rt_1');
  const cog = s.toCognitive();
  assert.equal(cog.name, 'Roundtrip');
  assert.deepEqual(cog.beliefs, { honest: true }, 'v1 consumers still see a cognitive persona');
  await unlink(path);
});

await test('capability probe is honest about this host', async () => {
  const cap = await new PersonaStudio().capability();
  assert.equal(typeof cap.voice, 'boolean');
  assert.ok(['basic', 'professional', 'scientific'].includes(cap.maxHonestMode));
});


// ── intake (v3 signal/noise layer) ──────────────────────────────────────
await test('intake grades the ROOM and names which tiers it can still support', async () => {
  const s = new PersonaStudio({ mode: 'scientific', realism: 'hyperrealism' });
  const clean = capture(117.1875, 200);
  const good = await s.intake(clean);
  assert.ok(good.snr.snrDb > 0, 'measures the capture SNR');
  assert.ok(good.sufficientFor.includes('basic'));
  assert.ok(good.seconds > 100, 'reports usable duration');

  // a noisy room: the same voice, buried in hiss
  const noisy = { samples: Float32Array.from(clean.samples, (v) => v * 0.2 + 0.05 * (Math.random() * 2 - 1)), sampleRate: SR };
  const bad = await new PersonaStudio({ mode: 'scientific' }).intake(noisy);
  assert.ok(bad.snr.snrDb < good.snr.snrDb, 'the noisy room measures worse');
  assert.ok(!bad.sufficientFor.includes('scientific/hyperrealism'), 'and cannot support hyperrealism');
});

await test('a noisy reference CANNOT earn hyperrealism — you cannot out-model a room', async () => {
  const s = new PersonaStudio({
    mode: 'scientific', realism: 'hyperrealism',
    sign: (h) => '0xsig', signer: '0xbankon',
  });
  const clean = capture(117.1875, 200);
  const noisy = { samples: Float32Array.from(clean.samples, (v) => v + 0.06 * (Math.random() * 2 - 1)), sampleRate: SR };
  s.identity({ name: 'NoisyRoom' })
    .consent({ kind: 'self', subject: 'codephreak' })
    .face({ faceprint: faceprint('0xf7'), landmarks: lms(), sourceLandmarks: lms(), frames: 40 });
  await s.voice({ referenceClip: noisy, clonedClip: noisy });
  const { graded, downgraded } = await s.stamp();
  assert.ok(graded.failed.includes('referenceSnrDb'), 'the room is the gate that fails');
  assert.notEqual(graded.realism, 'hyperrealism');
  assert.equal(downgraded, true);
});


await test('a clip with NO silence reports SNR as unmeasurable, not as zero', async () => {
  const s = new PersonaStudio({ mode: 'scientific', realism: 'realism' });
  const noPauses = clip(117.1875, 20); // wall-to-wall speech — no room to hear
  const r = await s.intake(noPauses);
  assert.equal(r.snr.snrDb, null, 'no floor exists in this clip');
  assert.equal(r.snr.verdict, 'unmeasurable');
  assert.match(r.snr.reason, /room tone/, 'and it says how to fix that');
  assert.ok(!r.sufficientFor.includes('scientific/realism'), 'unmeasured cannot pass a gate');

  // Supply room tone — the floor becomes measurable, the capture becomes gradeable.
  const roomTone = { samples: Float32Array.from({ length: SR * 2 }, () => 0.0008 * (Math.random() * 2 - 1)), sampleRate: SR };
  const r2 = await new PersonaStudio({ mode: 'scientific' }).intake(noPauses, { roomTone });
  assert.equal(typeof r2.snr.snrDb, 'number');
  assert.equal(r2.snr.floorFrom, 'room-tone');
  assert.ok(r2.snr.snrDb > 30, 'a quiet room against a strong voice is a clean capture');
});

console.log(`\naivatar: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
