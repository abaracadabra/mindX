/**
 * ExpressionController - Manages facial expressions and morph target animations
 * Handles complex expression combinations and smooth transitions
 */

export default class ExpressionController {
  constructor(faceMesh) {
    this.faceMesh = faceMesh;
    this.morphTargetInfluences = faceMesh.morphTargetInfluences || [];
    this.currentExpressions = {};
    this.animations = [];

    // Expression presets combining multiple morph targets
    this.expressions = {
      neutral: {},
      smile: { smile: 1.0 },
      laugh: { smile: 1.0, mouth_open: 0.6 },
      frown: { frown: 1.0 },
      sad: { frown: 0.8, eyebrows_furrowed: 0.5 },
      surprised: { eyebrows_raised: 1.0, mouth_open: 0.8 },
      thinking: { eyebrows_furrowed: 0.7 },
      confused: { eyebrows_furrowed: 1.0, frown: 0.3 },
      wink: { wink_left: 1.0, smile: 0.5 },
      blink: { blink: 1.0 },
      coding: { eyebrows_furrowed: 0.4, smile: 0.3 }, // Professor Codephreak default
      speaking: { mouth_open: 0.3 },
      happy: { smile: 1.0, eyebrows_raised: 0.3 },
    };

    // Map morph names to indices
    this.morphMap = {};
    if (faceMesh.geometry && faceMesh.geometry.morphAttributes.position) {
      faceMesh.geometry.morphAttributes.position.forEach((attr, index) => {
        const name = this.getMorphNameByIndex(index);
        if (name) {
          this.morphMap[name] = index;
        }
      });
    }
  }

  /**
   * Get morph target name by index (from FaceGeometry)
   */
  getMorphNameByIndex(index) {
    const morphNames = [
      'smile',
      'frown',
      'mouth_open',
      'blink',
      'wink_left',
      'wink_right',
      'eyebrows_raised',
      'eyebrows_furrowed',
    ];
    return morphNames[index];
  }

  /**
   * Set a specific expression
   * @param {string} expressionName - Name of expression preset
   * @param {number} intensity - Overall intensity (0-1)
   * @param {number} duration - Transition duration in ms
   */
  setExpression(expressionName, intensity = 1.0, duration = 300) {
    const expression = this.expressions[expressionName];
    if (!expression) {
      console.warn(`Unknown expression: ${expressionName}`);
      return;
    }

    // Reset all morph targets to 0 first
    Object.keys(this.morphMap).forEach(morphName => {
      if (!expression[morphName]) {
        this.animateMorph(morphName, 0, duration);
      }
    });

    // Apply expression morphs
    Object.entries(expression).forEach(([morphName, value]) => {
      this.animateMorph(morphName, value * intensity, duration);
    });

    this.currentExpressions = { ...expression };
    console.log(`Expression set to: ${expressionName} (intensity: ${intensity})`);
  }

  /**
   * Animate a specific morph target
   * @param {string} morphName - Morph target name
   * @param {number} targetValue - Target value (0-1)
   * @param {number} duration - Animation duration in ms
   */
  animateMorph(morphName, targetValue, duration = 300) {
    const morphIndex = this.morphMap[morphName];
    if (morphIndex === undefined) {
      console.warn(`Unknown morph target: ${morphName}`);
      return;
    }

    const startValue = this.morphTargetInfluences[morphIndex] || 0;
    const startTime = Date.now();

    // Add animation to queue
    this.animations.push({
      morphIndex,
      morphName,
      startValue,
      targetValue,
      startTime,
      duration,
    });
  }

  /**
   * Set morph target directly (no animation)
   * @param {string} morphName - Morph target name
   * @param {number} value - Value (0-1)
   */
  setMorphDirect(morphName, value) {
    const morphIndex = this.morphMap[morphName];
    if (morphIndex !== undefined) {
      this.morphTargetInfluences[morphIndex] = Math.max(0, Math.min(1, value));
    }
  }

  /**
   * Update animation loop (called from FaceRenderer)
   */
  update() {
    const now = Date.now();

    // Update all active animations
    this.animations = this.animations.filter(anim => {
      const elapsed = now - anim.startTime;
      const progress = Math.min(elapsed / anim.duration, 1.0);

      // Ease-in-out interpolation
      const eased = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2;

      const currentValue = anim.startValue + (anim.targetValue - anim.startValue) * eased;
      this.morphTargetInfluences[anim.morphIndex] = currentValue;

      // Remove animation if complete
      return progress < 1.0;
    });
  }

  /**
   * Blend multiple expressions
   * @param {Object} expressionWeights - Map of expression names to weights
   * @param {number} duration - Transition duration
   */
  blendExpressions(expressionWeights, duration = 300) {
    const combinedMorphs = {};

    // Combine all expression morphs with weights
    Object.entries(expressionWeights).forEach(([exprName, weight]) => {
      const expression = this.expressions[exprName];
      if (expression) {
        Object.entries(expression).forEach(([morphName, value]) => {
          combinedMorphs[morphName] = (combinedMorphs[morphName] || 0) + value * weight;
        });
      }
    });

    // Normalize and apply
    Object.entries(combinedMorphs).forEach(([morphName, value]) => {
      this.animateMorph(morphName, Math.min(value, 1.0), duration);
    });
  }

  /**
   * Create periodic animation (like idle breathing)
   * @param {string} morphName - Morph target to animate
   * @param {number} frequency - Frequency in Hz
   * @param {number} amplitude - Amplitude (0-1)
   */
  createPeriodicAnimation(morphName, frequency, amplitude) {
    const morphIndex = this.morphMap[morphName];
    if (morphIndex === undefined) return;

    const animate = () => {
      const time = Date.now() / 1000;
      const value = (Math.sin(time * frequency * Math.PI * 2) + 1) / 2 * amplitude;
      this.morphTargetInfluences[morphIndex] = value;
    };

    setInterval(animate, 16); // ~60fps
  }

  /**
   * Blink animation sequence
   */
  async blink() {
    this.animateMorph('blink', 1.0, 100);
    await this.sleep(100);
    this.animateMorph('blink', 0.0, 100);
  }

  /**
   * Random blink behavior (natural)
   */
  startRandomBlinks() {
    const blinkInterval = () => {
      this.blink();
      const nextBlink = 2000 + Math.random() * 4000; // 2-6 seconds
      setTimeout(blinkInterval, nextBlink);
    };
    blinkInterval();
  }

  /**
   * Speaking animation (mouth movement)
   * @param {string} text - Text being spoken (for future phoneme mapping)
   */
  speak(text) {
    // Simple mouth movement for speaking
    const syllables = text.split(' ').length;
    const baseDelay = 150;

    for (let i = 0; i < syllables; i++) {
      setTimeout(() => {
        this.animateMorph('mouth_open', 0.3 + Math.random() * 0.2, 100);
        setTimeout(() => {
          this.animateMorph('mouth_open', 0, 100);
        }, 100);
      }, i * baseDelay);
    }
  }

  /**
   * Get current expression state
   */
  getCurrentState() {
    return {
      currentExpressions: this.currentExpressions,
      morphInfluences: this.morphTargetInfluences.map((val, idx) => ({
        name: this.getMorphNameByIndex(idx),
        value: val,
      })),
      activeAnimations: this.animations.length,
    };
  }

  /**
   * Utility sleep function
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
