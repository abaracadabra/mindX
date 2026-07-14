/**
 * PersonaStudio.js — the definitive `.persona` creation tool.
 *
 * Composes the three peers into one being:
 *   faicey   → the FACE  (clone from image / perspectives / video / webcam)
 *   voaice   → the VOICE (clone, edit, measure forensically, export)
 *   facerig  → the RIG   (canonical wireframe engine, live reenactment)
 *
 * Two ways to make a persona:
 *   create()  — INVENT one (synthetic subject; no consent needed, none faked)
 *   clone()   — CLONE a real subject (consent required above `basic`)
 *
 * Both end at `stamp()`, which MEASURES what was actually achieved, GRADES it,
 * and writes the earned tier into the file. You cannot ask for hyperrealism and
 * receive the label; you can only produce artifacts that measure as hyperreal.
 * A persona that misses its target is still exported — at the tier it earned,
 * with the failed gates named. Honest downgrade over flattering fiction.
 *
 * Peer modules load LAZILY and DEGRADE: with no faicey/voaice present the studio
 * still builds, validates and grades personas from supplied prints — it just
 * cannot capture. `capability()` reports exactly what this host can do.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { blank, upgrade, validate, toCognitive, PERSONA_VERSION } from './schema.js';
import { resolveMode, grade, MODES } from './modes.js';
import { measureAll } from './measure.js';
import {
  consent as mkConsent,
  consentSatisfies,
  appendCustody,
  manifest as mkManifest,
  signManifest,
  verify as verifyProvenance,
} from './provenance.js';

const sha = (s) => '0x' + createHash('sha256').update(s).digest('hex');
// SNR is null when a clip carries no measurable noise floor — never print that as a number.
const fmtDb = (v) => (typeof v === 'number' && Number.isFinite(v) ? `${v.toFixed(1)}dB` : 'unmeasurable');

/** Lazy peer resolution — absent peers degrade, they do not crash. */
async function peers() {
  const out = { faicey: null, voaice: null };
  try {
    out.voaice = await import('voaice');
  } catch {
    try { out.voaice = await import('../../voaice/src/index.js'); } catch { /* absent */ }
  }
  try {
    out.faicey = {
      persona: await import('../../faicey/src/face_clone/persona.js'),
      faceprint: await import('../../faicey/src/face_clone/faceprint.js'),
    };
  } catch { /* absent */ }
  return out;
}

export class PersonaStudio {
  /**
   * @param {{mode?:'basic'|'professional'|'scientific', realism?:'realism'|'hyperrealism',
   *          sign?:Function, signer?:string}} [opts]
   */
  constructor(opts = {}) {
    this.mode = opts.mode || 'basic';
    this.realism = opts.realism || 'realism';
    this.settings = resolveMode(this.mode, this.realism);
    this.sign = opts.sign || null; // (hash) => signature — BYO key (vault/EIP-191/HSM)
    this.signer = opts.signer || null;
    this.persona = blank();
    this.persona.fidelity.mode = this.mode;
    this.persona.fidelity.realism = this.mode === 'scientific' ? this.realism : null;
    this._custody = [];
    this._sources = [];
    this._measured = {};
    this._peers = null;
  }

  async _p() {
    if (!this._peers) this._peers = await peers();
    return this._peers;
  }

  /** What can this host actually do? Honest capability probe. */
  async capability() {
    const p = await this._p();
    return {
      face: !!p.faicey,
      voice: !!p.voaice,
      voiceClone: !!p.voaice?.loadNeuralVoiceEngine,
      forensic: !!p.voaice?.Forensic,
      export: { wav: !!p.voaice?.exportClip, ogg: !!p.voaice?.oggAvailable?.() },
      signing: !!this.sign,
      // What the current stack can honestly reach. The scientific tier's face
      // gates assume a photoreal renderer; the in-repo renderer is wireframe/mesh.
      maxHonestMode: p.faicey && p.voaice ? (this.sign ? 'scientific' : 'professional') : 'basic',
    };
  }

