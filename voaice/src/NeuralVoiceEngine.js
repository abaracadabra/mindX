/**
 * NeuralVoiceEngine.js — torch-free neural TTS + zero-shot voice cloning.
 *
 * The neural peer of VoiceCreationEngine (which wraps OS TTS binaries). This engine speaks
 * via a small ONNX base model (Kokoro-82M, Stage 1) and clones a target timbre via an
 * OpenVoice-style tone-color converter (Stage 2). Everything runs on CPU through
 * onnxruntime-node — no torch, no transformers, no Python. VPS-safe.
 *
 * Graceful degradation is a first-class feature: when the ONNX runtime or the model weights
 * are absent (e.g. a fresh checkout, or CI), `synthesize()` still returns valid WAV bytes via
 * a dependency-free fallback source so the whole pipeline — server routes, voicey2 provider,
 * faicey bridge, tests — works offline. The fallback is a persona-tinted tone, NOT speech;
 * `.backend` on every result says which path produced the audio so callers never guess.
 *
 *   import { NeuralVoiceEngine } from 'voaice/neural';
 *   const eng = new NeuralVoiceEngine({ voiceId: 'jaimla' });
 *   await eng.init();
 *   const { buffer, backend } = await eng.synthesize({ text: 'hello, I am jaimla' });
 *
 * Cloning reuses Scientific.js so every clone also yields a registerable 18-dp voiceprint.
 */

import { EventEmitter } from 'node:events';
import { promises as fs } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

import { encodeWav, decodeWav } from './audio/wav.js';
import { normalizeToLufs } from './audio/loudness.js';
import { trimSilence } from './audio/vad.js';
import { phonemize } from './g2p.js';
import { Scientific } from './Scientific.js';
import { fanOut, extractTags } from './emotion.js';
import { tryLoadOrt } from './onnx/runtime.js';
import { KokoroSession } from './onnx/kokoro.js';
import { ToneColorConverter } from './onnx/tone_color.js';
import { SherpaVoice, tryLoadSherpa } from './onnx/sherpa.js';
import { ChatterboxVoice } from './onnx/chatterbox.js';
import { FormantTTS } from './tts/formant.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DEFAULT_MODEL_DIR = join(__dirname, '..', 'models');

/**
 * Persona → acoustic profile for the fallback source (Hz fundamental etc.) and the default
 * Kokoro voice name. Mirrors the personas VoiceCreationEngine ships (jaimla/professor).
 */
const VOICE_PROFILES = {
  jaimla: { f0: 210, harmonics: 6, brightness: 0.9, sid: 4, gender: 'female' },
  professor: { f0: 105, harmonics: 8, brightness: 0.6, sid: 11, gender: 'male' },
  mindx: { f0: 150, harmonics: 7, brightness: 0.75, sid: 2, gender: 'neutral' },
};
const DEFAULT_PROFILE = { f0: 160, harmonics: 6, brightness: 0.7, sid: 0, gender: 'neutral' };

// Default target loudness for output + reference clips (EBU R128). Keeps every voice at a
// consistent level and gives the cloner a level-normalised reference.
const TARGET_LUFS = -20;

export class NeuralVoiceEngine extends EventEmitter {
  /**
   * @param {{
   *   agentId?: string, voiceId?: string, modelDir?: string,
   *   sampleRate?: number, outputPath?: string, speed?: number
   * }} [options]
   */
  constructor(options = {}) {
    super();
    this.agentId = options.agentId || 'voaice-neural';
    this.voiceId = options.voiceId || 'jaimla';
    this.modelDir = options.modelDir || DEFAULT_MODEL_DIR;
    this.sampleRate = options.sampleRate || 24000;
    this.outputPath = options.outputPath || '/tmp/voaice-neural';
    this.speed = options.speed || 1.0;

    this.normalizeOutput = options.normalizeOutput !== false;
    this.targetLufs = options.targetLufs ?? TARGET_LUFS;

    // Backends, in preference order: sherpa-onnx (real Kokoro + ZipVoice clone) → raw onnx
    // (hand-rolled Kokoro + experimental tone-color) → dependency-free fallback.
    this.sherpa = new SherpaVoice({ modelDir: this.modelDir, numThreads: options.numThreads });
    this.kokoro = new KokoroSession({ modelDir: this.modelDir, sampleRate: this.sampleRate });
    this.toneColor = new ToneColorConverter({ modelDir: this.modelDir });
    this.chatterbox = new ChatterboxVoice({ modelDir: this.modelDir });
    this.scientific = new Scientific({ sampleRate: this.sampleRate });

    // formant TTS is pure code (no model) — always available as the model-free real-speech tier.
    this.formantEnabled = options.formant !== false;

    /** @type {{ sherpa:boolean, ort:boolean, base:boolean, clone:boolean, emotive:boolean, formant:boolean, backend:string }} */
    this.capability = { sherpa: false, ort: false, base: false, clone: false, emotive: false, formant: false, backend: 'fallback' };
    this._clones = new Map(); // id -> { embedding?, refSamples?, refSampleRate?, refText?, voiceprint }
    this._baseEmb = new Map(); // onnx tone-color: voiceId -> base voice embedding cache
  }

