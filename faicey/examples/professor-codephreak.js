/**
 * Professor Codephreak Example
 * Demonstrates face rendering for Professor Codephreak persona
 * github.com/Professor-Codephreak
 */

import FaceRenderer from '../core/FaceRenderer.js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class ProfessorCodephreakFace {
  constructor() {
    this.renderer = null;
    this.config = null;
    this.currentActivity = 'idle';
    this.loadConfig();
  }

  /**
   * Load persona configuration
   */
  loadConfig() {
    try {
      const configPath = join(__dirname, '../config/personas.json');
      const configData = readFileSync(configPath, 'utf-8');
      const allConfigs = JSON.parse(configData);
      this.config = allConfigs.personas['professor-codephreak'];
      console.log('✓ Loaded Professor Codephreak configuration');
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
      name: 'Professor Codephreak',
      defaultExpression: 'coding',
      wireframe: {
        enabled: true,
        color: '0x00ff00',
        thickness: 1.5,
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

    console.log('✓ Professor Codephreak face initialized');
    console.log(`  Default expression: ${this.config.defaultExpression}`);
    console.log(`  Wireframe: ${this.config.wireframe.enabled ? 'enabled' : 'disabled'}`);

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
   * Run a demonstration sequence showing different expressions
   */
  async runDemoSequence() {
    console.log('\n=== Professor Codephreak Demo Sequence ===\n');

    await this.sleep(2000);

    // Coding mode
    console.log('[Activity: Coding]');
    this.setActivity('coding');
    await this.sleep(3000);

    // Thinking about a problem
    console.log('[Activity: Deep Thinking]');
    this.setActivity('thinking');
    await this.sleep(3000);

    // Found the solution!
    console.log('[Activity: Eureka moment!]');
    this.setActivity('eureka');
    await this.sleep(2000);

    // Explaining the solution
    console.log('[Activity: Explaining code]');
    this.setActivity('explaining');
    this.speak('Let me explain how this algorithm works');
    await this.sleep(4000);

    // Back to coding
    console.log('[Activity: Coding]');
    this.setActivity('coding');
    await this.sleep(3000);

    // Debugging mode
    console.log('[Activity: Debugging]');
    this.setActivity('debugging');
    await this.sleep(3000);

    // Success!
    console.log('[Activity: Happy - Bug fixed!]');
    this.setActivity('eureka');
    await this.sleep(2000);

    console.log('\n=== Demo sequence complete ===\n');
    console.log('Professor Codephreak continues coding...');

    // Return to default
    this.setActivity('coding');
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
   * Make Professor Codephreak speak
   * @param {string} text - Text to speak
   */
  speak(text) {
    console.log(`  💬 "${text}"`);
    if (this.renderer.expressionController) {
      this.renderer.expressionController.speak(text);
    }
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
      activity: this.currentActivity,
      rendererState: this.renderer.exportState(),
    };
  }

  /**
   * Stop and cleanup
   */
  stop() {
    console.log('Stopping Professor Codephreak...');
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
  console.log('║   Professor Codephreak Face Renderer          ║');
  console.log('║   github.com/Professor-Codephreak             ║');
  console.log('║   Powered by three.js + mindX faicey          ║');
  console.log('╚════════════════════════════════════════════════╝\n');

  const professor = new ProfessorCodephreakFace();
  professor.init().start();

  // Handle cleanup on exit
  process.on('SIGINT', () => {
    console.log('\n\nShutting down gracefully...');
    professor.stop();
    process.exit(0);
  });

  // Keep process alive
  setInterval(() => {
    // Periodic state logging (optional)
    // console.log('State:', professor.getState());
  }, 10000);
}

export default ProfessorCodephreakFace;
