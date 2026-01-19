/**
 * Faicey - Three.js Face Rendering System for mindX
 * Main entry point - exports all core components
 */

// Core components
export { default as FaceRenderer } from './core/FaceRenderer.js';
export { default as FaceGeometry } from './core/FaceGeometry.js';
export { default as ExpressionController } from './core/ExpressionController.js';
export { default as WireframeController } from './core/WireframeController.js';

// Agent integration
export { default as FaiceyAgent, createFaiceyAgent } from './faicey_agent.js';

// Examples
export { default as ProfessorCodephreakFace } from './examples/professor-codephreak.js';
export { default as BasicFaceDemo } from './examples/basic-face.js';

// Utilities
export {
  MorphTarget,
  MorphTargetLibrary,
  PHONEME_MAP,
  textToPhonemes,
  phonemesToMorphs
} from './lib/MorphTargets.js';

// Version info
export const VERSION = '0.1.0';
export const DESCRIPTION = 'Three.js-based face rendering system for mindX personas';

/**
 * Quick start helper
 */
export async function quickStart(personaName = 'professor-codephreak') {
  const { createFaiceyAgent } = await import('./faicey_agent.js');
  const agent = await createFaiceyAgent(personaName);
  agent.start();
  return agent;
}

export default {
  FaceRenderer,
  FaceGeometry,
  ExpressionController,
  WireframeController,
  FaiceyAgent,
  createFaiceyAgent,
  ProfessorCodephreakFace,
  BasicFaceDemo,
  quickStart,
  VERSION,
  DESCRIPTION
};
