/**
 * modes.js — the three aivatar fidelity tiers.
 *
 * A mode is a CONTRACT, not a promise: it declares the capture, synthesis,
 * render and export settings the three peers must run at, AND the measurable
 * gates an artifact must pass to legitimately carry that mode's label.
 *
 *   basic        — expressive, cheap, obviously synthetic. Chat avatars, demos.
 *   professional — broadcast-grade. Media production, presentations, VO.
 *   scientific   — measured fidelity, forensic provenance. Two realism levels:
 *                    realism      — indistinguishable in normal viewing
 *                    hyperrealism — indistinguishable under scrutiny/analysis
 *
 * DOCTRINE — the scientific tier is honest or it is nothing:
 *  1. Fidelity is MEASURED (geometric RMSE, voiceprint similarity, spectral
 *     distance), never asserted. `gates` below are the pass marks.
 *  2. The label is EARNED at export time by the measurements, not chosen by
 *     the operator. `grade()` is what stamps a persona, and it will downgrade.
 *  3. Provenance is MANDATORY at the scientific tier (see provenance.js): a
 *     consent attestation for a real subject, a signed manifest, and a
 *     hash-linked custody chain travel with the artifact. An artifact that can
 *     pass for real MUST carry a cryptographic record of what it is. That is
 *     what makes it usable in media and admissible in analysis — the honesty
 *     is the feature, not a tax on it.
 *
 * © Professor Codephreak - rage.pythai.net
 */

/** @typedef {'basic'|'professional'|'scientific'} ModeName */
/** @typedef {'realism'|'hyperrealism'} RealismLevel */

export const MODES = {
  basic: {
    name: 'basic',
    intent: 'expressive, cheap, honestly synthetic — chat avatars, demos, agent faces',
    face: {
      source: 'single',            // one image / one webcam shot is enough
      minFrames: 1,
      landmarks: 478,              // MediaPipe always gives all of them
      render: 'wireframe',         // faicey contours / point cloud
      textured: false,
      expressions: true,
    },
    voice: {
      engine: 'system',            // OS TTS (espeak-ng/festival)
      clone: false,
      sampleRate: 22050,
      bitDepth: 16,
      quality: 'low',
      loudness: null,              // no broadcast levelling
    },
    rig: { fps: 30, blendshapes: 52, liveReenactment: true },
    export: { formats: ['wav'], persona: true, media: ['png', 'json'] },
    provenance: { required: false, consent: 'recommended' },
    gates: null,                   // nothing to prove — it looks synthetic
  },

  professional: {
    name: 'professional',
    intent: 'broadcast-grade — media production, presentations, narration, product',
    face: {
      source: 'perspectives',      // front + left + right (or guided AUTO capture)
      minFrames: 3,
      landmarks: 478,
      render: 'mesh',
      textured: true,
      expressions: true,
    },
    voice: {
      engine: 'neural',            // voaice ONNX TTS
      clone: true,                 // zero-shot from a reference clip
      sampleRate: 44100,
      bitDepth: 24,
      quality: 'high',
      loudness: -16,               // LUFS, streaming/broadcast target
      denoise: true,
    },
    rig: { fps: 60, blendshapes: 52, liveReenactment: true },
    export: { formats: ['wav', 'ogg'], persona: true, media: ['png', 'mp4', 'json'] },
    provenance: { required: true, consent: 'required-for-real-subject' },
    gates: {
      faceRmse: 0.02,              // normalised landmark RMSE vs source (≤)
      faceFrames: 3,               // distinct angles (≥)
      voiceSimilarity: 0.85,       // cloned vs reference voiceprint (≥)
      voicePrecision: 0.6,         // Scientific precision score (≥)
      voicedRatio: 0.4,            // reference clip must actually contain speech (≥)
      referenceSeconds: 6,         // usable reference audio (≥)
      referenceSnrDb: 20,          // the ROOM the reference was captured in (≥)
    },
  },

  scientific: {
    name: 'scientific',
    intent:
      'measured fidelity with forensic provenance — any and all media expressions ' +
      'and AIML interactions; realism (normal viewing) and hyperrealism (under scrutiny)',
    face: {
      source: 'video-or-perspectives',
      minFrames: 12,               // multi-angle + video frames, aggregated
      landmarks: 478,
      render: 'mesh',
      textured: true,
      photoreal: 'capability-gated', // uses a photoreal renderer IF one is present
      expressions: true,
      microExpressions: true,
    },
    voice: {
      engine: 'neural',
      clone: true,
      sampleRate: 48000,
      bitDepth: 32,                // float — no quantisation before mastering
      quality: 'studio',
      loudness: -14,
      denoise: true,
      prosody: 'measured',         // pitch/rate/energy fitted to the reference
    },
    rig: { fps: 60, blendshapes: 52, liveReenactment: true, microExpressions: true },
    export: {
      formats: ['wav', 'ogg'],
      persona: true,
      media: ['png', 'mp4', 'json'],
      manifest: true,              // C2PA-shaped provenance manifest, always
    },
    provenance: {
      required: true,
      consent: 'required',         // no scientific-tier clone of a real subject without it
      custodyChain: true,
      signedManifest: true,
      disclosure: 'embedded',      // the artifact declares itself, cryptographically
    },
    gates: {
      realism: {
        faceRmse: 0.010,
        faceFrames: 12,
        voiceSimilarity: 0.92,
        voicePrecision: 0.75,
        voicedRatio: 0.5,
        referenceSeconds: 30,
        referenceSnrDb: 25,        // a quiet room, not a good microphone in a bad one
        spectralDistance: 0.20,    // cloned vs reference (≤), lower = closer
      },
      hyperrealism: {
        faceRmse: 0.004,
        faceFrames: 30,
        voiceSimilarity: 0.965,
        voicePrecision: 0.85,
        voicedRatio: 0.6,
        referenceSeconds: 120,
        referenceSnrDb: 30,        // studio-clean intake — you cannot out-model a noisy room
        spectralDistance: 0.08,
        integrityClean: true,      // no splice/clipping artifacts in the output
      },
    },
  },
};

