#!/usr/bin/env node
/**
 * faicey smoke test — the minimum honest bar: every entry module parses and
 * imports under Node, and the core class constructs. Browser-side rendering
 * (three.js / MediaPipe) is exercised by the demo pages, not here.
 *
 * © Professor Codephreak - rage.pythai.net
 */
import { strict as assert } from 'assert';

let failures = 0;
const check = async (name, fn) => {
    try {
        await fn();
        console.log(`✅ ${name}`);
    } catch (err) {
        failures++;
        console.error(`❌ ${name}: ${err.message}`);
    }
};

await check('FaiceyCore imports with expected surface', async () => {
    // Constructing FaiceyCore auto-initializes browser audio (AudioContext /
    // getUserMedia), so under Node we assert the class shape, not an instance.
    const { FaiceyCore } = await import('../src/FaiceyCore.js');
    assert.equal(typeof FaiceyCore, 'function');
    for (const method of ['init', 'initAudioAnalysis']) {
        assert.equal(typeof FaiceyCore.prototype[method], 'function', `${method} on prototype`);
    }
});

await check('JaimlaAgent imports', async () => {
    const mod = await import('../src/agents/JaimlaAgent.js');
    assert.ok(Object.keys(mod).length > 0, 'module exports something');
});

await check('server.js parses (node --check contract)', async () => {
    const { execFileSync } = await import('child_process');
    const { fileURLToPath } = await import('url');
    const { dirname, resolve } = await import('path');
    const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    execFileSync(process.execPath, ['--check', resolve(root, 'server.js')]);
});

await check('package.json is coherent', async () => {
    const { readFileSync } = await import('fs');
    const { fileURLToPath } = await import('url');
    const { dirname, resolve } = await import('path');
    const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'));
    assert.equal(pkg.license, 'MIT');
    assert.ok(pkg.main, 'main entry declared');
});

if (failures) {
    console.error(`\n${failures} smoke check(s) failed`);
    process.exit(1);
}
console.log('\n🎭 faicey smoke: all checks passed');