  /** Probe runtimes + weights and resolve the active backend. Never throws. */
  async init() {
    try {
      await fs.mkdir(this.outputPath, { recursive: true });
      this.capability.sherpa = !!(await tryLoadSherpa());
      this.capability.ort = !!(await tryLoadOrt());

      const sherpaBase = this.capability.sherpa && this.sherpa.hasKokoro();
      const sherpaClone = this.capability.sherpa && this.sherpa.hasZipVoice();
      const ortBase = this.capability.ort && this.kokoro.isCached();
      const ortClone = ortBase && this.toneColor.isCached();

      this.capability.base = sherpaBase || ortBase;
      this.capability.clone = sherpaClone || ortClone;
      this.capability.emotive = await this.chatterbox.available().catch(() => false);
      this.capability.formant = this.formantEnabled;
      // model-free real speech (formant) outranks the bare tone fallback when no neural model.
      this.capability.backend =
        sherpaBase || sherpaClone ? 'sherpa' : ortBase ? 'onnx' : this.capability.formant ? 'formant' : 'fallback';

      this.emit('initialized', { agentId: this.agentId, voiceId: this.voiceId, capability: this.capability });
    } catch (error) {
      this.emit('error', error);
    }
    return this;
  }

  profile(voiceId) {
    return VOICE_PROFILES[voiceId || this.voiceId] || DEFAULT_PROFILE;
  }

  /** Stable id for a cloned embedding (sha256 of its bytes). */
  static embeddingId(embedding) {
    const buf = Buffer.from(new Float32Array(embedding).buffer);
    return '0x' + createHash('sha256').update(buf).digest('hex').slice(0, 32);
  }

