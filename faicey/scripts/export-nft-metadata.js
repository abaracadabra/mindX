#!/usr/bin/env node
/**
 * export-nft-metadata.js — export a faicey artifact as a DeltaVerse iNFT-7857
 * mint payload (and OpenSea metadata).
 *
 * Reads a `.persona` file or a faceprint/voiceprint JSON (anything with a `hash`
 * + measures) and writes the ERC-7857 `mintAgent(...)` payload, ready for the
 * DeltaVerse deployer/minter or the blockchain agent factory.
 *
 *   node scripts/export-nft-metadata.js jaimla.persona [--to 0xowner] [--storage ipfs://…] [--thot 0x…] [--out out.json]
 *
 * With no input it exports the sample prints under exports/.
 *
 * © Professor Codephreak - rage.pythai.net
 */
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { toInftMint } from '../src/face_clone/inft.js';

const root = dirname(dirname(fileURLToPath(import.meta.url)));

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

/** Pull a mintable print out of a .persona (embodiment) or a raw print file. */
function printFrom(doc, label) {
  if (doc.kind === 'aivatar-persona') {
    // a persona: prefer its bound persona-print hash + registerArgs
    if (doc.hash && doc.aiml?.inft?.registerArgs) {
      return { hash: doc.hash, measuresStr: doc.aiml.inft.registerArgs.m || [],
        modalities: doc.aiml.inft.modalities || [], kind: 'persona',
        precisionScore: doc.aiml.inft.registerArgs.precisionScore, registerArgs: doc.aiml.inft.registerArgs,
        name: doc.identity?.name || label };
    }
    const face = doc.embodiment?.face?.faceprint;
    if (face?.hash) return { ...face, kind: 'faceprint', name: doc.identity?.name || label };
    throw new Error('persona has no mintable print (bind a face/voice first)');
  }
  if (doc.hash) return { ...doc, name: doc.name || label }; // a raw faceprint/voiceprint
  throw new Error('not a .persona or a print (no hash)');
}

async function exportOne(path) {
  const doc = JSON.parse(readFileSync(path, 'utf8'));
  const p = printFrom(doc, basename(path).replace(/\.[^.]+$/, ''));
  const payload = await toInftMint(p, {
    to: arg('to'), storageURI: arg('storage'), thotRoot: arg('thot'),
    name: p.name, chainId: arg('chain') ? Number(arg('chain')) : null,
  });
  const out = arg('out', path.replace(/\.[^.]+$/, '') + '.inft.json');
  writeFileSync(out, JSON.stringify(payload, null, 2));
  console.log(`✓ ${basename(path)} → ${basename(out)}  (contentRoot ${payload.mintAgent.contentRoot.slice(0, 18)}…, dim ${payload.mintAgent.dimensions})`);
}

async function main() {
  const input = process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : null;
  if (input) return exportOne(input);
  // no input → export the sample prints under exports/
  const dir = join(root, 'exports');
  if (!existsSync(dir)) { console.error('no input and no exports/ dir'); process.exit(1); }
  const files = readdirSync(dir).filter((f) => f.endsWith('.json') && !f.endsWith('.inft.json'));
  if (!files.length) { console.error('no prints under exports/'); process.exit(1); }
  let done = 0;
  for (const f of files) {
    try { await exportOne(join(dir, f)); done++; }
    catch (e) { console.log(`· skip ${f} — ${e.message}`); } // legacy OpenSea metadata, not a print
  }
  if (!done) console.log('(no mintable prints found — pass a .persona file, e.g. `node scripts/export-nft-metadata.js my.persona`)');
}

main().catch((e) => { console.error('export failed:', e.message); process.exit(1); });
