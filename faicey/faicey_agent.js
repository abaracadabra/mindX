/**
 * Faicey Agent - Integration layer for mindX
 * Connects face rendering system with mindX agents and personality system
 */

import FaceRenderer from './core/FaceRenderer.js';
import ProfessorCodephreakFace from './examples/professor-codephreak.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class FaiceyAgent {
  constructor(personaName = 'mindx-base') {
    this.personaName = personaName;
    this.renderer = null;
    this.config = null;
    this.eventHandlers = {};
    this.isInitialized = false;
  }

  /**
   * Initialize the agent with specified persona
   */
  async init() {
    console.log(`Initializing Faicey Agent with persona: ${this.personaName}`);

    // Load persona configuration
    this.loadPersonaConfig();

    // Create appropriate renderer based on persona
    if (this.personaName === 'professor-codephreak') {
      this.renderer = new ProfessorCodephreakFace();
      this.renderer.init();
    } else {
      this.renderer = new FaceRenderer({
        wireframe: this.config?.wireframe?.enabled || true,
        faceColor: parseInt(this.config?.wireframe?.color || '0x00aaff'),
        expressions: true,
      });
      this.renderer.init();

      // Set default expression
      if (this.config?.defaultExpression) {
        this.renderer.setExpression(this.config.defaultExpression);
      }
    }

    this.isInitialized = true;
    console.log('✓ Faicey Agent initialized');

    return this;
  }

  /**
   * Load persona configuration from JSON
   */
  loadPersonaConfig() {
    try {
      const configPath = join(__dirname, 'config/personas.json');
      const configData = readFileSync(configPath, 'utf-8');
      const allConfigs = JSON.parse(configData);
      this.config = allConfigs.personas[this.personaName];

      if (!this.config) {
        console.warn(`Persona "${this.personaName}" not found, using defaults`);
        this.config = this.getDefaultConfig();
      }
    } catch (error) {
      console.error('Error loading persona config:', error.message);
      this.config = this.getDefaultConfig();
    }
  }

  /**
   * Get default configuration
   */
  getDefaultConfig() {
    return {
      name: this.personaName,
      defaultExpression: 'neutral',
      wireframe: {
        enabled: true,
        color: '0x00aaff',
        thickness: 1.0,
      },
    };
  }

  /**
   * Process agent message/event and update face
   * @param {Object} event - Event from mindX agent
   */
  processEvent(event) {
    if (!this.isInitialized) {
      console.warn('Agent not initialized');
      return;
    }

    const { type, data } = event;

    switch (type) {
      case 'thinking':
        this.setExpression('thinking');
        break;

      case 'speaking':
        this.speak(data.text || '');
        break;

      case 'listening':
        this.setExpression('neutral');
        break;

      case 'processing':
        this.setExpression('coding');
        break;

      case 'success':
        this.setExpression('happy');
        break;

      case 'error':
        this.setExpression('confused');
        break;

      case 'expression':
        this.setExpression(data.expression, data.intensity);
        break;

      case 'emotion':
        this.handleEmotion(data.emotion, data.intensity);
        break;

      default:
        console.log(`Unknown event type: ${type}`);
    }

    // Emit to registered handlers
    this.emit(type, data);
  }

  /**
   * Handle emotional state changes
   * @param {string} emotion - Emotion name
   * @param {number} intensity - Intensity (0-1)
   */
  handleEmotion(emotion, intensity = 1.0) {
    const emotionMap = {
      joy: 'happy',
      happiness: 'smile',
      sadness: 'sad',
      surprise: 'surprised',
      confusion: 'confused',
      focus: 'thinking',
      excitement: 'laugh',
      contemplation: 'thinking',
    };

    const expression = emotionMap[emotion.toLowerCase()] || 'neutral';
    this.setExpression(expression, intensity);
  }

  /**
   * Set facial expression
   * @param {string} expression - Expression name
   * @param {number} intensity - Intensity (0-1)
   */
  setExpression(expression, intensity = 1.0) {
    if (this.renderer && this.renderer.setExpression) {
      this.renderer.setExpression(expression, intensity);
    } else if (this.renderer && this.renderer.renderer) {
      this.renderer.renderer.setExpression(expression, intensity);
    }
  }

  /**
   * Make the persona speak
   * @param {string} text - Text to speak
   */
  speak(text) {
    if (this.renderer && this.renderer.speak) {
      this.renderer.speak(text);
    } else if (this.renderer && this.renderer.expressionController) {
      this.renderer.expressionController.speak(text);
    }
  }

  /**
   * Start animation loop
   */
  start() {
    if (!this.isInitialized) {
      console.warn('Agent not initialized. Call init() first.');
      return;
    }

    if (this.renderer && this.renderer.start) {
      this.renderer.start();
    } else if (this.renderer && this.renderer.animate) {
      this.renderer.animate();

      // Start natural blinking if available
      if (this.renderer.expressionController) {
        this.renderer.expressionController.startRandomBlinks();
      }
    }

    console.log('✓ Faicey Agent started');
    return this;
  }

  /**
   * Register event handler
   * @param {string} event - Event name
   * @param {Function} handler - Handler function
   */
  on(event, handler) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(handler);
  }

  /**
   * Emit event to registered handlers
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    const handlers = this.eventHandlers[event] || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error(`Error in event handler for ${event}:`, error);
      }
    });
  }

  /**
   * Get current state
   */
  getState() {
    return {
      persona: this.personaName,
      initialized: this.isInitialized,
      config: this.config,
      rendererState: this.renderer?.getState?.() || null,
    };
  }

  /**
   * Export face data for external use
   */
  exportFaceData() {
    if (!this.renderer) return null;

    return {
      persona: this.personaName,
      state: this.renderer.exportState ? this.renderer.exportState() : null,
      timestamp: Date.now(),
    };
  }

  /**
   * Stop and cleanup
   */
  stop() {
    console.log('Stopping Faicey Agent...');

    if (this.renderer && this.renderer.stop) {
      this.renderer.stop();
    } else if (this.renderer && this.renderer.stopAnimation) {
      this.renderer.stopAnimation();
    }

    this.isInitialized = false;
  }
}

/**
 * Create faicey agent for mindX integration
 * @param {string} personaName - Persona identifier
 * @returns {FaiceyAgent} Initialized agent
 */
export async function createFaiceyAgent(personaName = 'mindx-base') {
  const agent = new FaiceyAgent(personaName);
  await agent.init();
  return agent;
}

export default FaiceyAgent;
