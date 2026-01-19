/**
 * MorphTargets - Utility library for morph target management
 * Provides helpers for creating and managing facial morph targets
 */

export class MorphTarget {
  constructor(name, vertices) {
    this.name = name;
    this.vertices = vertices;
  }

  /**
   * Blend with another morph target
   * @param {MorphTarget} other - Other morph target
   * @param {number} weight - Blend weight (0-1)
   */
  blend(other, weight) {
    if (this.vertices.length !== other.vertices.length) {
      throw new Error('Morph targets must have same vertex count');
    }

    const blended = new Float32Array(this.vertices.length);
    for (let i = 0; i < this.vertices.length; i++) {
      blended[i] = this.vertices[i] * (1 - weight) + other.vertices[i] * weight;
    }

    return new MorphTarget(`${this.name}_blend_${other.name}`, blended);
  }
}

export class MorphTargetLibrary {
  constructor() {
    this.targets = new Map();
  }

  /**
   * Add a morph target to the library
   */
  add(morphTarget) {
    this.targets.set(morphTarget.name, morphTarget);
  }

  /**
   * Get a morph target by name
   */
  get(name) {
    return this.targets.get(name);
  }

  /**
   * Check if target exists
   */
  has(name) {
    return this.targets.has(name);
  }

  /**
   * Get all target names
   */
  getNames() {
    return Array.from(this.targets.keys());
  }

  /**
   * Create a combined morph from multiple targets
   * @param {Object} weights - Map of morph names to weights
   */
  combine(weights) {
    const morphs = Object.entries(weights)
      .map(([name, weight]) => ({ morph: this.get(name), weight }))
      .filter(({ morph }) => morph !== undefined);

    if (morphs.length === 0) {
      throw new Error('No valid morph targets found');
    }

    const baseVertices = morphs[0].morph.vertices;
    const combined = new Float32Array(baseVertices.length);

    // Initialize with zeros
    combined.fill(0);

    // Add weighted contributions
    morphs.forEach(({ morph, weight }) => {
      for (let i = 0; i < combined.length; i++) {
        combined[i] += morph.vertices[i] * weight;
      }
    });

    const name = Object.keys(weights).join('_');
    return new MorphTarget(`combined_${name}`, combined);
  }
}

/**
 * Phoneme to morph target mapping for speech animation
 */
export const PHONEME_MAP = {
  // Vowels
  'A': { mouth_open: 0.8, smile: 0.2 },
  'E': { smile: 0.6, mouth_open: 0.4 },
  'I': { smile: 0.8, mouth_open: 0.3 },
  'O': { mouth_open: 0.7 },
  'U': { mouth_open: 0.5 },

  // Consonants
  'M': { mouth_open: 0.0 },
  'P': { mouth_open: 0.1 },
  'B': { mouth_open: 0.2 },
  'F': { mouth_open: 0.3, frown: 0.2 },
  'V': { mouth_open: 0.3 },
  'TH': { mouth_open: 0.4 },
  'S': { smile: 0.3, mouth_open: 0.2 },
  'Z': { smile: 0.3, mouth_open: 0.2 },
  'L': { mouth_open: 0.4 },
  'R': { mouth_open: 0.3 },

  // Default
  'default': { mouth_open: 0.2 },
};

/**
 * Convert text to phoneme sequence (simplified)
 * @param {string} text - Input text
 * @returns {Array} Array of phoneme names
 */
export function textToPhonemes(text) {
  // This is a very simplified phoneme extraction
  // In production, use a proper TTS phoneme library
  const words = text.toUpperCase().split(' ');
  const phonemes = [];

  words.forEach(word => {
    for (let i = 0; i < word.length; i++) {
      const char = word[i];
      if (PHONEME_MAP[char]) {
        phonemes.push(char);
      } else {
        phonemes.push('default');
      }
    }
    phonemes.push('default'); // Pause between words
  });

  return phonemes;
}

/**
 * Create morph sequence from phonemes
 * @param {Array} phonemes - Array of phoneme names
 * @returns {Array} Array of {morphs, duration} objects
 */
export function phonemesToMorphs(phonemes) {
  return phonemes.map(phoneme => ({
    morphs: PHONEME_MAP[phoneme] || PHONEME_MAP.default,
    duration: 100, // ms per phoneme
  }));
}

export default {
  MorphTarget,
  MorphTargetLibrary,
  PHONEME_MAP,
  textToPhonemes,
  phonemesToMorphs,
};
