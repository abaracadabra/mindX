/**
 * STT.js — speech to text, as a module.
 *
 * One façade over the recognisers a host may have, resolved at runtime:
 *
 *   whisper.cpp  — `whisper-cli` / `whisper-cpp` / `main` (ggml, CPU, torch-free)
 *   vosk         — `vosk-transcriber` (offline, small models)
 *   sherpa-onnx  — via voaice's existing ONNX runtime seam (torch-free)
 *   ffmpeg       — used only to normalise input to 16 kHz mono for the above
 *
 * THE HONESTY RULE: if no recogniser is present, this module does NOT invent a
 * transcript. `transcribe()` throws with a clear install hint, and `available()`
 * says false BEFORE you commit to a pipeline. A wrong transcript is worse than
 * no transcript — it silently poisons everything downstream.
 *
 * What IS always available, with zero dependencies, is `segment()`: VAD-driven
 * utterance segmentation with timings, energy, and per-segment SNR. That is not
 * transcription and never pretends to be — it is the honest floor: *where* the
 * speech is, how much of it there is, and whether it is clean enough to be worth
 * transcribing at all.
 *
 *   import { STT } from 'voaice/stt';
 *   const stt = new STT();
 *   if ((await stt.available()).any) {
 *     const { text, segments } = await stt.transcribe(clip);
 *   } else {
 *     const segments = stt.segment(clip);   // always works
 *   }
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { spawn, spawnSync } from 'node:child_process';
import { readFile, unlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { EventEmitter } from 'node:events';
import { encodeWav } from '../audio/wav.js';
import { voicedFrames } from '../audio/vad.js';
import { snr } from '../dsp/noise.js';

const _bin = new Map();
const hasBinary = (b) => {
  if (!_bin.has(b)) {
    let ok = false;
    try { ok = spawnSync('sh', ['-c', `command -v ${b}`], { stdio: 'ignore' }).status === 0; } catch { ok = false; }
    _bin.set(b, ok);
  }
  return _bin.get(b);
};

/** Recognisers, best-first. */
export const ENGINES = {
  'whisper.cpp': {
    binaries: ['whisper-cli', 'whisper-cpp', 'whisper'],
    hint: 'build whisper.cpp (github.com/ggerganov/whisper.cpp) and put whisper-cli on PATH, plus a ggml model',
    quality: 'high',
  },
  vosk: {
    binaries: ['vosk-transcriber'],
    hint: 'pip install vosk && download a model (alphacephei.com/vosk/models)',
    quality: 'medium',
  },
  'sherpa-onnx': {
    binaries: ['sherpa-onnx-offline'],
    hint: 'install sherpa-onnx (torch-free ONNX ASR) + an offline transducer model',
    quality: 'high',
  },
};

export class STT extends EventEmitter {
  /**
   * @param {{engine?:'auto'|string, model?:string, language?:string, threads?:number}} [opts]
   *   model — path to the ggml/vosk/sherpa model (required by every native engine)
   */
  constructor(opts = {}) {
    super();
    this.engine = opts.engine || 'auto';
    this.model = opts.model || process.env.VOAICE_STT_MODEL || null;
    this.language = opts.language || 'en';
    this.threads = opts.threads || 4;
  }

  /** Which recognisers exist here? `any:false` means transcription is impossible — believe it. */
  async available() {
    const found = {};
    for (const [name, e] of Object.entries(ENGINES)) {
      const bin = e.binaries.find((b) => hasBinary(b));
      if (bin) found[name] = { binary: bin, quality: e.quality, model: this.model };
    }
    const names = Object.keys(found);
    return {
      any: names.length > 0,
      engines: found,
      resolved: this.engine !== 'auto' && found[this.engine] ? this.engine : names[0] || null,
      modelConfigured: !!this.model,
      // segmentation needs nothing at all
      segmentation: true,
      hints: names.length ? [] : Object.entries(ENGINES).map(([n, e]) => `${n}: ${e.hint}`),
    };
  }