  // ── identity + cognition ────────────────────────────────────────────────
  /** Set who this being IS (v1 cognitive fields are accepted verbatim). */
  identity({ name, agent_id, label, description, role, ...cognitive } = {}) {
    Object.assign(this.persona.identity, {
      name: name ?? this.persona.identity.name,
      agent_id: agent_id ?? this.persona.identity.agent_id,
      label: label ?? name ?? this.persona.identity.label,
      description: description ?? this.persona.identity.description,
      role: role ?? this.persona.identity.role,
    });
    if (Object.keys(cognitive).length) {
      const up = upgrade(cognitive);
      Object.assign(this.persona.cognition, {
        ...this.persona.cognition,
        ...Object.fromEntries(Object.entries(up.cognition).filter(([, v]) =>
          v !== null && !(Array.isArray(v) && !v.length) && !(typeof v === 'object' && v !== null && !Array.isArray(v) && !Object.keys(v).length)
        )),
      });
    }
    return this;
  }

  /** Load cognition from an existing v1 `.persona` file (drAIML, boardroom…). */
  async cognitionFrom(path) {
    const v1 = JSON.parse(await readFile(path, 'utf8'));
    const up = upgrade(v1);
    this.persona.cognition = up.cognition;
    if (!this.persona.identity.name) this.persona.identity = up.identity;
    this._sources.push({ type: 'cognition', hash: sha(JSON.stringify(v1)), note: path });
    this._custody = appendCustody(this._custody, { action: 'cognition', contentHash: sha(JSON.stringify(v1)), note: path });
    return this;
  }

  // ── consent ─────────────────────────────────────────────────────────────
  /** Record consent. `kind: 'synthetic'` for invented beings; see CONSENT_KINDS. */
  consent(c) {
    this.persona.provenance.consent = mkConsent(c);
    this._custody = appendCustody(this._custody, {
      action: 'consent',
      contentHash: this.persona.provenance.consent.hash,
      note: c.kind,
    });
    return this;
  }

  // ── intake ──────────────────────────────────────────────────────────────
  /**
   * INTAKE — judge a reference capture BEFORE cloning from it.
   *
   * You cannot out-model a noisy room. Every artifact of the capture — the
   * hum, the reflections, the clipping — is faithfully learned by the clone and
   * then carried into every word it ever says. So the room is a graded axis
   * (`referenceSnrDb`), and this is where a bad capture is caught early, while
   * re-recording still costs nothing.
   *
   * Optionally cleans the clip (voaice spectral subtraction) and records the
   * cleaning as a custody step — an edited reference is a fact about the
   * artifact, not a secret.
   *
   * @param {{samples:Float32Array, sampleRate:number}} clip
   * @param {{denoise?:boolean, trim?:boolean}} [opts]
   * @returns {Promise<{clip:object, snr:object, segments:object|null,
   *                    verdict:string, sufficientFor:string[], denoised:boolean}>}
   */
  async intake(clip, opts = {}) {
    const { voaice } = await this._p();
    if (opts.roomTone) this._roomTone = opts.roomTone;
    if (!voaice?.snr) {
      throw new Error('aivatar: intake() needs voaice (the signal/noise layer) — install the peer');
    }
    let working = { samples: Float32Array.from(clip.samples), sampleRate: clip.sampleRate };
    let denoised = false;

    if (opts.denoise) {
      const res = voaice.denoise(working.samples, working.sampleRate);
      if (res.profileUsed) {
        working = { samples: res.samples, sampleRate: working.sampleRate };
        denoised = true;
        this._custody = appendCustody(this._custody, {
          action: 'denoise',
          contentHash: null,
          note: `SNR ${fmtDb(res.snrBefore.snrDb)} → ${fmtDb(res.snrAfter.snrDb)}`,
        });
      }
    }
    if (opts.trim && voaice.trimSilence) {
      const t = voaice.trimSilence(working.samples, working.sampleRate);
      if (t?.trimmed) {
        working = { samples: Float32Array.from(t.samples), sampleRate: working.sampleRate };
        this._custody = appendCustody(this._custody, { action: 'trim', contentHash: null, note: 'leading/trailing silence' });
      }
    }

    const report = voaice.snr(working.samples, working.sampleRate, { noiseClip: this._roomTone });
    const seconds = working.samples.length / working.sampleRate;
    const voiced = voaice.voicedRatio ? voaice.voicedRatio(working.samples, working.sampleRate) : null;

    // Which tiers could this capture still support? Named honestly, up front.
    const sufficientFor = [];
    for (const [name, gates] of [
      ['professional', MODES.professional.gates],
      ['scientific/realism', MODES.scientific.gates.realism],
      ['scientific/hyperrealism', MODES.scientific.gates.hyperrealism],
    ]) {
      // An unmeasurable floor (null) cannot clear a floor gate — unmeasured is
      // never passed. The intake report says exactly how to fix that.
      const okSnr = typeof report.snrDb === 'number' && report.snrDb >= (gates.referenceSnrDb ?? -Infinity);
      const okSec = seconds * (voiced ?? 1) >= (gates.referenceSeconds ?? 0);
      const okVoiced = (voiced ?? 1) >= (gates.voicedRatio ?? 0);
      if (okSnr && okSec && okVoiced) sufficientFor.push(name);
    }
    sufficientFor.unshift('basic');

    this._custody = appendCustody(this._custody, {
      action: 'intake',
      contentHash: null,
      note: `${seconds.toFixed(1)}s · SNR ${fmtDb(report.snrDb)} · ${report.verdict}`,
    });

    return {
      clip: working,
      snr: report,
      seconds,
      voicedRatio: voiced,
      segments: voaice.STT ? new voaice.STT().segment(working) : null,
      verdict: report.verdict,
      sufficientFor,
      denoised,
    };
  }

