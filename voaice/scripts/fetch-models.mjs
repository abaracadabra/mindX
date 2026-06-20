#!/usr/bin/env node
/**
 * fetch-models.mjs — download the neural voice weights (CPU/ONNX, torch-free).
 *
 * Weights are NOT committed: they are large and carry their own upstream licenses (see
 * MODELS.md). This downloader pulls them into ./models on demand. URLs are read from
 * models/manifest.json so the chosen export can change without touching code; override the
 * base with VOAICE_MODELS_BASE for a private mirror/IPFS gateway.
 *
 *   npm run fetch-models            # fetch all artefacts in the manifest
 *   npm run fetch-models -- kokoro  # fetch one group
 *
 * Stage 1 (talk):  kokoro.onnx, voices.bin, kokoro.json
 * Stage 2 (clone): tone_encoder.onnx, tone_converter.onnx, tone_color.json
 */

import { createWriteStream, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';
import { spawnSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MODELS_DIR = join(__dirname, '..', 'models');
const MANIFEST = join(MODELS_DIR, 'manifest.json');

// Default manifest targets the sherpa-onnx model bundles (the real CPU path). Each group
// entry is either a flat "filename" (base/filename → models/filename) or an archive object
// { archive: "url", into: "<dir>" } that is downloaded and extracted into models/<dir>/.
const DEFAULT_MANIFEST = {
  base: 'https://github.com/k2-fsa/sherpa-onnx/releases/download',
  groups: {
    kokoro: [{ archive: 'tts-models/kokoro-en-v0_19.tar.bz2', into: 'kokoro' }],
    zipvoice: [{ archive: 'tts-models/sherpa-onnx-zipvoice-distill-zh-en-emilia.tar.bz2', into: 'zipvoice' }],
  },
};

function loadManifest() {
  if (!existsSync(MANIFEST)) {
    console.log('No models/manifest.json — using the built-in sherpa-onnx default bundles.');
    console.log('(Override per-host with models/manifest.json or VOAICE_MODELS_BASE.)\n');
    return DEFAULT_MANIFEST;
  }
  return JSON.parse(readFileSync(MANIFEST, 'utf8'));
}

async function download(url, dest) {
  if (existsSync(dest)) {
    console.log(`✓ ${dest} (cached)`);
    return;
  }
  console.log(`↓ ${url}`);
  const res = await fetch(url);
  if (!res.ok || !res.body) throw new Error(`fetch failed ${res.status} ${url}`);
  mkdirSync(dirname(dest), { recursive: true });
  await pipeline(Readable.fromWeb(res.body), createWriteStream(dest));
  console.log(`✓ ${dest}`);
}

/** Download an archive and extract it into models/<into>/ via system `tar` (flatten 1 level). */
async function fetchArchive(base, entry) {
  const into = join(MODELS_DIR, entry.into);
  if (existsSync(join(into, 'model.onnx')) || existsSync(join(into, 'encoder.onnx'))) {
    console.log(`✓ ${entry.into}/ (cached)`);
    return;
  }
  const url = /^https?:/.test(entry.archive) ? entry.archive : `${base}/${entry.archive}`;
  const tmp = join(MODELS_DIR, entry.archive.split('/').pop());
  await download(url, tmp);
  mkdirSync(into, { recursive: true });
  // strip the archive's top-level dir so files land directly in models/<into>/
  const r = spawnSync('tar', ['xf', tmp, '-C', into, '--strip-components=1'], { stdio: 'inherit' });
  if (r.status !== 0) {
    throw new Error(`tar extraction failed for ${tmp} (is \`tar\` installed?)`);
  }
  console.log(`✓ extracted → ${into}/`);
}

async function main() {
  const manifest = loadManifest();
  const base = process.env.VOAICE_MODELS_BASE || manifest.base;
  const only = process.argv[2];
  const groups = Object.entries(manifest.groups).filter(([g]) => !only || g === only);
  if (!groups.length) {
    console.error(`No group "${only}" in manifest. Available: ${Object.keys(manifest.groups).join(', ')}`);
    process.exit(1);
  }
  for (const [group, entries] of groups) {
    console.log(`\n[${group}]`);
    for (const e of entries) {
      if (typeof e === 'object' && e.archive) await fetchArchive(base, e);
      else await download(`${base}/${e}`, join(MODELS_DIR, e));
    }
  }
  console.log('\nDone. The neural engine will detect the weights on next init().');
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
