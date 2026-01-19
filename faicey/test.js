/**
 * Simple test to verify faicey installation and basic functionality
 */

console.log('Testing Faicey System...\n');

async function runTests() {
  let testsPassed = 0;
  let testsFailed = 0;

  // Test 1: Import core modules
  try {
    console.log('Test 1: Importing core modules...');
    const FaceRenderer = (await import('./core/FaceRenderer.js')).default;
    const FaceGeometry = (await import('./core/FaceGeometry.js')).default;
    const ExpressionController = (await import('./core/ExpressionController.js')).default;
    const WireframeController = (await import('./core/WireframeController.js')).default;
    console.log('✓ Core modules imported successfully\n');
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to import core modules:', error.message, '\n');
    testsFailed++;
  }

  // Test 2: Create FaceGeometry
  try {
    console.log('Test 2: Creating face geometry...');
    const { default: FaceGeometry } = await import('./core/FaceGeometry.js');
    const faceGeometry = new FaceGeometry();
    const geometry = faceGeometry.createFaceGeometry();
    const morphs = faceGeometry.getMorphTargets();
    console.log(`✓ Created geometry with ${morphs.length} morph targets:`);
    console.log(`  ${morphs.join(', ')}\n`);
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to create geometry:', error.message, '\n');
    testsFailed++;
  }

  // Test 3: Initialize FaceRenderer
  try {
    console.log('Test 3: Initializing FaceRenderer...');
    const { default: FaceRenderer } = await import('./core/FaceRenderer.js');
    const renderer = new FaceRenderer({
      wireframe: true,
      expressions: true
    });
    renderer.init();
    console.log('✓ FaceRenderer initialized successfully\n');
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to initialize renderer:', error.message, '\n');
    testsFailed++;
  }

  // Test 4: Load persona config
  try {
    console.log('Test 4: Loading persona configuration...');
    const { readFileSync } = await import('fs');
    const configData = readFileSync('./config/personas.json', 'utf-8');
    const config = JSON.parse(configData);
    const personaCount = Object.keys(config.personas).length;
    console.log(`✓ Loaded ${personaCount} personas:`);
    Object.keys(config.personas).forEach(name => {
      console.log(`  - ${name}`);
    });
    console.log();
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to load persona config:', error.message, '\n');
    testsFailed++;
  }

  // Test 5: Create FaiceyAgent
  try {
    console.log('Test 5: Creating FaiceyAgent...');
    const { FaiceyAgent } = await import('./faicey_agent.js');
    const agent = new FaiceyAgent('professor-codephreak');
    await agent.init();
    console.log('✓ FaiceyAgent created and initialized\n');
    agent.stop();
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to create agent:', error.message, '\n');
    testsFailed++;
  }

  // Test 6: Test MorphTarget utilities
  try {
    console.log('Test 6: Testing MorphTarget utilities...');
    const { textToPhonemes, phonemesToMorphs } = await import('./lib/MorphTargets.js');
    const text = 'Hello World';
    const phonemes = textToPhonemes(text);
    const morphs = phonemesToMorphs(phonemes);
    console.log(`✓ Converted "${text}" to ${phonemes.length} phonemes\n`);
    testsPassed++;
  } catch (error) {
    console.error('✗ Failed to test morph utilities:', error.message, '\n');
    testsFailed++;
  }

  // Summary
  console.log('═══════════════════════════════════════');
  console.log('Test Summary:');
  console.log(`  Passed: ${testsPassed}`);
  console.log(`  Failed: ${testsFailed}`);
  console.log(`  Total:  ${testsPassed + testsFailed}`);
  console.log('═══════════════════════════════════════\n');

  if (testsFailed === 0) {
    console.log('🎉 All tests passed! Faicey is ready to use.\n');
    console.log('Next steps:');
    console.log('  npm run example:professor  - Run Professor Codephreak demo');
    console.log('  npm run example:basic      - Run basic face demo');
    console.log('  See USAGE.md for more examples\n');
  } else {
    console.log('⚠️  Some tests failed. Please check the errors above.\n');
    process.exit(1);
  }
}

runTests().catch(error => {
  console.error('Fatal error running tests:', error);
  process.exit(1);
});