export const MODE_NAMES = Object.freeze(Object.keys(MODES));
export const REALISM_LEVELS = Object.freeze(['realism', 'hyperrealism']);

/** Resolve a mode (+ realism level for scientific) into one flat settings object. */
export function resolveMode(mode = 'basic', realism = 'realism') {
  const m = MODES[mode];
  if (!m) throw new Error(`aivatar: unknown mode "${mode}" (${MODE_NAMES.join('|')})`);
  const gates =
    mode === 'scientific'
      ? m.gates[REALISM_LEVELS.includes(realism) ? realism : 'realism']
      : m.gates;
  return {
    ...m,
    realism: mode === 'scientific' ? realism : null,
    gates,
  };
}

/**
 * GRADE — the heart of the honesty doctrine. Given the measurements actually
 * achieved, return the highest tier the artifact EARNS. Never trusts a claim.
 *
 * @param {{faceRmse?:number, faceFrames?:number, voiceSimilarity?:number,
 *          voicePrecision?:number, voicedRatio?:number, referenceSeconds?:number,
 *          spectralDistance?:number, integrityClean?:boolean}} measured
 * @returns {{mode:ModeName, realism:RealismLevel|null, passed:string[], failed:string[]}}
 */
export function grade(measured = {}) {
  const check = (gates) => {
    const failed = [];
    const passed = [];
    const cmp = (key, ok) => (ok ? passed.push(key) : failed.push(key));
    if (gates.faceRmse !== undefined && measured.faceRmse !== undefined)
      cmp('faceRmse', measured.faceRmse <= gates.faceRmse);
    else if (gates.faceRmse !== undefined) failed.push('faceRmse:unmeasured');
    if (gates.faceFrames !== undefined)
      cmp('faceFrames', (measured.faceFrames ?? 0) >= gates.faceFrames);
    if (gates.voiceSimilarity !== undefined)
      cmp('voiceSimilarity', (measured.voiceSimilarity ?? 0) >= gates.voiceSimilarity);
    if (gates.voicePrecision !== undefined)
      cmp('voicePrecision', (measured.voicePrecision ?? 0) >= gates.voicePrecision);
    if (gates.voicedRatio !== undefined)
      cmp('voicedRatio', (measured.voicedRatio ?? 0) >= gates.voicedRatio);
    if (gates.referenceSeconds !== undefined)
      cmp('referenceSeconds', (measured.referenceSeconds ?? 0) >= gates.referenceSeconds);
    if (gates.referenceSnrDb !== undefined)
      cmp('referenceSnrDb', (measured.referenceSnrDb ?? -Infinity) >= gates.referenceSnrDb);
    if (gates.spectralDistance !== undefined)
      cmp('spectralDistance', (measured.spectralDistance ?? 1) <= gates.spectralDistance);
    if (gates.integrityClean !== undefined)
      cmp('integrityClean', measured.integrityClean === true);
    return { passed, failed };
  };

  const hyper = check(MODES.scientific.gates.hyperrealism);
  if (!hyper.failed.length) return { mode: 'scientific', realism: 'hyperrealism', ...hyper };
  const real = check(MODES.scientific.gates.realism);
  if (!real.failed.length) return { mode: 'scientific', realism: 'realism', ...real };
  const pro = check(MODES.professional.gates);
  if (!pro.failed.length) return { mode: 'professional', realism: null, ...pro };
  return { mode: 'basic', realism: null, passed: pro.passed, failed: pro.failed };
}

export default MODES;
