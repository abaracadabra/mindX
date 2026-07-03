/**
 * kokoro.js — base text-to-speech session (Stage 1: "can talk").
 *
 * Thin wrapper over a Kokoro-82M ONNX export (kokoro-onnx style I/O): phoneme token ids +
 * a 256-d style vector -> 24 kHz mono waveform. CPU, int8-friendly, torch-free. The model
 * file, the voice-style pack and the token vocab are fetched separately (scripts/fetch-models.mjs)
 * and never committed. I/O tensor names and the vocab are read from a sidecar `kokoro.json`
 * so the wrapper tracks the chosen export without code changes.
 *
 * When the weights are absent, callers fall back to the dependency-free synth in
 * NeuralVoiceEngine — this module only ever speaks when real weights are present.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createSession, tensor } from './runtime.js';

const DEFAULT_SR = 24000;

export class KokoroSession {
  /**
   * @param {{ modelDir: string, sampleRate?: number }} opts
   *   modelDir contains: kokoro.onnx, voices.bin, kokoro.json (config: io names + vocab + styleDim)
   */
  constructor(opts) {
    this.modelDir = opts.modelDir;
    this.sampleRate = opts.sampleRate || DEFAULT_SR;
    this.session = null;
    this.cfg = null;
    this.voices = null; // Map<string, Float32Array> style vectors
  }

  modelPath() {
    return join(this.modelDir, 'kokoro.onnx');
  }
  configPath() {
    return join(this.modelDir, 'kokoro.json');
  }
  voicesPath() {
    return join(this.modelDir, 'voices.bin');
  }

  /** True when every artefact the session needs is present on disk. */
  isCached() {
    return [this.modelPath(), this.configPath(), this.voicesPath()].every(existsSync);
  }

  /** Load config + voice pack + ONNX session (idempotent). */
  async load() {
    if (this.session) return;
    if (!this.isCached()) {
      throw new Error(
        `voaice neural: Kokoro weights not found in ${this.modelDir}. ` +
          'Run `npm run fetch-models` (CPU, torch-free) to download them.'
      );
    }
    this.cfg = JSON.parse(readFileSync(this.configPath(), 'utf8'));
    this.sampleRate = this.cfg.sampleRate || this.sampleRate;
    this.voices = this._loadVoices();
    this.session = await createSession(this.modelPath());
  }

  /**
   * Voice pack layout (documented in MODELS.md): a JSON manifest `voices` mapping a voice
   * name to [offset, length] into a flat Float32 `voices.bin`, with `styleDim` per frame.
   */
  _loadVoices() {
    const buf = readFileSync(this.voicesPath());
    const flat = new Float32Array(buf.buffer, buf.byteOffset, Math.floor(buf.byteLength / 4));
    const map = new Map();
    for (const [name, [off, len]] of Object.entries(this.cfg.voices || {})) {
      map.set(name, flat.subarray(off, off + len));
    }
    return map;
  }

  listVoices() {
    return this.voices ? [...this.voices.keys()] : Object.keys((this.cfg && this.cfg.voices) || {});
  }

  /** Map a phoneme/grapheme string to token ids via the config vocab. */
  _tokenize(phonemes) {
    const vocab = (this.cfg && this.cfg.vocab) || {};
    const ids = [];
    for (const ch of phonemes) {
      const id = vocab[ch];
      if (id !== undefined) ids.push(id);
    }
    // Kokoro wraps the sequence in pad/bos/eos (id 0 by convention)
    return [0, ...ids, 0];
  }

  /** Pick the style vector for a voice, defaulting to the first available. */
  _style(voice) {
    if (this.voices.has(voice)) return this.voices.get(voice);
    const first = this.voices.keys().next().value;
    if (!first) throw new Error('voaice neural: Kokoro voice pack is empty');
    return this.voices.get(first);
  }

  /**
   * Synthesize a waveform from phonemes.
   * @param {string} phonemes
   * @param {{ voice?: string, speed?: number, style?: Float32Array }} [opts]
   * @returns {Promise<{ samples: Float32Array, sampleRate: number }>}
   */
  async synth(phonemes, opts = {}) {
    await this.load();
    const io = this.cfg.io || { tokens: 'input_ids', style: 'style', speed: 'speed', output: 'waveform' };
    const styleDim = this.cfg.styleDim || 256;

    const ids = this._tokenize(phonemes);
    // Kokoro indexes the style pack by sequence length; clamp to the pack's frames.
    const styleAll = opts.style || this._style(opts.voice || this.cfg.defaultVoice);
    const frame = Math.min(ids.length, Math.floor(styleAll.length / styleDim) - 1);
    const style = styleAll.subarray(Math.max(0, frame) * styleDim, Math.max(0, frame) * styleDim + styleDim);

    const feeds = {
      [io.tokens]: await tensor('int64', BigInt64Array.from(ids.map((v) => BigInt(v))), [1, ids.length]),
      [io.style]: await tensor('float32', Float32Array.from(style), [1, styleDim]),
      [io.speed]: await tensor('float32', Float32Array.from([opts.speed || 1.0]), [1]),
    };
    const out = await this.session.run(feeds);
    const wave = out[io.output] || out[Object.keys(out)[0]];
    return { samples: Float32Array.from(wave.data), sampleRate: this.sampleRate };
  }
}

export default KokoroSession;
