#!/usr/bin/env node
/**
 * sync-engine.mjs — copy the canonical Faicey wireframe engine + vendored three.js
 * from the facerig package into faicey/static/vendor so the browser demos load them
 * locally (no CDN).
 *
 * Source of truth: facerig is canonical. It owns the engine (src/lib/faicey) and the
 * complete vendored three.js source (vendor/three). This script copies the built
 * artifacts that the browser actually needs:
 *
 *   facerig/dist-lib/faicey-engine.js                          -> static/vendor/faicey-engine.js
 *   facerig/vendor/three/build/three.module.js                 -> static/vendor/three.module.js
 *   facerig/vendor/three/examples/jsm/controls/OrbitControls.js-> static/vendor/jsm/controls/OrbitControls.js
 *
 * Run `npm run sync-engine` (also runs automatically on `prestart`/`preserve`).
 * Requires that facerig has been built first: `cd ../facerig && npm run build:lib`.
 */

import { existsSync, mkdirSync, copyFileSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const faiceyRoot = resolve(__dirname, '..');
const facerigRoot = resolve(faiceyRoot, '..', 'facerig');
const vendorOut = join(faiceyRoot, 'static', 'vendor');

const engineBundle = join(facerigRoot, 'dist-lib', 'faicey-engine.js');
const threeModule = join(facerigRoot, 'vendor', 'three', 'build', 'three.module.js');
// three.module.js re-exports from ./three.core.js (a sibling) — it MUST be copied
// alongside or both the Node #three import and the browser import map break.
const threeCore = join(facerigRoot, 'vendor', 'three', 'build', 'three.core.js');
const orbitControls = join(
  facerigRoot,
  'vendor',
  'three',
  'examples',
  'jsm',
  'controls',
  'OrbitControls.js'
);

function fail(msg) {
  console.error(`\n[sync-engine] ERROR: ${msg}\n`);
  process.exit(1);
}

// Standalone clones (no facerig sibling) run off the committed static/vendor
// copies — that's not an error. Only fail when there is NEITHER a facerig
// source to sync from NOR an already-vendored engine to serve.
const vendoredEngine = join(vendorOut, 'faicey-engine.js');
if (!existsSync(facerigRoot) || !existsSync(engineBundle)) {
  if (existsSync(vendoredEngine)) {
    console.log(
      '[sync-engine] facerig source not present — serving the committed ' +
        'static/vendor engine as-is (canonical rebuilds happen in facerig).'
    );
    process.exit(0);
  }
  fail(
    `engine bundle not found at\n  ${engineBundle}\n` +
      `and no committed vendor copy at ${vendoredEngine}.\n` +
      `Build it first:  cd ../facerig && npm install && npm run build:lib`
  );
}
if (!existsSync(threeModule)) {
  fail(
    `vendored three.js not found at\n  ${threeModule}\n` +
      `Ensure facerig/vendor/three is populated (see facerig/vendor/three/VENDOR.md).`
  );
}

const copies = [
  [engineBundle, join(vendorOut, 'faicey-engine.js')],
  [threeModule, join(vendorOut, 'three.module.js')],
  [threeCore, join(vendorOut, 'three.core.js')],
  [orbitControls, join(vendorOut, 'jsm', 'controls', 'OrbitControls.js')],
];

for (const [src, dest] of copies) {
  if (!existsSync(src)) {
    console.warn(`[sync-engine] skip (missing): ${src}`);
    continue;
  }
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  const kb = (statSync(dest).size / 1024).toFixed(1);
  console.log(`[sync-engine] ${dest.replace(faiceyRoot + '/', '')}  (${kb} kB)`);
}

console.log('[sync-engine] done — engine + three vendored into static/vendor (no CDN).');
