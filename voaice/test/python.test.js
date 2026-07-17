/**
 * python.test.js — the Python speech bridge probes and degrades honestly.
 * Runs offline: Python is present on CI/dev but the speech libs usually aren't,
 * so this exercises the capability + honest-refusal paths (the ones that matter).
 */
import assert from 'node:assert/strict';
import { unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { PythonSpeech } from '../src/index.js';

let pass = 0;
let fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

const py = new PythonSpeech();
let pythonPresent = true;

await test('capability probe returns a structured report (or python is absent)', async () => {
  try {
    const cap = await py.capability();
    assert.ok(cap.python, 'reports the python version');
    assert.ok(cap.tts && Array.isArray(cap.tts.available), 'tts availability listed');
    assert.ok(cap.stt && Array.isArray(cap.stt.available), 'stt availability listed');
    // when no engine is present, hints tell you how to install one
    if (!cap.tts.resolved) assert.ok(cap.tts.hints.length >= 1, 'tts install hints');
    if (!cap.stt.resolved) assert.ok(cap.stt.hints.length >= 1, 'stt install hints');
  } catch (e) {
    pythonPresent = false;
    assert.match(e.message, /python/i, 'a clear "python not found" error is acceptable');
    console.log('   (python3 not on PATH — bridge reported it honestly)');
  }
});

await test('available() summarises without throwing', async () => {
  const a = await py.available();
  assert.equal(typeof a.tts, 'boolean');
  assert.equal(typeof a.stt, 'boolean');
});

await test('tts refuses empty text', async () => {
  await assert.rejects(() => py.tts('   ', '/tmp/none.wav'), /nothing to speak/);
});

await test('with no engine, tts/stt fail with an install hint — never fake output', async () => {
  if (!pythonPresent) { console.log('   (skipped: no python)'); return; }
  const cap = await py.capability();
  if (!cap.tts.resolved) {
    await assert.rejects(() => py.tts('hello', join(tmpdir(), 'x.wav')), /pip install|no Python TTS/i);
  }
  if (!cap.stt.resolved) {
    await assert.rejects(() => py.stt(join(tmpdir(), 'x.wav')), /refusing to invent|pip install|no Python STT/i);
  }
  if (cap.tts.resolved || cap.stt.resolved) console.log(`   (an engine is installed: ${cap.tts.resolved || ''} ${cap.stt.resolved || ''})`);
});

console.log(`\npython bridge: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
