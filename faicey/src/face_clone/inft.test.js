/**
 * inft.test.js — faicey artifact → DeltaVerse iNFT-7857 mint payload.
 * Pure Node. Run: node src/face_clone/inft.test.js
 */
import { strict as assert } from 'assert';
import { toInftMint, dimensionFor, VALID_DIMENSIONS } from './inft.js';
import { neutralFace } from './neutral_face.js';
import { proportions } from './geometry.js';
import { measureFaceprint } from './faceprint.js';
import { personaPrint } from './persona.js';

let pass = 0, fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

await test('dimensionFor maps a measure count to a VALID ERC-7857 dimension', () => {
  assert.equal(dimensionFor(6), 8, '6 measures → 8');
  assert.equal(dimensionFor(12), 64, '12 face measures → 64');
  assert.equal(dimensionFor(18), 64, 'persona 18 → 64');
  for (const n of [6, 12, 18, 100]) assert.ok(VALID_DIMENSIONS.includes(dimensionFor(n)), `${n} → valid`);
});

await test('a faceprint mints as an iNFT — mintAgent args are complete + on-contract', async () => {
  const face = await measureFaceprint(proportions(neutralFace()), { confidence: 1, symmetry: 1, frontality: 1 });
  const p = await toInftMint(face, { to: '0x' + 'ab'.repeat(20), storageURI: 'ipfs://Qm…' });
  assert.equal(p.standard, 'ERC-7857');
  const m = p.mintAgent;
  // every argument the iNFT_7857.mintAgent(...) call needs
  for (const k of ['to', 'contentRoot', 'storageURI', 'metadataRoot', 'dimensions', 'parallelUnits', 'sealedKeyHash', 'tokenURI_']) {
    assert.ok(m[k] !== undefined && m[k] !== null, `mintAgent.${k} present`);
  }
  assert.equal(m.contentRoot, face.hash, 'the faceprint hash IS the content root');
  assert.match(m.contentRoot, /^0x[0-9a-f]{64}$/, 'content root is bytes32');
  assert.match(m.metadataRoot, /^0x[0-9a-f]{64}$/, 'metadata root is bytes32');
  assert.match(m.sealedKeyHash, /^0x[0-9a-f]{64}$/, 'sealed key hash is bytes32');
  assert.ok(VALID_DIMENSIONS.includes(m.dimensions), 'valid dimension');
  assert.ok(m.parallelUnits >= 1, 'parallel units ≥ 1');
});

await test('deterministic — same print → same mint payload', async () => {
  const face = await measureFaceprint(proportions(neutralFace()), { confidence: 1, symmetry: 1, frontality: 1 });
  const a = await toInftMint(face, { to: '0x1', storageURI: 's' });
  const b = await toInftMint(face, { to: '0x1', storageURI: 's' });
  assert.equal(a.mintAgent.contentRoot, b.mintAgent.contentRoot);
  assert.equal(a.mintAgent.metadataRoot, b.mintAgent.metadataRoot, 'metadata root reproducible');
  assert.equal(a.mintAgent.sealedKeyHash, b.mintAgent.sealedKeyHash, 'sealed key reproducible');
});

await test('a bound persona (face ⊕ voice) mints, carrying both modalities', async () => {
  const face = await measureFaceprint(proportions(neutralFace()), { confidence: 1, symmetry: 1, frontality: 1 });
  const voice = { hash: '0x' + 'cd'.repeat(32), measuresStr: ['120', '0.03', '1800', '0.06'], precisionScore: (0.8e18).toString() };
  const persona = await personaPrint({ face, voice, label: 'Jaimla' });
  const p = await toInftMint(persona, { to: '0xowner', name: 'Jaimla' });
  assert.equal(p.mintAgent.contentRoot, persona.hash, 'persona hash is the content root');
  assert.ok(p.metadata.faicey.modalities.includes('face') && p.metadata.faicey.modalities.includes('voice'), 'both modalities in metadata');
  assert.ok(p.metadata.faicey.registerArgs, 'the ERC-7857 registerArgs travel in the metadata');
  assert.ok(p.mintAgent.tokenURI_.startsWith('data:application/json'), 'tokenURI carries the metadata');
});

await test('a THOT root links the memory lineage (attachThotRoot)', async () => {
  const face = await measureFaceprint(proportions(neutralFace()), { confidence: 1, symmetry: 1, frontality: 1 });
  const thotRoot = '0x' + 'ef'.repeat(32);
  const p = await toInftMint(face, { to: '0x1', thotRoot });
  assert.deepEqual(p.attachThotRoot, { thotRoot }, 'thot root attached for the lineage');
  await assert.rejects(() => toInftMint(face, { thotRoot: '0xnothex' }), /32-byte hash/, 'a bad thot root is rejected');
});

await test('rejects an artifact with no valid hash', async () => {
  await assert.rejects(() => toInftMint({ measuresStr: ['1'] }), /32-byte hash/);
  await assert.rejects(() => toInftMint(null), /nothing to mint/);
});

console.log(`\ninft: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
