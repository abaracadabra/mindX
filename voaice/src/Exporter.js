/**
 * Exporter.js — quality-tiered audio export: .wav (in-house codec, 16/24/32f)
 * and .ogg (Vorbis via the system ffmpeg when present).
 *
 * Quality is a SETTING, not an accident of the pipeline:
 *
 *   import { exportClip, QUALITY, oggAvailable } from 'voaice/exporter';
 *   await exportClip(clip, { format: 'wav', quality: 'studio', path: 'out.wav' });
 *   await exportClip(clip, { format: 'ogg', quality: 'high',   path: 'out.ogg' });
 *   // or explicit settings instead of a tier:
 *   await exportClip(clip, { format: 'ogg', settings: { sampleRate: 48000, oggQuality: 8 } });
 *
 * WAV needs nothing beyond this package. OGG shells out to ffmpeg/libvorbis
 * (`-q:a` 0..10) and fails with a clear message when ffmpeg is absent —
 * `oggAvailable()` lets callers offer the option honestly.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { spawn, spawnSync } from 'node:child_process';
import { writeFile } from 'node:fs/promises';
import { encodeWav } from './audio/wav.js';
import { resample } from './Editor.js';

/** Quality tiers — sampleRate / WAV bitDepth / OGG libvorbis -q:a. */
export const QUALITY = {
  low: { sampleRate: 22050, bitDepth: 16, oggQuality: 2 },
  medium: { sampleRate: 44100, bitDepth: 16, oggQuality: 5 },
  high: { sampleRate: 48000, bitDepth: 24, oggQuality: 7 },
  studio: { sampleRate: 48000, bitDepth: 32, oggQuality: 10 },
};

/** Resolve a tier name or explicit settings object into concrete settings. */
export function resolveQuality(quality = 'high', settings = {}) {
  const base = QUALITY[quality] || QUALITY.high;
  return { ...base, ...settings };
}

let _ffmpeg; // memoised availability
/** Is a usable ffmpeg (the OGG encoder) on PATH? */
export function oggAvailable() {
  if (_ffmpeg === undefined) {
    try {
      _ffmpeg = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0;
    } catch {
      _ffmpeg = false;
    }
  }
  return _ffmpeg;
}

/** Encode a clip to WAV bytes at the given quality. */
export function toWav(clip, { quality, settings } = {}) {
  const q = resolveQuality(quality, settings);
  const c = clip.sampleRate === q.sampleRate ? clip : resample(clip, q.sampleRate);
  return {
    buffer: encodeWav(c.samples, q.sampleRate, { bitDepth: q.bitDepth }),
    settings: q,
    format: 'wav',
  };
}

/** Encode a clip to OGG/Vorbis bytes via ffmpeg (async). */
export async function toOgg(clip, { quality, settings } = {}) {
  if (!oggAvailable()) {
    throw new Error(
      'toOgg: ffmpeg not found on PATH — OGG export needs ffmpeg/libvorbis ' +
        '(WAV export works without it). Install ffmpeg or use format:"wav".'
    );
  }
  const q = resolveQuality(quality, settings);
  const c = clip.sampleRate === q.sampleRate ? clip : resample(clip, q.sampleRate);
  // Feed a float WAV in (no double quantisation); libvorbis owns the lossy step.
  const wavIn = encodeWav(c.samples, q.sampleRate, { bitDepth: 32 });
  const args = [
    '-hide_banner', '-loglevel', 'error',
    '-f', 'wav', '-i', 'pipe:0',
    '-c:a', 'libvorbis', '-q:a', String(q.oggQuality),
    '-f', 'ogg', 'pipe:1',
  ];
  const buffer = await new Promise((resolvePromise, reject) => {
    const p = spawn('ffmpeg', args, { stdio: ['pipe', 'pipe', 'pipe'] });
    const out = [];
    const err = [];
    p.stdout.on('data', (d) => out.push(d));
    p.stderr.on('data', (d) => err.push(d));
    p.on('error', reject);
    p.on('close', (code) =>
      code === 0
        ? resolvePromise(Buffer.concat(out))
        : reject(new Error(`ffmpeg exited ${code}: ${Buffer.concat(err).toString().slice(0, 300)}`))
    );
    p.stdin.on('error', () => {}); // ffmpeg may close stdin early on error
    p.stdin.end(wavIn);
  });
  return { buffer, settings: q, format: 'ogg' };
}

/**
 * Export a clip to bytes or a file.
 * @param {{samples: Float32Array, sampleRate: number}} clip
 * @param {{format?: 'wav'|'ogg', quality?: keyof typeof QUALITY, settings?: object, path?: string}} opts
 * @returns {Promise<{format, settings, bytes, buffer, path?}>}
 */
export async function exportClip(clip, opts = {}) {
  const format = (opts.format || 'wav').toLowerCase();
  let result;
  if (format === 'wav') result = toWav(clip, opts);
  else if (format === 'ogg') result = await toOgg(clip, opts);
  else throw new Error(`exportClip: unsupported format "${format}" (wav|ogg)`);
  const out = { ...result, bytes: result.buffer.length };
  if (opts.path) {
    await writeFile(opts.path, result.buffer);
    out.path = opts.path;
  }
  return out;
}

export default exportClip;
