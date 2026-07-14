/**
 * TTS.js — text to speech, as a module.
 *
 * One façade over every synthesis path voaice can reach, ordered by quality and
 * resolved at runtime against what the host actually has:
 *
 *   neural   — voaice's torch-free ONNX engine (cloned voices, best quality)
 *   native   — the OS speech binaries: espeak-ng · festival · flite · pico2wave
 *              · spd-say (Linux) · say (macOS) · piper (if installed)
 *   formant  — voaice's in-house formant synthesiser (zero dependencies)
 *
 * The formant floor is what makes this module honest: there is ALWAYS a voice.
 * A host with no speech binaries and no model weights still speaks — audibly
 * synthetic, clearly labelled, never silently failing. `capability()` reports
 * exactly which paths exist before you commit to one.
 *
 * Everything returns the canonical clip — `{ samples: Float32Array, sampleRate }` —
 * so TTS output flows straight into VoiceShaper, Editor, Forensic and Exporter
 * with no glue.
 *
 *   import { TTS } from 'voaice/tts';
 *   const tts = new TTS({ engine: 'auto', voice: 'jaimla' });
 *   const clip = await tts.speak('the machine speaks for itself');
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { spawn, spawnSync } from 'node:child_process';
import { readFile, unlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { EventEmitter } from 'node:events';
import { decodeWav } from '../audio/wav.js';
import { FormantTTS } from './formant.js';

/** Native engines, best-first. Each declares how to render text → a WAV file. */
export const NATIVE_ENGINES = {
  piper: {
    binary: 'piper',
    // piper reads text on stdin and writes a wav; model path comes from opts.model
    args: ({ out, model }) => ['--model', model || 'en_US-lessac-medium.onnx', '--output_file', out],
    stdin: true,
    quality: 'high',
  },
  'espeak-ng': {
    binary: 'espeak-ng',
    args: ({ text, out, rate, pitch, voice }) => [
      '-w', out, '-s', String(Math.round(rate ?? 165)), '-p', String(Math.round(pitch ?? 50)),
      '-v', voice || 'en', text,
    ],
    quality: 'low',
  },
  espeak: {
    binary: 'espeak',
    args: ({ text, out, rate, pitch }) => ['-w', out, '-s', String(Math.round(rate ?? 165)), '-p', String(Math.round(pitch ?? 50)), text],
    quality: 'low',
  },
  flite: {
    binary: 'flite',
    args: ({ text, out }) => ['-t', text, '-o', out],
    quality: 'medium',
  },
  pico2wave: {
    binary: 'pico2wave',
    args: ({ text, out, lang }) => ['-l', lang || 'en-US', '-w', out, text],
    quality: 'medium',
  },
  say: {
    binary: 'say', // macOS
    args: ({ text, out, voice, rate }) => [
      '-o', out, '--data-format=LEF32@22050', ...(voice ? ['-v', voice] : []),
      ...(rate ? ['-r', String(Math.round(rate))] : []), text,
    ],
    quality: 'high',
  },
  festival: {
    binary: 'text2wave',
    args: ({ out }) => ['-o', out],
    stdin: true,
    quality: 'medium',
  },
};

const _probed = new Map();
/** Is a binary on PATH? (memoised) */
export function hasBinary(bin) {
  if (!_probed.has(bin)) {
    let ok = false;
    try {
      ok = spawnSync('sh', ['-c', `command -v ${bin}`], { stdio: 'ignore' }).status === 0;
    } catch { ok = false; }
    _probed.set(bin, ok);
  }
  return _probed.get(bin);
}

/** Which native engines exist on this host, best-first. */
export function nativeEngines() {
  return Object.entries(NATIVE_ENGINES)
    .filter(([, e]) => hasBinary(e.binary))
    .map(([name, e]) => ({ name, binary: e.binary, quality: e.quality }));
}

export class TTS extends EventEmitter {
  /**
   * @param {{engine?:'auto'|'neural'|'native'|'formant'|string, voice?:string,
   *          sampleRate?:number, rate?:number, pitch?:number, model?:string,
   *          modelDir?:string, lang?:string}} [opts]
   */
  constructor(opts = {}) {
    super();
    this.engine = opts.engine || 'auto';
    this.voice = opts.voice || 'default';
    this.sampleRate = opts.sampleRate || 24000;
    this.rate = opts.rate;
    this.pitch = opts.pitch;
    this.model = opts.model;
    this.modelDir = opts.modelDir;
    this.lang = opts.lang;
    this._neural = null;
    this._formant = null;
  }