  // ── embodiment ──────────────────────────────────────────────────────────
  /**
   * Attach a FACE. Supply either a faicey clone profile (from
   * FaceCloneEngine.cloneFrom*) or a raw faceprint + landmarks.
   * @param {{profile?:object, faceprint?:object, landmarks?:Array, sourceLandmarks?:Array, frames?:number, source?:string}} f
   */
  face(f = {}) {
    const profile = f.profile || {};
    const faceprint = f.faceprint || profile.faceprint || null;
    if (!faceprint) throw new Error('aivatar: face() needs a faceprint (or a clone profile)');
    this.persona.embodiment.face = {
      faceprint,
      source: f.source || profile.source || 'unknown',
      frames: f.frames ?? profile.frames ?? (profile.recognition?.frames || 1),
      render: this.settings.face.render,
      textured: this.settings.face.textured,
    };
    this._faceLandmarks = f.landmarks || profile.landmarks || null;
    this._sourceLandmarks = f.sourceLandmarks || null;
    this._measured.faceFrames = this.persona.embodiment.face.frames;
    this._sources.push({ type: 'face', hash: faceprint.hash || null, note: this.persona.embodiment.face.source });
    this._custody = appendCustody(this._custody, {
      action: 'clone-face',
      contentHash: faceprint.hash || null,
      note: `${this.persona.embodiment.face.frames} frame(s)`,
    });
    return this;
  }

  /**
   * Attach a VOICE. Supply a reference clip (to clone) and/or the cloned output.
   * Measurement happens here — this is where realism claims are earned.
   * @param {{referenceClip?:object, clonedClip?:object, voiceprint?:object, engine?:string}} v
   */
  async voice(v = {}) {
    const { voaice } = await this._p();
    let voiceprint = v.voiceprint || null;
    if (!voiceprint && voaice?.Forensic && v.referenceClip?.samples?.length) {
      const f = new voaice.Forensic({ sampleRate: v.referenceClip.sampleRate });
      voiceprint = f.voiceprint(v.referenceClip.samples);
    }
    if (!voiceprint) throw new Error('aivatar: voice() needs a reference clip (with voaice) or a voiceprint');

    this.persona.embodiment.voice = {
      voiceprint,
      engine: v.engine || this.settings.voice.engine,
      clone: this.settings.voice.clone,
      sampleRate: this.settings.voice.sampleRate,
      bitDepth: this.settings.voice.bitDepth,
      quality: this.settings.voice.quality,
      loudness: this.settings.voice.loudness,
    };
    this._refClip = v.referenceClip || null;
    this._clonedClip = v.clonedClip || null;
    // Room tone (a few seconds of the empty room) makes SNR measurable even for
    // a reference with no pauses in it.
    if (v.roomTone) this._roomTone = v.roomTone;
    this._sources.push({ type: 'voice', hash: voiceprint.hash, note: v.engine || this.settings.voice.engine });
    this._custody = appendCustody(this._custody, { action: 'clone-voice', contentHash: voiceprint.hash });
    return this;
  }

