/**
 * python_speech.js — the Node bridge to voaice's Python TTS/STT tools.
 *
 * The voaice core is torch-free JS DSP; some speech stacks only exist in Python
 * (Coqui TTS, whisper, vosk…). This wraps `python/voaice_speech.py` so a Node
 * caller can reach them — with the same honesty the rest of voaice keeps:
 * capability is probed first, and a missing engine is a clear error, never a
 * fabricated result.
 *
 *   import { PythonSpeech } from 'voaice/python';
 *   const py = new PythonSpeech();
 *   const cap = await py.capability();          // { tts:{available,resolved}, stt:{...} }
 *   if (cap.tts.resolved) await py.tts('hello', 'out.wav');
 *   if (cap.stt.resolved) { const { text } = await py.stt('clip.wav'); }
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const SCRIPT = resolve(dirname(fileURLToPath(import.meta.url)), '../python/voaice_speech.py');

export class PythonSpeech {
  /** @param {{python?:string, script?:string}} [opts] */
  constructor(opts = {}) {
    this.python = opts.python || process.env.VOAICE_PYTHON || 'python3';
    this.script = opts.script || SCRIPT;
    this._cap = null;
  }

  /** Run the tool and parse its JSON. Rejects with the tool's {error} message. */
  _run(args) {
    return new Promise((res, rej) => {
      let out = '';
      let err = '';
      let p;
      try {
        p = spawn(this.python, [this.script, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
      } catch (e) {
        return rej(new Error(`python speech: cannot spawn ${this.python} (${e.message})`));
      }
      p.stdout.on('data', (d) => (out += d));
      p.stderr.on('data', (d) => (err += d));
      p.on('error', (e) => rej(new Error(`python speech: ${e.message} — is ${this.python} on PATH?`)));
      p.on('close', (code) => {
        const body = (out || err).trim();
        let json = null;
        try { json = body ? JSON.parse(body.split('\n').pop()) : null; } catch { /* non-JSON */ }
        if (code === 0) return res(json ?? {});
        rej(new Error(json?.error || body || `python speech exited ${code}`));
      });
    });
  }

  /** What Python TTS/STT engines does this host have? Memoised. */
  async capability() {
    if (!this._cap) this._cap = await this._run(['capability']);
    return this._cap;
  }

  /** True if any Python TTS (or STT) engine is installed. */
  async available() {
    const c = await this.capability().catch(() => null);
    return { tts: !!c?.tts?.resolved, stt: !!c?.stt?.resolved, python: c?.python || null };
  }

  /**
   * Text → speech. Writes `out` (a .wav) and returns { engine, out, text }.
   * @param {string} text
   * @param {string} out  output path
   * @param {{engine?:string, voice?:string, rate?:number}} [opts]
   */
  async tts(text, out, opts = {}) {
    if (!text || !String(text).trim()) throw new Error('python tts: nothing to speak');
    const args = ['tts', '--text', String(text), '--out', out];
    if (opts.engine) args.push('--engine', opts.engine);
    if (opts.voice) args.push('--voice', String(opts.voice));
    if (opts.rate) args.push('--rate', String(opts.rate));
    return this._run(args);
  }

  /**
   * Speech → text. Returns { engine, text, language, audio }. Throws (never
   * fabricates) when no recogniser is installed.
   * @param {string} wavPath  16 kHz mono WAV
   * @param {{engine?:string, model?:string, language?:string}} [opts]
   */
  async stt(wavPath, opts = {}) {
    const args = ['stt', '--in', wavPath];
    if (opts.engine) args.push('--engine', opts.engine);
    if (opts.model) args.push('--model', opts.model);
    if (opts.language) args.push('--language', opts.language);
    return this._run(args);
  }
}

export default PythonSpeech;
