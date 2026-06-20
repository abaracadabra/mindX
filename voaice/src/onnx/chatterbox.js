/**
 * chatterbox.js — emotion-capable TTS backend (Resemble AI Chatterbox, ONNX/CPU).
 *
 * Chatterbox is the open TTS with built-in EMOTION control: a continuous `exaggeration` scalar
 * (0..1, 0.5 = neutral), `cfg_weight` (pacing), `temperature`, and Turbo's `[laugh]`/`[chuckle]`/
 * `[cough]` tags. A torch-free ONNX port exists (`onnx-community/chatterbox-ONNX`, MIT) that
 * preserves `exaggeration` — but it is a 0.5B autoregressive LM TTS and is **slow on CPU**
 * (offline/batch, NOT live). So this backend is opt-in and used only when emotion is requested.
 *
 * The ONNX export is FOUR graphs (speech encoder, embed/tokens, LM with KV-cache, conditional
 * decoder) driven by an autoregressive loop. Wiring that loop in JS is substantial; this wrapper
 * detects the bundle + exposes the parameter surface, and runs only when a port that bundles a
 * callable `generate` graph is present — otherwise it reports unavailable so the engine falls back.
 * It is honest-experimental, in the spirit of the tone-color wrapper.
 *
 * Bundle (fetched separately, never committed — see MODELS.md): models/chatterbox/
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tryLoadOrt, createSession, tensor } from './runtime.js';

export class ChatterboxVoice {
  /** @param {{ modelDir:string }} opts */
  constructor(opts) {
    this.modelDir = join(opts.modelDir, 'chatterbox');
    this.cfg = null;
    this.session = null;
  }

  configPath() {
    return join(this.modelDir, 'chatterbox.json');
  }

  /** True when the bundle + a runnable config are present. */
  isCached() {
    // require the config and at least a decoder graph; the config declares the callable surface
    return existsSync(this.configPath()) && existsSync(join(this.modelDir, 'decoder.onnx'));
  }

  async available() {
    return this.isCached() && !!(await tryLoadOrt());
  }

  async load() {
    if (this.session) return;
    if (!this.isCached()) {
      throw new Error(
        `voaice neural: Chatterbox bundle not found in ${this.modelDir}. ` +
          'Run `npm run fetch-models -- chatterbox` (ONNX, torch-free, MIT — slow on CPU).'
      );
    }
    this.cfg = JSON.parse(readFileSync(this.configPath(), 'utf8'));
    // A merged/callable single-graph export exposes cfg.io.model; the multi-graph AR port does not.
    if (!this.cfg.io || !this.cfg.io.model) {
      throw new Error(
        'voaice neural: this Chatterbox ONNX port is the multi-graph autoregressive export; the ' +
          'JS AR decode loop is not implemented. Use a merged-graph export (cfg.io.model) or run ' +
          'Chatterbox as an offline sidecar. Emotion CONTROL + FACE display work regardless.'
      );
    }
    this.session = await createSession(join(this.modelDir, this.cfg.io.model));
  }

  listExpressiveKnobs() {
    return ['exaggeration', 'cfg_weight', 'temperature'];
  }

  /**
   * Emotive synthesis. `exaggeration` is Chatterbox's emotion-intensity dial.
   * @param {{ text:string, exaggeration?:number, cfg_weight?:number, temperature?:number,
   *           refSamples?:Float32Array, refSampleRate?:number }} req
   * @returns {Promise<{ samples:Float32Array, sampleRate:number }>}
   */
  async synth(req) {
    await this.load();
    const io = this.cfg.io;
    const sr = this.cfg.sampleRate || 24000;
    const feeds = {
      [io.text]: await tensor('string', [req.text], [1]),
      [io.exaggeration]: await tensor('float32', Float32Array.from([req.exaggeration ?? 0.5]), [1]),
      [io.cfg]: await tensor('float32', Float32Array.from([req.cfg_weight ?? 0.5]), [1]),
    };
    if (io.temperature) {
      feeds[io.temperature] = await tensor('float32', Float32Array.from([req.temperature ?? 0.8]), [1]);
    }
    const out = await this.session.run(feeds);
    const wave = out[io.output] || out[Object.keys(out)[0]];
    return { samples: Float32Array.from(wave.data), sampleRate: sr };
  }
}

export default ChatterboxVoice;