  /**
   * Utterance segmentation — the zero-dependency floor. Where the speech is,
   * how loud, how clean. Never claims to be a transcript.
   * @param {{samples:Float32Array, sampleRate:number}} clip
   * @returns {{segments:Array<{startSec,endSec,durationSec,rms,snrDb}>, speechSec:number, totalSec:number, snr:object}}
   */
  segment(clip, opts = {}) {
    const { samples, sampleRate } = clip;
    const { frames, frameLen, hop } = voicedFrames(samples, sampleRate, opts);
    const minGapSec = opts.minGapSec ?? 0.3;
    const minSegSec = opts.minSegSec ?? 0.15;

    const segs = [];
    let cur = null;
    for (const f of frames) {
      if (f.voiced) {
        if (!cur) cur = { start: f.start, end: f.start + frameLen };
        else cur.end = f.start + frameLen;
      } else if (cur && (f.start - cur.end) / sampleRate > minGapSec) {
        segs.push(cur);
        cur = null;
      }
    }
    if (cur) segs.push(cur);

    const out = segs
      .filter((s) => (s.end - s.start) / sampleRate >= minSegSec)
      .map((s) => {
        const seg = samples.subarray(s.start, Math.min(samples.length, s.end));
        let acc = 0;
        for (let i = 0; i < seg.length; i++) acc += seg[i] * seg[i];
        const r = Math.sqrt(acc / Math.max(1, seg.length));
        let segSnr = null;
        try { segSnr = snr(seg, sampleRate).snrDb; } catch { /* short segment */ }
        return {
          startSec: s.start / sampleRate,
          endSec: s.end / sampleRate,
          durationSec: (s.end - s.start) / sampleRate,
          rms: r,
          snrDb: segSnr,
        };
      });

    const speechSec = out.reduce((a, s) => a + s.durationSec, 0);
    return {
      segments: out,
      speechSec,
      totalSec: samples.length / sampleRate,
      snr: snr(samples, sampleRate),
      hop,
      note: 'segmentation only — not a transcript',
    };
  }

  /**
   * Transcribe. Throws (with an install hint) when no recogniser exists — it
   * will not fabricate text.
   * @param {{samples:Float32Array, sampleRate:number}} clip
   * @returns {Promise<{text:string, engine:string, segments:Array, language:string}>}
   */
  async transcribe(clip, opts = {}) {
    const cap = await this.available();
    if (!cap.any) {
      throw new Error(
        'STT: no speech recogniser on this host — refusing to invent a transcript.\n' +
          cap.hints.map((h) => '  · ' + h).join('\n') +
          '\n  (stt.segment() works with zero dependencies and tells you where the speech is.)'
      );
    }
    const name = opts.engine || cap.resolved;
    const eng = cap.engines[name];
    if (!eng) throw new Error(`STT: engine "${name}" is not available here`);
    const model = opts.model || this.model;
    if (!model) {
      throw new Error(
        `STT: ${name} needs a model — pass { model } or set VOAICE_STT_MODEL. ${ENGINES[name].hint}`
      );
    }

    // Every native recogniser wants 16 kHz mono PCM.
    const wav = encodeWav(this._to16k(clip).samples, 16000, { bitDepth: 16 });
    const path = join(tmpdir(), `voaice-stt-${process.pid}-${Date.now()}.wav`);
    await writeFile(path, wav);
    this.emit('transcribing', { engine: name, seconds: clip.samples.length / clip.sampleRate });

    try {
      const text = await this._run(name, eng.binary, path, model, opts);
      return {
        text: text.trim(),
        engine: name,
        language: opts.language || this.language,
        segments: this.segment(clip).segments,
      };
    } finally {
      await unlink(path).catch(() => {});
    }
  }

  _to16k(clip) {
    if (clip.sampleRate === 16000) return clip;
    const ratio = clip.sampleRate / 16000;
    const n = Math.max(1, Math.round(clip.samples.length / ratio));
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const pos = i * ratio;
      const i0 = Math.floor(pos);
      const i1 = Math.min(clip.samples.length - 1, i0 + 1);
      out[i] = clip.samples[i0] + (clip.samples[i1] - clip.samples[i0]) * (pos - i0);
    }
    return { samples: out, sampleRate: 16000 };
  }

  async _run(name, binary, wavPath, model, opts) {
    const args =
      name === 'whisper.cpp'
        ? ['-m', model, '-f', wavPath, '-l', opts.language || this.language, '-t', String(this.threads), '-nt', '-otxt', '-of', wavPath]
        : name === 'vosk'
          ? ['--model', model, '--input', wavPath, '--output', '-']
          : ['--tokens', `${model}/tokens.txt`, '--encoder', `${model}/encoder.onnx`,
             '--decoder', `${model}/decoder.onnx`, '--joiner', `${model}/joiner.onnx`, wavPath];

    const stdout = await new Promise((resolve, reject) => {
      const p = spawn(binary, args, { stdio: ['ignore', 'pipe', 'pipe'] });
      const out = [];
      const err = [];
      p.stdout.on('data', (d) => out.push(d));
      p.stderr.on('data', (d) => err.push(d));
      p.on('error', reject);
      p.on('close', (code) =>
        code === 0
          ? resolve(Buffer.concat(out).toString())
          : reject(new Error(`${binary} exited ${code}: ${Buffer.concat(err).toString().slice(0, 300)}`))
      );
    });

    if (name === 'whisper.cpp') {
      // -otxt writes <wavPath>.txt; prefer it, fall back to stdout
      try {
        const txt = await readFile(`${wavPath}.txt`, 'utf8');
        await unlink(`${wavPath}.txt`).catch(() => {});
        if (txt.trim()) return txt;
      } catch { /* fall through */ }
    }
    return stdout;
  }
}

export default STT;