  /** Attach the RIG settings (facerig canonical engine drives these). */
  rig(r = {}) {
    this.persona.embodiment.rig = { ...this.settings.rig, ...r };
    return this;
  }

  // ── measure → grade → stamp ─────────────────────────────────────────────
  /**
   * Run every available measurement.
   *
   * `supplied` exists for axes this host genuinely CANNOT compute (e.g. a
   * photoreal renderer's geometric error, or an external listening-test score).
   * It can only FILL a hole — a supplied value never overrides a computed one.
   * Otherwise "measurement" would just be a suggestion box, and the earned-tier
   * doctrine would be theatre. Every axis records how it was obtained, and that
   * record travels into the signed manifest: a supplied number is attributable
   * to whoever signed it.
   */
  async measure(supplied = {}) {
    const { voaice } = await this._p();
    const forensic =
      voaice?.Forensic && (this._refClip || this._clonedClip)
        ? new voaice.Forensic({ sampleRate: (this._refClip || this._clonedClip).sampleRate })
        : null;
    const computed = measureAll({
      clonedLandmarks: this._faceLandmarks,
      sourceLandmarks: this._sourceLandmarks,
      faceFrames: this._measured.faceFrames,
      referenceClip: this._refClip,
      clonedClip: this._clonedClip,
      forensic,
      dsp: voaice ? { fft: voaice.fft, hann: voaice.hann, magnitudeSpectrum: voaice.magnitudeSpectrum } : null,
      voicedRatioFn: voaice?.voicedRatio,
      snrFn: voaice?.snr,
      roomTone: this._roomTone || null,
    });

    const source = { ...(this._measuredSource || {}) };
    const out = { ...this._measured };
    for (const [k, v] of Object.entries(computed)) {
      if (v === undefined) continue;
      out[k] = v;
      source[k] = 'computed';
    }
    for (const [k, v] of Object.entries(supplied)) {
      if (v === undefined) continue;
      if (source[k] === 'computed') continue; // computed wins, always
      out[k] = v;
      source[k] = 'supplied';
    }
    this._measured = out;
    this._measuredSource = source;
    this.persona.fidelity.measured = out;
    this.persona.fidelity.measuredSource = source;
    return out;
  }

