/**
 * minter.test.js — the iNFT payload → a real, correctly-encoded mint transaction.
 * The encoder was cross-checked byte-for-byte against viem; this locks the
 * structure in-repo (round-trip decode) with no external dependency.
 * Run: node src/face_clone/minter.test.js
 */
import { strict as assert } from 'assert';
import { toMintTx, encodeMintAgent, encodeAttachThot, SELECTORS } from './minter.js';
import { toInftMint } from './inft.js';
import { neutralFace } from './neutral_face.js';
import { proportions } from './geometry.js';
import { measureFaceprint } from './faceprint.js';

let pass = 0, fail = 0;
const test = async (name, fn) => {
  try { await fn(); pass++; console.log(`✅ ${name}`); }
  catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); }
};

// minimal calldata decoder for mintAgent (mirror of the encoder) — proves the
// bytes a wallet would broadcast decode back to the intended arguments.
function decodeMintAgent(data) {
  const d = data.slice(10); // strip 0x + 4-byte selector
  const word = (i) => d.slice(i * 64, i * 64 + 64);
  const to = '0x' + word(0).slice(24);
  const contentRoot = '0x' + word(1);
  const offStorage = parseInt(word(2), 16);
  const metadataRoot = '0x' + word(3);
  const dimensions = parseInt(word(4), 16);
  const parallelUnits = parseInt(word(5), 16);
  const sealedKeyHash = '0x' + word(6);
  const offToken = parseInt(word(7), 16);
  const readStr = (byteOff) => {
    const at = byteOff * 2; const len = parseInt(d.slice(at, at + 64), 16);
    const hex = d.slice(at + 64, at + 64 + len * 2);
    return new TextDecoder().decode(Uint8Array.from(hex.match(/../g).map((h) => parseInt(h, 16))));
  };
  return { to, contentRoot, storageURI: readStr(offStorage), metadataRoot, dimensions,
    parallelUnits, sealedKeyHash, tokenURI: readStr(offToken) };
}

const facePrint = async () => measureFaceprint(proportions(neutralFace()), { confidence: 1, symmetry: 1, frontality: 1 });

await test('mint tx carries the right selector, contract, and chain', async () => {
  const payload = await toInftMint(await facePrint(), { to: '0x' + '11'.repeat(20), storageURI: 'ipfs://Qm' });
  const tx = toMintTx(payload, { contract: '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9', chainId: 31337 });
  assert.equal(tx.mint.to, '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9', 'to = the iNFT contract');
  assert.equal(tx.chainId, 31337);
  assert.ok(tx.mint.data.startsWith(SELECTORS.mintAgent), 'mintAgent selector');
  assert.equal(tx.mint.value, '0x0', 'no value — mint is free here');
  assert.equal(tx.mint.functionName, 'mintAgent');
  assert.equal(tx.mint.args.length, 8, 'the 8 mintAgent args for a viem/ethers caller');
});

await test('the calldata decodes back to the payload — it is a REAL, valid tx', async () => {
  const to = '0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169'.toLowerCase();
  const payload = await toInftMint(await facePrint(), { to, storageURI: 'ipfs://QmExampleFaceCID', name: 'Jaimla' });
  const tx = toMintTx(payload, { contract: '0xcf7ed3acca5a467e9e704c703e8d87f634fb0fc9' });
  const dec = decodeMintAgent(tx.mint.data);
  assert.equal(dec.to.toLowerCase(), to, 'owner survives encoding');
  assert.equal(dec.contentRoot, payload.mintAgent.contentRoot, 'content root survives');
  assert.equal(dec.metadataRoot, payload.mintAgent.metadataRoot, 'metadata root survives');
  assert.equal(dec.dimensions, payload.mintAgent.dimensions, 'dimensions survive');
  assert.equal(dec.parallelUnits, payload.mintAgent.parallelUnits);
  assert.equal(dec.sealedKeyHash, payload.mintAgent.sealedKeyHash);
  assert.equal(dec.storageURI, 'ipfs://QmExampleFaceCID', 'the dynamic storage string survives');
  assert.equal(dec.tokenURI, payload.mintAgent.tokenURI_, 'the dynamic tokenURI survives');
});

await test('a THOT root becomes a second, tokenId-parameterised tx', async () => {
  const payload = await toInftMint(await facePrint(), { to: '0x' + '22'.repeat(20), thotRoot: '0x' + 'ef'.repeat(32) });
  const tx = toMintTx(payload, { contract: '0x' + 'aa'.repeat(20) });
  assert.equal(typeof tx.attachThot, 'function', 'attachThot is a follow-up the caller runs with the minted tokenId');
  const t2 = tx.attachThot(7);
  assert.ok(t2.data.startsWith(SELECTORS.attachThotRoot), 'attachThotRoot selector');
  assert.equal(encodeAttachThot(7, '0x' + 'ef'.repeat(32)), t2.data, 'encodes tokenId + thotRoot');
  assert.deepEqual(t2.args, ['7', '0x' + 'ef'.repeat(32)]);
});

await test('the owner (to) defaults to the sender when unset', async () => {
  const payload = await toInftMint(await facePrint(), { storageURI: 's' }); // no `to`
  assert.equal(payload.mintAgent.to, null, 'payload has no owner yet');
  const tx = toMintTx(payload, { contract: '0x' + 'bb'.repeat(20), from: '0x' + '33'.repeat(20) });
  assert.equal(tx.mint.args[0], '0x' + '33'.repeat(20), 'sender becomes the owner');
});

await test('rejects a non-payload and a missing contract', async () => {
  assert.throws(() => toMintTx({ standard: 'x' }, { contract: '0x1' }), /not an ERC-7857/);
  const payload = await toInftMint(await facePrint(), { to: '0x' + '44'.repeat(20) });
  assert.throws(() => toMintTx(payload, {}), /contract address is required/);
});

console.log(`\nminter: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
