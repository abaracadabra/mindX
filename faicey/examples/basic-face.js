/**
 * Basic Face Example
 * Simple demonstration of faicey face rendering
 */

import FaceRenderer from '../core/FaceRenderer.js';

class BasicFaceDemo {
  constructor() {
    this.renderer = null;
  }

  /**
   * Initialize renderer with basic settings
   */
  init() {
    this.renderer = new FaceRenderer({
      wireframe: true,
      faceColor: 0x00aaff,
      backgroundColor: 0x000000,
      expressions: true,
    });

    this.renderer.init();
    console.log('✓ Basic face initialized');

    return this;
  }

  /**
   * Start animation and demo
   */
  start() {
    console.log('✓ Starting basic face demo...\n');

    this.renderer.animate();

    // Demo all expressions
    this.demoExpressions();

    return this;
  }

  /**
   * Cycle through all available expressions
   */
  async demoExpressions() {
    const expressions = [
      'neutral',
      'smile',
      'laugh',
      'frown',
      'sad',
      'surprised',
      'thinking',
      'confused',
      'wink',
      'blink',
      'happy',
    ];

    console.log('Cycling through expressions:\n');

    for (const expr of expressions) {
      console.log(`  → ${expr}`);
      this.renderer.setExpression(expr);
      await this.sleep(2000);
    }

    console.log('\nDemo complete! Returning to neutral.');
    this.renderer.setExpression('neutral');
  }

  /**
   * Utility sleep
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Stop and cleanup
   */
  stop() {
    if (this.renderer) {
      this.renderer.stopAnimation();
      this.renderer.dispose();
    }
  }
}

// Main execution
if (import.meta.url === `file://${process.argv[1]}`) {
  console.log('=== Basic Face Demo ===\n');

  const demo = new BasicFaceDemo();
  demo.init().start();

  // Cleanup handler
  process.on('SIGINT', () => {
    console.log('\nExiting...');
    demo.stop();
    process.exit(0);
  });
}

export default BasicFaceDemo;