  /**
   * Seal the persona: measure, grade against the tier gates, write the EARNED
   * tier (downgrading if the target was not met), build + sign the manifest.
   * @returns {Promise<{persona:object, graded:object, requested:object, downgraded:boolean, validation:object}>}
   */
  async stamp(supplied = {}) {
    await this.measure(supplied);
    const graded = grade(this._measured);
    const requested = { mode: this.mode, realism: this.mode === 'scientific' ? this.realism : null };

    const rank = { basic: 0, professional: 1, scientific: 2 };
    const downgraded =
      rank[graded.mode] < rank[requested.mode] ||
      (graded.mode === 'scientific' &&
        requested.realism === 'hyperrealism' &&
        graded.realism !== 'hyperrealism');

    // The file always carries the EARNED tier. That is the whole doctrine.
    this.persona.fidelity.mode = graded.mode;
    this.persona.fidelity.realism = graded.realism;
    this.persona.fidelity.graded = graded;
    this.persona.fidelity.requested = requested;

    // Consent gate — a real subject cloned above `basic` needs a consent record.
    const cs = consentSatisfies(this.persona.provenance.consent, this.persona.fidelity.mode);
    if (!cs.ok && this.persona.fidelity.mode !== 'basic') {
      throw new Error(`aivatar: ${this.persona.fidelity.mode} tier blocked — ${cs.reason}. Record consent() first.`);
    }

    // Persona print (faicey personaPrint binds face+voice into one identity hash).
    const { faicey } = await this._p();
    if (faicey?.persona?.personaPrint) {
      const pp = await faicey.persona.personaPrint({
        face: this.persona.embodiment.face?.faceprint,
        voice: this.persona.embodiment.voice?.voiceprint,
        label: this.persona.identity.label,
      });
      this.persona.hash = pp.hash;
      this.persona.aiml.inft = { registerArgs: pp.registerArgs, modalities: pp.modalities };
    } else {
      this.persona.hash = sha(
        JSON.stringify([
          this.persona.embodiment.face?.faceprint?.hash || '',
          this.persona.embodiment.voice?.voiceprint?.hash || '',
        ])
      );
    }

    this._custody = appendCustody(this._custody, {
      action: 'stamp',
      contentHash: this.persona.hash,
      note: `${graded.mode}${graded.realism ? '/' + graded.realism : ''}`,
    });
    this.persona.provenance.custody = this._custody;

    // Manifest — mandatory above basic; signed if a signer was supplied.
    if (this.persona.fidelity.mode !== 'basic' || this.sign) {
      let man = mkManifest({
        persona: { hash: this.persona.hash, label: this.persona.identity.label, modalities: this._modalities() },
        mode: this.persona.fidelity.mode,
        realism: this.persona.fidelity.realism,
        measured: this._measured,
        measuredSource: this._measuredSource, // computed vs supplied, per axis
        consent: this.persona.provenance.consent,
        custody: this._custody,
        sources: this._sources,
      });
      if (this.sign) man = await signManifest(man, this.sign, this.signer);
      else if (this.persona.fidelity.mode === 'scientific') {
        throw new Error(
          'aivatar: scientific tier requires a SIGNED manifest — construct the studio with { sign, signer }. ' +
            'An artifact that can pass for real must be able to prove what it is.'
        );
      }
      this.persona.provenance.manifest = man;
    }

    this.persona.media = {
      formats: this.settings.export.formats,
      settings: { voice: this.persona.embodiment.voice ? { ...this.settings.voice } : null },
    };

    const validation = validate(this.persona);
    return { persona: this.persona, graded, requested, downgraded, validation };
  }

  _modalities() {
    return [
      this.persona.embodiment.face && 'face',
      this.persona.embodiment.voice && 'voice',
      this.persona.embodiment.rig && 'rig',
    ].filter(Boolean);
  }

  // ── io ──────────────────────────────────────────────────────────────────
  /** Write the `.persona` file (stamps first if not yet stamped). */
  async save(path) {
    if (!this.persona.fidelity.graded) await this.stamp();
    // Prints carry 18-dp registers as BigInt (the on-chain form); JSON has no
    // BigInt — serialise as decimal strings, which is exactly what a contract
    // call takes anyway. `measuresStr` already holds the canonical strings.
    const json = JSON.stringify(this.persona, (_k, v) => (typeof v === 'bigint' ? v.toString() : v), 2);
    await writeFile(path, json);
    return { path, hash: this.persona.hash, mode: this.persona.fidelity.mode };
  }

  /** Project to a v1 cognitive `.persona` (what BDI agents / drAIML consume). */
  toCognitive() {
    return toCognitive(this.persona);
  }

  /** Load + fully verify a `.persona`: schema, earned tier, provenance chain. */
  static async load(path) {
    const p = JSON.parse(await readFile(path, 'utf8'));
    const persona = p.kind === 'aivatar-persona' ? p : upgrade(p);
    const validation = validate(persona);
    const provenance = persona.provenance?.manifest
      ? verifyProvenance(persona.provenance.manifest, persona.provenance.custody || [])
      : { ok: true, signed: false, errors: [], note: 'no manifest (basic tier)' };
    return { persona, validation, provenance };
  }
}

export { MODES, PERSONA_VERSION };
export default PersonaStudio;
