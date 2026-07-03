/**
 * g2p.js — grapheme-to-phoneme, lazily backed by espeak-ng when present.
 *
 * The Kokoro/OpenVoice ONNX models are phoneme-driven. The reference g2p is espeak-ng
 * (the same front-end Kokoro trains against). voaice keeps zero hard deps, so this module
 * detects the `espeak-ng` binary at runtime (exactly like VoiceCreationEngine probes its
 * TTS binaries) and falls back to a dependency-free normaliser when it is absent — enough
 * to exercise the pipeline offline, with a clear quality caveat surfaced via `.backend`.
 */

import { spawn } from 'node:child_process';

let _cached = null; // null = unprobed, true/false = result

/** Resolve once whether `espeak-ng` is callable on this host. */
export async function hasEspeak() {
  if (_cached !== null) return _cached;
  _cached = await new Promise((resolve) => {
    let done = false;
    const finish = (v) => {
      if (!done) {
        done = true;
        resolve(v);
      }
    };
    try {
      const p = spawn('espeak-ng', ['--version'], { stdio: 'ignore' });
      p.on('error', () => finish(false));
      p.on('close', (code) => finish(code === 0 || code === 1));
    } catch {
      finish(false);
    }
  });
  return _cached;
}

/** Run espeak-ng's IPA phonemiser (`-q -x --ipa`). */
function espeakPhonemes(text, lang) {
  return new Promise((resolve, reject) => {
    const p = spawn('espeak-ng', ['-q', '--ipa', '-v', lang], { stdio: ['pipe', 'pipe', 'ignore'] });
    let out = '';
    p.stdout.on('data', (d) => (out += d));
    p.on('error', reject);
    p.on('close', () => resolve(out.replace(/\s+/g, ' ').trim()));
    p.stdin.end(text);
  });
}

/**
 * Dependency-free fallback: lowercase, strip control chars, collapse whitespace and keep
 * sentence punctuation. NOT true phonemes — a graceful degradation so the model/test
 * pipeline runs without espeak-ng installed.
 */
function fallbackNormalise(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s.,!?;:'\-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Phonemise text for the neural front-end.
 * @param {string} text
 * @param {{lang?: string}} [opts]
 * @returns {Promise<{ phonemes: string, backend: 'espeak-ng'|'fallback' }>}
 */
export async function phonemize(text, opts = {}) {
  const lang = opts.lang || 'en-us';
  if (await hasEspeak()) {
    try {
      return { phonemes: await espeakPhonemes(text, lang), backend: 'espeak-ng' };
    } catch {
      /* fall through to the dependency-free path */
    }
  }
  return { phonemes: fallbackNormalise(text), backend: 'fallback' };
}

/** Reset the cached probe (testing). */
export function _resetProbe() {
  _cached = null;
}
