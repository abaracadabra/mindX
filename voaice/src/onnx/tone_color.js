/**
 * tone_color.js — speaker embedding + tone-color conversion (Stage 2: "clones voices").
 *
 * OpenVoice-v2 style, exported to ONNX, CPU/torch-free. Two graphs:
 *   - speaker encoder:  reference mel/waveform -> speaker embedding (the "clone token")
 *   - tone-color converter: (base waveform, source embedding, target embedding) -> recoloured waveform
 *
 * The base "talk" voice comes from KokoroSession; this re-colours its timbre onto the
 * cloned speaker. Artefacts are fetched separately and never committed. Absent weights =>
 * graceful error so callers degrade to the un-cloned base voice.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createSession, tensor } from './runtime.js';
import { magnitudeSpectrum } from '../dsp/fft.js';

export class ToneColorConverter {
  /**
   * @param {{ modelDir: string }} opts
   *   modelDir contains: tone_encoder.onnx, tone_converter.onnx, tone_color.json
   */
  constructor(opts) {
    this.modelDir = opts.modelDir;
    this.encoder = null;
    this.converter = null;
    this.cfg = null;
  }

  encoderPath() {
    return join(this.modelDir, 'tone_encoder.onnx');
  }
  converterPath() {
    return join(this.modelDir, 'tone_converter.onnx');
  }
  configPath() {
    return join(this.modelDir, 'tone_color.json');
  }

  isCached() {
    return [this.encoderPath(), this.converterPath(), this.configPath()].every(existsSync);
  }

  async load() {
    if (this.encoder && this.converter) return;
    if (!this.isCached()) {
      throw new Error(
        `voaice neural: tone-color weights not found in ${this.modelDir}. ` +
          'Run `npm run fetch-models` to enable voice cloning (Stage 2).'
      );
    }
    this.cfg = JSON.parse(readFileSync(this.configPath(), 'utf8'));
    this.encoder = await createSession(this.encoderPath());
    this.converter = await createSession(this.converterPath());
  }

  /**
   * Compute a log-magnitude spectrogram feature for the encoder. Reuses voaice's in-house
   * FFT (no new dep). Frame/hop come from config to match the export.
   */
  _spectrogram(samples) {
    const fftSize = this.cfg.fftSize || 1024;
    const hop = this.cfg.hop || 256;
    const cols = [];
    for (let start = 0; start + fftSize <= samples.length; start += hop) {
      const frame = new Float32Array(fftSize);
      for (let i = 0; i < fftSize; i++) frame[i] = samples[start + i];
      // magnitudeSpectrum applies a Hann window and sizes to nextPow2 internally
      const mag = magnitudeSpectrum(frame);
      cols.push(Float32Array.from(mag, (m) => Math.log(m + 1e-6)));
    }
    const bins = cols.length ? cols[0].length : 0;
    const flat = new Float32Array(cols.length * bins);
    cols.forEach((c, i) => flat.set(c, i * bins));
    return { flat, frames: cols.length, bins };
  }

  /**
   * Extract a speaker embedding from reference samples.
   * @param {Float32Array} samples
   * @returns {Promise<Float32Array>} embedding (the clone token)
   */
  async extractEmbedding(samples) {
    await this.load();
    const io = this.cfg.encoderIo || { input: 'spec', output: 'embedding' };
    const { flat, frames, bins } = this._spectrogram(samples);
    const feeds = { [io.input]: await tensor('float32', flat, [1, frames, bins]) };
    const out = await this.encoder.run(feeds);
    const emb = out[io.output] || out[Object.keys(out)[0]];
    return Float32Array.from(emb.data);
  }

  /**
   * Recolour a base waveform from a source embedding to a target (cloned) embedding.
   * @param {Float32Array} baseWave  output of the base TTS
   * @param {Float32Array} srcEmb    base voice embedding
   * @param {Float32Array} tgtEmb    cloned speaker embedding
   * @returns {Promise<Float32Array>} recoloured waveform
   */
  async convert(baseWave, srcEmb, tgtEmb) {
    await this.load();
    const io = this.cfg.converterIo || {
      audio: 'audio',
      src: 'src_emb',
      tgt: 'tgt_emb',
      output: 'audio_out',
    };
    const feeds = {
      [io.audio]: await tensor('float32', Float32Array.from(baseWave), [1, baseWave.length]),
      [io.src]: await tensor('float32', Float32Array.from(srcEmb), [1, srcEmb.length]),
      [io.tgt]: await tensor('float32', Float32Array.from(tgtEmb), [1, tgtEmb.length]),
    };
    const out = await this.converter.run(feeds);
    const wave = out[io.output] || out[Object.keys(out)[0]];
    return Float32Array.from(wave.data);
  }
}

export default ToneColorConverter;
