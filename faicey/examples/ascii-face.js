/**
 * ASCII Face Visualization
 * Text-based face rendering for terminal/Node.js
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class ASCIIFace {
  constructor(personaName = 'professor-codephreak') {
    this.personaName = personaName;
    this.currentExpression = 'neutral';
    this.morphValues = {
      smile: 0,
      frown: 0,
      mouth_open: 0,
      blink: 0,
      wink_left: 0,
      wink_right: 0,
      eyebrows_raised: 0,
      eyebrows_furrowed: 0,
    };
    this.loadConfig();
  }

  loadConfig() {
    try {
      const configPath = join(__dirname, '../config/personas.json');
      const configData = readFileSync(configPath, 'utf-8');
      const allConfigs = JSON.parse(configData);
      this.config = allConfigs.personas[this.personaName];
    } catch (error) {
      this.config = { name: this.personaName, defaultExpression: 'neutral' };
    }
  }

  setExpression(expression, intensity = 1.0) {
    this.currentExpression = expression;

    // Reset all morphs
    Object.keys(this.morphValues).forEach(key => {
      this.morphValues[key] = 0;
    });

    // Apply expression
    const expressions = {
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
      coding: { eyebrows_furrowed: 0.4, smile: 0.3 },
      happy: { smile: 1.0, eyebrows_raised: 0.3 },
    };

    const expr = expressions[expression] || {};
    Object.entries(expr).forEach(([morph, value]) => {
      this.morphValues[morph] = value * intensity;
    });
  }

  getEyeLeft() {
    if (this.morphValues.blink > 0.5 || this.morphValues.wink_left > 0.5) {
      return '-';
    }
    return 'O';
  }

  getEyeRight() {
    if (this.morphValues.blink > 0.5 || this.morphValues.wink_right > 0.5) {
      return '-';
    }
    return 'O';
  }

  getEyebrows() {
    if (this.morphValues.eyebrows_raised > 0.5) {
      return { left: '^', right: '^', offset: 1 };
    } else if (this.morphValues.eyebrows_furrowed > 0.5) {
      return { left: '\\', right: '/', offset: 0 };
    }
    return { left: '-', right: '-', offset: 0 };
  }

  getMouth() {
    const smile = this.morphValues.smile;
    const frown = this.morphValues.frown;
    const open = this.morphValues.mouth_open;

    if (open > 0.5) {
      return 'O';
    } else if (smile > 0.5) {
      return '‿';
    } else if (frown > 0.5) {
      return '⌓';
    }
    return '_';
  }

  render() {
    const eyebrows = this.getEyebrows();
    const leftEye = this.getEyeLeft();
    const rightEye = this.getEyeRight();
    const mouth = this.getMouth();

    console.log('\n');
    console.log('    ╭─────────────────╮');
    console.log('   ╱                   ╲');

    if (eyebrows.offset > 0) {
      console.log(`  │    ${eyebrows.left}       ${eyebrows.right}    │`);
      console.log(`  │     ${leftEye}     ${rightEye}     │`);
    } else {
      console.log(`  │    ${eyebrows.left}${leftEye}     ${rightEye}${eyebrows.right}    │`);
    }

    console.log('  │                   │');
    console.log(`  │         ${mouth}         │`);
    console.log('  │                   │');
    console.log('   ╲                 ╱');
    console.log('    ╰───────────────╯');
    console.log('\n');
  }

  renderWireframe() {
    const eyebrows = this.getEyebrows();
    const leftEye = this.getEyeLeft();
    const rightEye = this.getEyeRight();
    const mouth = this.getMouth();

    const color = this.config?.wireframe?.color || '0x00ff00';
    let colorCode = '\x1b[92m'; // Default green

    if (color.includes('00ff00')) colorCode = '\x1b[92m'; // Green
    else if (color.includes('00aaff')) colorCode = '\x1b[96m'; // Cyan
    else if (color.includes('ffaa00')) colorCode = '\x1b[93m'; // Yellow
    else if (color.includes('9900ff')) colorCode = '\x1b[95m'; // Magenta
    else if (color.includes('ff00ff')) colorCode = '\x1b[95m'; // Magenta

    console.log('\n');
    console.log(colorCode + '        ╱───────────╲');
    console.log(colorCode + '      ╱               ╲');

    if (eyebrows.offset > 0) {
      console.log(colorCode + `     │   ${eyebrows.left}       ${eyebrows.right}   │`);
      console.log(colorCode + `     │    ${leftEye}     ${rightEye}    │`);
    } else {
      console.log(colorCode + `     │   ${eyebrows.left}${leftEye}     ${rightEye}${eyebrows.right}   │`);
    }

    console.log(colorCode + '     │       ▼       │');
    console.log(colorCode + `     │       ${mouth}       │`);
    console.log(colorCode + '     │               │');
    console.log(colorCode + '      ╲             ╱');
    console.log(colorCode + '       ╲───────────╱');
    console.log('\x1b[0m\n'); // Reset color
  }

  displayInfo() {
    console.log(`┌─────────────────────────────────────────────┐`);
    console.log(`│  Persona: ${this.config.name.padEnd(32)}│`);
    console.log(`│  Expression: ${this.currentExpression.padEnd(28)}│`);
    console.log(`│  Wireframe: ${(this.config.wireframe?.enabled ? 'enabled' : 'disabled').padEnd(29)}│`);
    console.log(`│  Color: ${(this.config.wireframe?.color || 'default').padEnd(33)}│`);
    console.log(`└─────────────────────────────────────────────┘`);
  }
}

// Demo
async function demo() {
  console.clear();
  console.log('╔═══════════════════════════════════════════════╗');
  console.log('║   Professor Codephreak ASCII Face Renderer   ║');
  console.log('║   github.com/Professor-Codephreak            ║');
  console.log('║   mindX faicey - Terminal Edition            ║');
  console.log('╚═══════════════════════════════════════════════╝\n');

  const face = new ASCIIFace('professor-codephreak');

  // Show all expressions
  const expressions = [
    { name: 'neutral', duration: 1500 },
    { name: 'coding', duration: 2000 },
    { name: 'thinking', duration: 2000 },
    { name: 'confused', duration: 1500 },
    { name: 'surprised', duration: 1500 },
    { name: 'happy', duration: 1500 },
    { name: 'smile', duration: 1500 },
    { name: 'wink', duration: 1000 },
    { name: 'blink', duration: 500 },
    { name: 'coding', duration: 2000 },
  ];

  for (const { name, duration } of expressions) {
    console.clear();
    console.log('\x1b[1m' + name.toUpperCase() + '\x1b[0m');
    face.setExpression(name);
    face.renderWireframe();
    face.displayInfo();

    console.log(`Morph Values:`);
    Object.entries(face.morphValues).forEach(([key, value]) => {
      if (value > 0) {
        const bar = '█'.repeat(Math.floor(value * 20));
        console.log(`  ${key.padEnd(20)} ${bar} ${(value * 100).toFixed(0)}%`);
      }
    });

    await new Promise(resolve => setTimeout(resolve, duration));
  }

  console.log('\n✓ Demo complete!\n');
}

if (import.meta.url === `file://${process.argv[1]}`) {
  demo().catch(console.error);
}

export default ASCIIFace;
