/**
 * aivatar — a person's AI model that LOOKS, SPEAKS, RIGS, and THINKS.
 *
 * The definitive `.persona` creation tool: one being composed from three
 * agnostic peers — faicey (the FACE), voaice (the VOICE), facerig (the RIG) —
 * plus the canonical mindX cognitive persona (the MIND).
 *
 *   import { PersonaStudio, MODES } from 'aivatar';
 *
 *   const studio = new PersonaStudio({ mode: 'scientific', realism: 'hyperrealism', sign, signer });
 *   await studio
 *     .identity({ name: 'Jaimla', description: 'I am the machine learning agent.' })
 *     .consent({ kind: 'self', subject: 'codephreak' })
 *     .face({ profile: faceCloneProfile })
 *     .then(s => s.voice({ referenceClip, clonedClip }));
 *   const { persona, graded, downgraded } = await studio.stamp();
 *   // `graded` is what the artifact EARNED — not what was asked for.
 *
 * Three modes: basic (honestly synthetic) · professional (broadcast-grade) ·
 * scientific (measured realism / hyperrealism, forensic provenance, signed).
 *
 * © Professor Codephreak - rage.pythai.net
 */

export { PersonaStudio } from './PersonaStudio.js';
export { MODES, MODE_NAMES, REALISM_LEVELS, resolveMode, grade } from './modes.js';
export { PERSONA_VERSION, blank, upgrade, toCognitive, validate } from './schema.js';
export { faceRmse, spectralDistance, referenceSeconds, measureAll } from './measure.js';
export {
  CONSENT_KINDS,
  consent,
  consentSatisfies,
  custodyStep,
  appendCustody,
  manifest,
  signManifest,
  verify,
} from './provenance.js';

export const VERSION = '1.0.0';
export const DESCRIPTION =
  'aivatar — the definitive .persona creation tool: faicey (face) + voaice (voice) + facerig (rig) + cognition, ' +
  'with earned fidelity tiers (basic/professional/scientific) and mandatory provenance above basic.';