  /** What can this host actually synthesize with? Honest, no guessing. */
  async capability() {
    const native = nativeEngines();
    let neural = false;
    try {
      const { NeuralVoiceEngine } = await import('../NeuralVoiceEngine.js');
      const probe = new NeuralVoiceEngine({ voiceId: this.voice, modelDir: this.modelDir });
      neural = typeof probe.synthesize === 'function';
    } catch { neural = false; }
    return {
      neural, // present as a code path; weights may still be absent (it degrades internally)
      native: native.map((n) => n.name),
      formant: true, // always — the in-house floor
      resolved: this._resolve(native, neural),
    };
  }

  _resolve(native, neural) {
    if (this.engine === 'neural') return 'neural';
    if (this.engine === 'formant') return 'formant';
    if (this.engine === 'native') return native.length ? native[0].name : 'formant';
    if (NATIVE_ENGINES[this.engine]) return this.engine;
    // auto: neural → best native → formant
    if (neural) return 'neural';
    if (native.length) return native[0].name;
    return 'formant';
  }

  /**
   * Speak. Returns the canonical clip plus which engine actually produced it —
   * a caller can always tell what it got, and grade accordingly.
   * @param {string} text
   * @param {{voice?:string, rate?:number, pitch?:number, emotion?:string}} [opts]
   * @returns {Promise<{samples:Float32Array, sampleRate:number, engine:string, text:string}>}
   */
  async speak(text, opts = {}) {
    if (!text || !String(text).trim()) throw new Error('TTS: nothing to speak');
    const cap = await this.capability();
    const engine = opts.engine || cap.resolved;
    this.emit('speaking', { text, engine });

    let clip;
    if (engine === 'neural') clip = await this._neuralSpeak(text, opts);
    else if (engine === 'formant') clip = this._formantSpeak(text, opts);
    else clip = await this._nativeSpeak(engine, text, opts);

    const out = { ...clip, engine, text };
    this.emit('spoke', { engine, samples: out.samples.length, sampleRate: out.sampleRate });
    return out;
  }

  async _neuralSpeak(text, opts) {
    if (!this._neural) {
      const { NeuralVoiceEngine } = await import('../NeuralVoiceEngine.js');
      this._neural = new NeuralVoiceEngine({
        voiceId: opts.voice || this.voice,
        modelDir: this.modelDir,
      });
      if (typeof this._neural.init === 'function') await this._neural.init().catch(() => {});
    }
    const res = await this._neural.synthesize({
      text,
      voiceId: opts.voice || this.voice,
      emotion: opts.emotion,
      write: false,
    });
    // The engine returns WAV bytes or a clip; normalise both.
    if (res?.samples) return { samples: res.samples, sampleRate: res.sampleRate || this.sampleRate };
    const buf = res?.wav || res?.buffer || res;
    const dec = decodeWav(Buffer.isBuffer(buf) ? buf : Buffer.from(buf));
    return { samples: dec.samples, sampleRate: dec.sampleRate };
  }

  _formantSpeak(text, opts) {
    if (!this._formant) this._formant = new FormantTTS({ sampleRate: this.sampleRate });
    const samples = this._formant.synthesize
      ? this._formant.synthesize(text, { pitch: opts.pitch ?? this.pitch, rate: opts.rate ?? this.rate })
      : this._formant.speak(text);
    const arr = samples?.samples || samples;
    return { samples: Float32Array.from(arr), sampleRate: this.sampleRate };
  }

  async _nativeSpeak(name, text, opts) {
    const cfg = NATIVE_ENGINES[name];
    if (!cfg) throw new Error(`TTS: unknown native engine "${name}"`);
    if (!hasBinary(cfg.binary)) throw new Error(`TTS: ${cfg.binary} is not installed`);
    const out = join(tmpdir(), `voaice-tts-${process.pid}-${Date.now()}.wav`);
    const args = cfg.args({
      text, out,
      voice: opts.voice || (this.voice === 'default' ? undefined : this.voice),
      rate: opts.rate ?? this.rate,
      pitch: opts.pitch ?? this.pitch,
      model: this.model,
      lang: this.lang,
    });
    await new Promise((resolve, reject) => {
      const p = spawn(cfg.binary, args, { stdio: cfg.stdin ? ['pipe', 'ignore', 'pipe'] : ['ignore', 'ignore', 'pipe'] });
      const err = [];
      p.stderr?.on('data', (d) => err.push(d));
      p.on('error', reject);
      p.on('close', (code) =>
        code === 0 ? resolve() : reject(new Error(`${cfg.binary} exited ${code}: ${Buffer.concat(err).toString().slice(0, 200)}`))
      );
      if (cfg.stdin) p.stdin.end(text);
    });
    const wav = await readFile(out);
    await unlink(out).catch(() => {});
    const dec = decodeWav(wav);
    return { samples: dec.samples, sampleRate: dec.sampleRate };
  }
}

export default TTS;
