/**
 * schema.js — the aivatar `.persona` (v2).
 *
 * A `.persona` file is the whole being of an AI actor in one JSON document:
 * how it THINKS (the canonical mindX cognitive block — beliefs, desires,
 * traits, inference roster), how it LOOKS and SOUNDS (embodiment: faceprint,
 * voiceprint, rig), how REAL it is (fidelity: mode, realism, measurements),
 * and WHERE IT CAME FROM (provenance: consent, custody, signed manifest).
 *
 * v2 is a strict SUPERSET of the v1 cognitive `.persona` (agents/boardroom/*.persona,
 * drAIML): every v1 field keeps its meaning and position, so a v1 file loads as
 * a v2 persona with an empty embodiment (`upgrade()`), and every v2 persona is
 * still a valid cognitive persona to anything that only reads v1 fields.
 *
 *   identity     name, id, label, description
 *   cognition    v1 block: communication_style, behavioral_traits,
 *                expertise_areas, beliefs, desires, inference, authority
 *   embodiment   face {faceprint, source, frames}, voice {voiceprint, engine,
 *                reference}, rig {fps, blendshapes, live}
 *   fidelity     mode, realism, measured{}, graded{}  ← EARNED, not declared
 *   provenance   consent, custody[], manifest         ← mandatory ≥ professional
 *   media        export targets + settings actually used
 *   aiml         interaction bindings (chat/agent hookup, x402, iNFT)
 *
 * © Professor Codephreak - rage.pythai.net
 */

export const PERSONA_VERSION = 2;

/** An empty, valid v2 persona. */
export function blank() {
  return {
    v: PERSONA_VERSION,
    kind: 'aivatar-persona',
    identity: { name: null, agent_id: null, label: null, description: null, role: null },
    cognition: {
      communication_style: null,
      behavioral_traits: [],
      expertise_areas: [],
      beliefs: {},
      desires: {},
      inference: {},
      authority: {},
    },
    embodiment: {
      face: null, // {faceprint, source, frames, render}
      voice: null, // {voiceprint, engine, sampleRate, bitDepth, referenceSeconds}
      rig: null, // {fps, blendshapes, liveReenactment}
    },
    fidelity: { mode: 'basic', realism: null, measured: {}, graded: null },
    provenance: { consent: null, custody: [], manifest: null },
    media: { formats: [], settings: {} },
    aiml: { bindings: {}, x402: null, inft: null },
    hash: null, // persona print (faicey personaPrint) — the identity anchor
  };
}

/** Load a v1 cognitive `.persona` (or a partial) into a full v2 persona. */
export function upgrade(v1 = {}) {
  if (v1 && v1.kind === 'aivatar-persona') return v1; // already v2
  const p = blank();
  p.identity = {
    name: v1.name ?? null,
    agent_id: v1.agent_id ?? null,
    label: v1.label ?? v1.name ?? null,
    description: v1.description ?? null,
    role: v1.role ?? null,
  };
  p.cognition = {
    communication_style: v1.communication_style ?? null,
    behavioral_traits: v1.behavioral_traits ?? [],
    expertise_areas: v1.expertise_areas ?? [],
    beliefs: v1.beliefs ?? {},
    desires: v1.desires ?? {},
    inference: v1.inference ?? {},
    authority: v1.authority ?? {},
  };
  if (v1.weight !== undefined) p.cognition.weight = v1.weight;
  return p;
}

/** Project a v2 persona back down to the v1 cognitive shape (for BDI agents). */
export function toCognitive(p) {
  return {
    name: p.identity.name,
    agent_id: p.identity.agent_id,
    role: p.identity.role,
    description: p.identity.description,
    ...p.cognition,
  };
}

/**
 * Validate a persona. Returns structural errors AND doctrine violations —
 * a persona claiming a fidelity it did not earn, or a clone of a real subject
 * with no consent, is INVALID, not merely impolite.
 * @returns {{ok:boolean, errors:string[], warnings:string[]}}
 */
export function validate(p) {
  const errors = [];
  const warnings = [];
  if (!p || p.kind !== 'aivatar-persona') return { ok: false, errors: ['not an aivatar persona'], warnings };
  if (p.v !== PERSONA_VERSION) warnings.push(`persona version ${p.v} (expected ${PERSONA_VERSION})`);
  if (!p.identity?.name) errors.push('identity.name is required');

  const mode = p.fidelity?.mode;
  if (!['basic', 'professional', 'scientific'].includes(mode)) {
    errors.push(`fidelity.mode must be basic|professional|scientific (got ${mode})`);
  }
  const hasFace = !!p.embodiment?.face;
  const hasVoice = !!p.embodiment?.voice;
  if (!hasFace && !hasVoice) errors.push('embodiment needs a face and/or a voice');

  // Doctrine: the claimed tier must be the tier the measurements EARNED.
  if (p.fidelity?.graded) {
    const g = p.fidelity.graded;
    if (g.mode !== mode) {
      errors.push(
        `fidelity.mode "${mode}" was not earned — measurements grade as "${g.mode}"` +
          (g.failed?.length ? ` (failed: ${g.failed.join(', ')})` : '')
      );
    }
    if (mode === 'scientific' && g.realism !== p.fidelity.realism) {
      errors.push(`realism "${p.fidelity.realism}" not earned — graded "${g.realism}"`);
    }
  } else if (mode !== 'basic') {
    errors.push(`fidelity.mode "${mode}" requires measurements (fidelity.graded is null)`);
  }

  // Doctrine: provenance is mandatory above basic.
  if (mode !== 'basic') {
    if (!p.provenance?.consent) errors.push(`${mode} tier requires a consent record`);
    if (!p.provenance?.manifest) errors.push(`${mode} tier requires a signed manifest`);
    else if (!p.provenance.manifest.signature) {
      if (mode === 'scientific') errors.push('scientific tier requires the manifest to be SIGNED');
      else warnings.push('manifest is unsigned');
    }
    if (mode === 'scientific' && !(p.provenance?.custody?.length >= 1)) {
      errors.push('scientific tier requires a custody chain');
    }
  }
  return { ok: errors.length === 0, errors, warnings };
}

export default { PERSONA_VERSION, blank, upgrade, toCognitive, validate };
