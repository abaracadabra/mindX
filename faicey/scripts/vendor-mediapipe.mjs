#!/usr/bin/env node
/**
 * vendor-mediapipe.mjs — vendor MediaPipe Face Landmarker locally (no CDN).
 *
 * Copies the @mediapipe/tasks-vision runtime (bundle + WASM) out of node_modules into
 * static/vendor/mediapipe/, and downloads the face_landmarker.task model. The bundle is small and
 * committed; the WASM binaries + the .task weights are gitignored and re-fetched by this script
 * (Apache-2.0, Google). Run after `npm i @mediapipe/tasks-vision`.
 *
 *   npm run vendor:mediapipe
 */
import { existsSync, mkdirSync, copyFileSync, readdirSync, createWriteStream } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const src = join(root, 'node_modules', '@mediapipe', 'tasks-vision');
const dst = join(root, 'static', 'vendor', 'mediapipe');
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

if (!existsSync(src)) {
  console.error('Missing node_modules/@mediapipe/tasks-vision — run `npm i @mediapipe/tasks-vision` first.');
  process.exit(1);
}
mkdirSync(join(dst, 'wasm'), { recursive: true });

copyFileSync(join(src, 'vision_bundle.mjs'), join(dst, 'vision_bundle.mjs'));
for (const f of readdirSync(join(src, 'wasm'))) copyFileSync(join(src, 'wasm', f), join(dst, 'wasm', f));
console.log('✓ vendored bundle + wasm → static/vendor/mediapipe/');

const model = join(dst, 'face_landmarker.task');
if (existsSync(model)) {
  console.log('✓ face_landmarker.task (cached)');
} else {
  console.log('↓ face_landmarker.task');
  const res = await fetch(process.env.VOAICE_MEDIAPIPE_MODEL || MODEL_URL);
  if (!res.ok || !res.body) throw new Error(`model fetch failed ${res.status}`);
  await pipeline(Readable.fromWeb(res.body), createWriteStream(model));
  console.log('✓ face_landmarker.task');
}
console.log('\nDone — face cloning from real photos/video is live at /clone-face.');