  /**
   * Synthesize speech from text. Routes to the active backend (sherpa → onnx → fallback). When
   * a known `embeddingId` (or inline `embedding`) names a cloned voice, speaks in that voice:
   * ZipVoice re-clones from the stored reference (sherpa); tone-color converts the timbre (onnx).
   * Output is loudness-normalised to a consistent level unless disabled.
   * @param {{ text:string, voiceId?:string, embedding?:Float32Array, embeddingId?:string, speed?:number, write?:boolean }} req
   * @returns {Promise<{ buffer:Buffer, samples:Float32Array, sampleRate:number, backend:string, wavPath?:string }>}
   */
  async synthesize(req) {
    const rawText = (req.text || '').toString();
    if (!rawText.trim()) throw new Error('voaice neural: empty text');
    const voiceId = req.voiceId || this.voiceId;
    const profile = this.profile(voiceId);
    const clone = req.embeddingId ? this._clones.get(req.embeddingId) : null;
    const inlineEmb = req.embedding || (clone && clone.embedding) || null;

    // Emotion fan-out: strip paralinguistic tags from text, resolve voice params + face descriptor.
    const emotion = fanOut(req.emotion);
    const { clean: text, tags } = extractTags(rawText);
    // emotion prosody nudges pace on backends without native emotion (sherpa/onnx/fallback);
    // Chatterbox instead actuates `exaggeration`/`cfg_weight` directly.
    const speed = (req.speed || this.speed) * emotion.voice.prosody.speed;

    let samples;
    let sampleRate = this.sampleRate;
    let backend;

    // Emotive voice: only when an emotion is explicitly requested AND Chatterbox is available
    // (it is slow on CPU, so it is never the default path).
    if (req.emotion && emotion.label !== 'neutral' && this.capability.emotive) {
      try {
        const out = await this.chatterbox.synth({
          text,
          exaggeration: emotion.voice.exaggeration,
          cfg_weight: emotion.voice.cfg_weight,
          temperature: emotion.voice.temperature,
        });
        samples = out.samples;
        sampleRate = out.sampleRate;
        backend = `chatterbox:${emotion.label}`;
      } catch {
        /* fall through to the active non-emotive backend; face still shows the emotion */
      }
    }

    if (samples) {
      /* emotive path already produced audio */
    } else if (this.capability.backend === 'sherpa') {
      if (clone && clone.refSamples && this.sherpa.hasZipVoice()) {
        const out = await this.sherpa.speakCloned({
          text,
          refSamples: clone.refSamples,
          refSampleRate: clone.refSampleRate,
          refText: clone.refText,
          speed,
          numSteps: req.numSteps,
        });
        samples = out.samples;
        sampleRate = out.sampleRate;
        backend = 'sherpa:zipvoice-clone';
      } else {
        const out = await this.sherpa.speakPreset({ text, sid: profile.sid, speed });
        samples = out.samples;
        sampleRate = out.sampleRate;
        backend = 'sherpa:kokoro';
      }
    } else if (this.capability.backend === 'onnx') {
      const { phonemes } = await phonemize(text);
      const base = await this.kokoro.synth(phonemes, { voice: voiceId, speed });
      samples = base.samples;
      sampleRate = base.sampleRate;
      backend = 'onnx:kokoro';
      if (inlineEmb && this.toneColor.isCached()) {
        const srcEmb = await this._baseEmbedding(voiceId, samples);
        samples = await this.toneColor.convert(samples, srcEmb, inlineEmb);
        backend = 'onnx:kokoro+tone-color';
      }
    } else if (this.capability.backend === 'formant') {
      // model-free REAL speech (clean-room Klatt-style formant synth) — persona f0 + emotion pitch.
      const f0 = profile.f0 * (emotion.voice.prosody.pitch || 1);
      const ft = new FormantTTS({ sampleRate: this.sampleRate, f0, speed });
      samples = ft.synthesize(text);
      sampleRate = this.sampleRate;
      backend = 'formant';
    } else {
      const { phonemes, backend: g2p } = await phonemize(text);
      samples = this._fallbackSource(phonemes, profile, speed);
      backend = `fallback(${g2p})`;
    }

    if (this.normalizeOutput) samples = normalizeToLufs(samples, sampleRate, this.targetLufs);
    this.sampleRate = sampleRate;

    const buffer = encodeWav(samples, sampleRate);
    const durationMs = Math.round((samples.length / sampleRate) * 1000);
    const result = { buffer, samples, sampleRate, backend, emotion, tags };
    if (req.write !== false) {
      result.wavPath = join(this.outputPath, `${this.agentId}-${Date.now()}.wav`);
      await fs.writeFile(result.wavPath, buffer);
    }
    // faicey consumes this: the SAME owned emotion drives the FACE (toFace) + tag triggers, so the
    // face emotes even when the audio backend cannot. VoiceyBridge listens for 'speechGenerated'.
    this.emit('speechGenerated', {
      text,
      emotion,
      tags,
      duration: durationMs,
      analysis: { sentiment: emotion.label, emotion, tags },
    });
    return result;
  }

