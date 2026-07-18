/**
 * morph.test.js — the morph-mode registry's pure core.
 * Run: node src/face_clone/morph.test.js
 */
import { strict as assert } from 'assert';
import { MORPH_MODES, MORPH_PALETTE, morphMode, isWholeFace, clampIntensity, morphPalette, ageBand, ageYears } from './morph.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

test('the registry has human, machine, and the four archetypes', () => {
  const keys = MORPH_MODES.map((m) => m.key);
  for (const k of ['none', 'cyborgi', 'vampire', 'elf', 'dragon', 'pleiadian']) assert.ok(keys.includes(k), `has ${k}`);
});

test('morphMode resolves a key and falls back to human', () => {
  assert.equal(morphMode('dragon').label, 'dragon');
  assert.equal(morphMode('nonsense').key, 'none', 'unknown → human');
});

test('whole-face vs sided modes', () => {
  assert.equal(isWholeFace('vampire'), true);
  assert.equal(isWholeFace('cyborgi'), false, 'cyborgi is one-sided');
  assert.equal(isWholeFace('none'), false);
});

test('clampIntensity keeps the slider in [0,1]', () => {
  assert.equal(clampIntensity(-1), 0);
  assert.equal(clampIntensity(2), 1);
  assert.equal(clampIntensity(0.5), 0.5);
  assert.equal(clampIntensity(NaN), 0);
});

test('each archetype has a palette; none/mech do not', () => {
  for (const k of ['vampire', 'elf', 'dragon', 'pleiadian']) { assert.ok(morphPalette(k), `${k} palette`); assert.ok(MORPH_PALETTE[k].eye, `${k}.eye`); }
  assert.equal(morphPalette('none'), null);
  assert.equal(morphPalette('cyborgi'), null, 'cyborgi uses mech.js palette');
});

test('ageBand + ageYears span child → elder monotonically', () => {
  assert.equal(ageBand(0), 'child');
  assert.equal(ageBand(0.5), 'adult');
  assert.equal(ageBand(1), 'elder');
  assert.ok(ageYears(0) < ageYears(0.5) && ageYears(0.5) < ageYears(1), 'years increase with the slider');
  assert.ok(ageYears(1) <= 90 && ageYears(0) >= 6, 'within a sane human range');
});

console.log(`\nmorph: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
