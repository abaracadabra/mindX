/**
 * Show all available personas
 */

import ASCIIFace from './ascii-face.js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function showAllPersonas() {
  console.log('\n╔═══════════════════════════════════════════════╗');
  console.log('║      mindX Faicey - All Available Personas   ║');
  console.log('╚═══════════════════════════════════════════════╝\n');

  const configPath = join(__dirname, '../config/personas.json');
  const configData = readFileSync(configPath, 'utf-8');
  const config = JSON.parse(configData);

  const personas = Object.keys(config.personas);

  personas.forEach((personaName, index) => {
    const face = new ASCIIFace(personaName);
    const persona = config.personas[personaName];

    console.log(`\n${index + 1}. ${persona.name}`);
    console.log('─'.repeat(45));
    console.log(`   ${persona.description}`);

    face.setExpression(persona.defaultExpression);
    face.renderWireframe();

    console.log(`   Default Expression: ${persona.defaultExpression}`);
    console.log(`   Wireframe Style: ${persona.wireframe.style || 'standard'}`);
    console.log(`   Color: ${persona.wireframe.color}`);

    if (persona.personality) {
      console.log(`   Traits: ${persona.personality.traits.join(', ')}`);
    }
  });

  console.log('\n═══════════════════════════════════════════════\n');
  console.log('Usage:');
  console.log('  import { createFaiceyAgent } from \'./faicey_agent.js\';');
  console.log('  const agent = await createFaiceyAgent(\'professor-codephreak\');');
  console.log('  agent.start();\n');
}

showAllPersonas();