  /**
   * Clone a voice from a reference clip. The reference is VAD-trimmed and loudness-normalised
   * (clean input → steadier clone), a forensic 18-dp voiceprint is always measured, and a clone
   * profile is stored addressable by the returned id for later synthesis. The stored profile is
   * backend-shaped: sherpa/ZipVoice keeps the reference samples + transcript (`text` is REQUIRED
   * for that path); onnx/tone-color keeps a speaker embedding.
   * @param {{ wavPath?:string, buffer?:Buffer, samples?:Float32Array, sampleRate?:number, text?:string }} req
   * @returns {Promise<{ embeddingId:string|null, embedding:Float32Array|null, voiceprint:object, backend:string, needsText:boolean }>}
   */
  async cloneFromReference(req) {
    let samples = req.samples;
    let sampleRate = req.sampleRate || this.sampleRate;
    if (!samples) {
      const buf = req.buffer || (req.wavPath ? await fs.readFile(req.wavPath) : null);
      if (!buf) throw new Error('voaice neural: cloneFromReference needs wavPath, buffer or samples');
      const decoded = decodeWav(buf);
      samples = decoded.samples;
      sampleRate = decoded.sampleRate;
    }

    // Clean the reference: trim silence, then normalise level.
    samples = trimSilence(samples, sampleRate).samples;
    samples = normalizeToLufs(samples, sampleRate, this.targetLufs);

    // Forensic voiceprint (reuses Scientific.js; works with zero models present).
    const sci = new Scientific({ sampleRate });
    const voiceprint = sci.measure(samples.subarray(0, Math.min(samples.length, sampleRate * 5)));

    const id = '0x' + createHash('sha256').update(voiceprint.hash + (req.text || '')).digest('hex').slice(0, 32);
    let embedding = null;
    let backend = 'voiceprint-only';
    let needsText = false;

    if (this.capability.backend === 'sherpa' && this.sherpa.hasZipVoice()) {
      // ZipVoice clones at generation time from reference audio + its transcript.
      needsText = !req.text;
      this._clones.set(id, { refSamples: samples, refSampleRate: sampleRate, refText: req.text || '', voiceprint });
      backend = 'sherpa:zipvoice';
    } else if (this.capability.backend === 'onnx' && this.toneColor.isCached()) {
      embedding = await this.toneColor.extractEmbedding(samples);
      this._clones.set(id, { embedding, voiceprint });
      backend = 'onnx:tone-color';
    }
    return { embeddingId: backend === 'voiceprint-only' ? null : id, embedding, voiceprint, backend, needsText };
  }

  /** Convenience: clone then immediately speak in the cloned voice. */
  async synthesizeCloned(req) {
    const clone = await this.cloneFromReference({ ...(req.reference || {}), text: req.referenceText });
    const out = await this.synthesize({ ...req, embeddingId: clone.embeddingId || undefined });
    return { ...out, embeddingId: clone.embeddingId, voiceprint: clone.voiceprint, needsText: clone.needsText };
  }

  listVoices() {
    return Object.keys(VOICE_PROFILES);
  }

  /** Base voice's own embedding, for the source side of a tone-color conversion (onnx path). */
  async _baseEmbedding(voiceId, baseSamples) {
    if (this._baseEmb.has(voiceId)) return this._baseEmb.get(voiceId);
    const emb = await this.toneColor.extractEmbedding(baseSamples);
    this._baseEmb.set(voiceId, emb);
    return emb;
  }

  /**
   * Dependency-free voiced source: a persona-tinted harmonic tone with a per-token amplitude
   * envelope so duration tracks text length. NOT speech — a deterministic placeholder that
   * keeps the pipeline runnable (and persona-differentiable) without any model weights.
   */
  _fallbackSource(phonemes, profile, speed) {
    const sr = this.sampleRate;
    const tokens = Math.max(1, phonemes.replace(/\s+/g, '').length);
    const secPerToken = 0.075 / Math.max(0.5, Math.min(2, speed));
    const total = Math.max(1, Math.ceil(tokens * secPerToken * sr));
    const out = new Float32Array(total);
    const f0 = profile.f0;
    const nH = profile.harmonics;
    for (let i = 0; i < total; i++) {
      const t = i / sr;
      // gentle vibrato + per-token amplitude gate to suggest syllables
      const vib = 1 + 0.01 * Math.sin(2 * Math.PI * 5 * t);
      const gate = 0.55 + 0.45 * Math.sin(2 * Math.PI * (1 / (secPerToken * 2)) * t);
      let s = 0;
      for (let h = 1; h <= nH; h++) {
        const amp = (profile.brightness ** (h - 1)) / h;
        s += amp * Math.sin(2 * Math.PI * f0 * h * vib * t);
      }
      // attack/release envelope over the whole utterance
      const env = Math.min(1, i / (0.02 * sr)) * Math.min(1, (total - i) / (0.05 * sr));
      out[i] = 0.6 * env * gate * (s / nH);
    }
    return out;
  }
}

export default NeuralVoiceEngine;
