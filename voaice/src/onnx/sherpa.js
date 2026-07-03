/**
 * sherpa.js — the real, production CPU TTS + zero-shot cloning backend.
 *
 * Thin wrapper over `sherpa-onnx-node` (k2-fsa/sherpa-onnx, Apache-2.0): a C++ binding over
 * ONNX Runtime — no torch, no Python, CPU `provider: 'cpu'`. It subsumes Kokoro's raw
 * input_ids/style/speed I/O (and bundles espeak-ng-data, so no system espeak-ng is needed),
 * and it exposes genuine zero-shot cloning via ZipVoice (reference WAV + transcript + numSteps).
 *
 * Two model bundles, fetched separately into ./models (never committed — see MODELS.md):
 *   models/kokoro/   model.onnx, voices.bin, tokens.txt, espeak-ng-data/   (preset voices)
 *   models/zipvoice/ encoder.onnx, decoder.onnx, vocoder.onnx, tokens.txt, espeak-ng-data/, lexicon.txt (clone)
 *
 * `sherpa-onnx-node` is an optionalDependency loaded lazily; absent runtime or weights => the
 * NeuralVoiceEngine degrades to the raw-onnx wrappers or the dependency-free fallback.
 */

import { existsSync } from 'node:fs';
import { join } from 'node:path';

let _sherpa = null;
let _probed = false;

/** Lazily resolve sherpa-onnx-node, or null if not installed. */
export async function tryLoadSherpa() {
  if (_probed) return _sherpa;
  _probed = true;
  try {
    const mod = await import('sherpa-onnx-node');
    _sherpa = mod.default || mod;
  } catch {
    _sherpa = null;
  }
  return _sherpa;
}

export class SherpaVoice {
  /**
   * @param {{ modelDir: string, numThreads?: number }} opts
   */
  constructor(opts) {
    this.modelDir = opts.modelDir;
    this.numThreads = opts.numThreads || 1;
    this._tts = { kokoro: null, zipvoice: null };
  }

  kokoroDir() {
    return join(this.modelDir, 'kokoro');
  }
  zipvoiceDir() {
    return join(this.modelDir, 'zipvoice');
  }

  /** Preset-voice (Kokoro) bundle present? */
  hasKokoro() {
    const d = this.kokoroDir();
    return ['model.onnx', 'voices.bin', 'tokens.txt'].every((f) => existsSync(join(d, f)));
  }

  /**
   * Zero-shot clone (ZipVoice) bundle present AND loadable?
   * The zh-en distill model REQUIRES lexicon.txt — sherpa's C-API hard-aborts the whole process if
   * it is missing ("Please provide lexicon.txt"). So we require lexicon.txt here: without it we
   * report ZipVoice unavailable (clone falls back to the forensic 18-dp voiceprint) rather than
   * crash the server. ZipVoice is also far slower than realtime on CPU — GPU-territory regardless.
   */
  hasZipVoice() {
    const d = this.zipvoiceDir();
    const enc = existsSync(join(d, 'text_encoder_int8.onnx')) || existsSync(join(d, 'text_encoder.onnx'));
    const dec = existsSync(join(d, 'fm_decoder_int8.onnx')) || existsSync(join(d, 'fm_decoder.onnx'));
    const loadable = existsSync(join(d, 'lexicon.txt')); // required by this model; absent → don't load
    return enc && dec && existsSync(join(d, 'vocos_24khz.onnx')) && existsSync(join(d, 'tokens.txt')) && loadable;
  }

  async _kokoro() {
    if (this._tts.kokoro) return this._tts.kokoro;
    const sherpa = await tryLoadSherpa();
    if (!sherpa) throw new Error('voaice neural: sherpa-onnx-node not installed');
    if (!this.hasKokoro()) throw new Error(`voaice neural: Kokoro bundle missing in ${this.kokoroDir()}`);
    const d = this.kokoroDir();
    this._tts.kokoro = new sherpa.OfflineTts({
      model: {
        kokoro: {
          model: join(d, 'model.onnx'),
          voices: join(d, 'voices.bin'),
          tokens: join(d, 'tokens.txt'),
          dataDir: join(d, 'espeak-ng-data'),
        },
        numThreads: this.numThreads,
        provider: 'cpu',
        debug: false,
      },
      maxNumSentences: 1,
    });
    return this._tts.kokoro;
  }

  async _zipvoice() {
    if (this._tts.zipvoice) return this._tts.zipvoice;
    const sherpa = await tryLoadSherpa();
    if (!sherpa) throw new Error('voaice neural: sherpa-onnx-node not installed');
    if (!this.hasZipVoice()) throw new Error(`voaice neural: ZipVoice bundle missing in ${this.zipvoiceDir()}`);
    const d = this.zipvoiceDir();
    const pick = (a, b) => (existsSync(join(d, a)) ? join(d, a) : join(d, b));
    const lexicon = join(d, 'lexicon.txt');
    // sherpa-onnx zipvoice config: tokens + textEncoder + decoder (flow-matching) + vocoder + dataDir.
    // Prefer the int8 graphs for CPU speed; the distill bundle ships fp32 + int8.
    this._tts.zipvoice = new sherpa.OfflineTts({
      model: {
        zipvoice: {
          tokens: join(d, 'tokens.txt'),
          // config field is `encoder` (the text encoder) / `decoder` (the flow-matching decoder);
          // bundle files are text_encoder*.onnx / fm_decoder*.onnx — int8 preferred for CPU.
          encoder: pick('text_encoder_int8.onnx', 'text_encoder.onnx'),
          decoder: pick('fm_decoder_int8.onnx', 'fm_decoder.onnx'),
          vocoder: join(d, 'vocos_24khz.onnx'),
          dataDir: join(d, 'espeak-ng-data'),
          ...(existsSync(lexicon) ? { lexicon } : {}),
        },
        numThreads: Math.max(2, this.numThreads),
        provider: 'cpu',
        debug: false,
      },
      maxNumSentences: 1,
    });
    return this._tts.zipvoice;
  }

  /**
   * Preset-voice synthesis (Kokoro).
   * @param {{ text:string, sid?:number, speed?:number }} req
   * @returns {Promise<{ samples: Float32Array, sampleRate: number }>}
   */
  async speakPreset(req) {
    const sherpa = await tryLoadSherpa();
    const tts = await this._kokoro();
    const audio = tts.generate({
      text: req.text,
      generationConfig: new sherpa.GenerationConfig({ sid: req.sid || 0, speed: req.speed || 1.0 }),
    });
    return { samples: Float32Array.from(audio.samples), sampleRate: audio.sampleRate };
  }

  /**
   * Zero-shot cloned synthesis (ZipVoice). Needs the reference audio AND its transcript.
   * @param {{ text:string, refSamples:Float32Array, refSampleRate:number, refText:string, numSteps?:number, speed?:number }} req
   * @returns {Promise<{ samples: Float32Array, sampleRate: number }>}
   */
  async speakCloned(req) {
    const sherpa = await tryLoadSherpa();
    const tts = await this._zipvoice();
    const audio = tts.generate({
      text: req.text,
      generationConfig: new sherpa.GenerationConfig({
        speed: req.speed || 1.0,
        referenceAudio: Float32Array.from(req.refSamples),
        referenceSampleRate: req.refSampleRate,
        referenceText: req.refText,
        numSteps: req.numSteps || 4,
      }),
    });
    return { samples: Float32Array.from(audio.samples), sampleRate: audio.sampleRate };
  }
}

export default SherpaVoice;
