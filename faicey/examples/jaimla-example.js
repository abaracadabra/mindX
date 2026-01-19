/**
 * Jaimla Example
 * Demonstrates face rendering for Jaimla - versatile multimodal ML agent
 * Reference: github.com/jaimla
 */

import FaceRenderer from '../core/FaceRenderer.js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class JaimlaFace {
  constructor() {
    this.renderer = null;
    this.config = null;
    this.currentActivity = 'idle';
    this.loadConfig();
  }

  /**
   * Load Jaimla persona configuration
   */
  loadConfig() {
    try {
      const configPath = join(__dirname, '../config/personas.json');
      const configData = readFileSync(configPath, 'utf-8');
      const allConfigs = JSON.parse(configData);
      this.config = allConfigs.personas['jaimla'];
      console.log('✓ Loaded Jaimla configuration');
    } catch (error) {
      console.error('Failed to load config:', error.message);
      this.config = this.getDefaultConfig();
    }
  }

  /**
   * Get default configuration if file not found
   */
  getDefaultConfig() {
    return {
      name: 'Jaimla',
      defaultExpression: 'happy',
      wireframe: {
        enabled: true,
        color: '0xff0080',
        thickness: 1.1,
      },
    };
  }

  /**
   * Initialize the face renderer
   */
  init() {
    const wireframeColor = parseInt(this.config.wireframe.color);

    this.renderer = new FaceRenderer({
      wireframe: this.config.wireframe.enabled,
      faceColor: wireframeColor,
      wireframeThickness: this.config.wireframe.thickness,
      backgroundColor: 0x000000,
      expressions: true,
    });

    this.renderer.init();

    // Set initial expression
    this.renderer.setExpression(this.config.defaultExpression);

    console.log('✓ Jaimla face initialized');
    console.log(`  Default expression: ${this.config.defaultExpression}`);
    console.log(`  Wireframe: ${this.config.wireframe.enabled ? 'enabled' : 'disabled'}`);
    console.log(`  Color: Vibrant Pink (${this.config.wireframe.color})`);
    console.log(`  Gender: Female`);

    return this;
  }

  /**
   * Start the animation loop
   */
  start() {
    if (!this.renderer) {
      console.error('Renderer not initialized. Call init() first.');
      return;
    }

    console.log('✓ Starting animation...');
    this.renderer.animate();

    // Start natural blinking
    if (this.renderer.expressionController) {
      this.renderer.expressionController.startRandomBlinks();
    }

    // Run demo sequence
    this.runDemoSequence();

    return this;
  }

  /**
   * Run a demonstration sequence showing Jaimla's capabilities
   */
  async runDemoSequence() {
    console.log('\n=== Jaimla Multimodal ML Agent Demo ===\n');

    await this.sleep(2000);

    // Idle state - friendly and welcoming
    console.log('[State: Idle - Ready to collaborate]');
    this.setActivity('idle');
    await this.sleep(3000);

    // Processing multimodal input
    console.log('[Activity: Processing multimodal data]');
    this.setActivity('processing');
    await this.sleep(3000);

    // Learning from new data
    console.log('[Activity: Learning from interactions]');
    this.setActivity('learning');
    await this.sleep(3000);

    // Discovery moment
    console.log('[Activity: Discovering new patterns!]');
    this.setActivity('discovering');
    await this.sleep(2000);

    // Collaborating with other agents
    console.log('[Activity: Collaborating with AUTOMINDx & Faicey]');
    this.setActivity('collaborating');
    this.speak('Working together makes us stronger!');
    await this.sleep(4000);

    // Teaching mode
    console.log('[Activity: Teaching - Sharing knowledge]');
    this.setActivity('teaching');
    this.speak('Let me show you what I learned');
    await this.sleep(4000);

    // Back to happy idle
    console.log('[State: Content - Ready for next task]');
    this.setActivity('idle');
    await this.sleep(2000);

    console.log('\n=== Demo sequence complete ===\n');
    console.log('Jaimla is ready for multimodal collaboration...');

    // Return to default
    this.setActivity('idle');
  }

  /**
   * Set current activity and update expression
   * @param {string} activity - Activity name from config
   */
  setActivity(activity) {
    this.currentActivity = activity;

    const expressions = this.config.expressions;
    if (!expressions || !expressions[activity]) {
      console.warn(`Unknown activity: ${activity}`);
      return;
    }

    const activityConfig = expressions[activity];
    const expression = activityConfig.base || activity;
    const intensity = activityConfig.intensity || 1.0;

    this.renderer.setExpression(expression, intensity);
  }

  /**
   * Make Jaimla speak
   * @param {string} text - Text to speak
   */
  speak(text) {
    console.log(`  💬 Jaimla: "${text}"`);
    if (this.renderer.expressionController) {
      this.renderer.expressionController.speak(text);
    }
  }

  /**
   * Demonstrate multimodal capabilities
   */
  demonstrateMultimodal() {
    console.log('\n=== Multimodal Capabilities Demo ===');
    console.log('✓ Text Processing (NLP)');
    console.log('✓ Voice Recognition (Audio)');
    console.log('✓ Computer Vision (Image)');
    console.log('✓ Recommendation Systems');
    console.log('✓ Autonomous Agent Orchestration');
    console.log('\nDeployment: Local, Handheld, Offline-capable');
    console.log('Collaboration: AUTOMINDx, Faicey, Open-source community\n');
  }

  /**
   * Rotate face to look at angle
   * @param {number} yaw - Horizontal rotation
   * @param {number} pitch - Vertical rotation
   */
  lookAt(yaw, pitch) {
    this.renderer.setRotation(pitch, yaw, 0);
  }

  /**
   * Get current state for debugging
   */
  getState() {
    return {
      persona: this.config.name,
      gender: 'female',
      activity: this.currentActivity,
      capabilities: this.config.capabilities,
      rendererState: this.renderer.exportState(),
    };
  }

  /**
   * Stop and cleanup
   */
  stop() {
    console.log('Stopping Jaimla...');
    if (this.renderer) {
      this.renderer.stopAnimation();
      this.renderer.dispose();
    }
  }

  /**
   * Utility sleep function
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Main execution
if (import.meta.url === `file://${process.argv[1]}`) {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║         Jaimla Face Renderer                   ║');
  console.log('║   Versatile Multimodal ML Agent (Female)       ║');
  console.log('║   github.com/jaimla                            ║');
  console.log('║   Powered by three.js + mindX faicey           ║');
  console.log('╚════════════════════════════════════════════════╝\n');

  const jaimla = new JaimlaFace();
  jaimla.init();
  jaimla.demonstrateMultimodal();
  jaimla.start();

  // Handle cleanup on exit
  process.on('SIGINT', () => {
    console.log('\n\nShutting down gracefully...');
    jaimla.stop();
    process.exit(0);
  });

  // Keep process alive
  setInterval(() => {
    // Periodic state logging (optional)
    // console.log('State:', jaimla.getState());
  }, 10000);
}

export default JaimlaFace;
