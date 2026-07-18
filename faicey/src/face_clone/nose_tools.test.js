/**
 * nose_tools.test.js — the nose (network diagnostics) + its nostrils
 * (blockchain scan, RAGE search). Pure helpers, proven headless.
 * Run: node src/face_clone/nose_tools.test.js
 */
import { strict as assert } from 'assert';
import {
  classifyLatency, pingStats, connectionSummary,
  isAddress, isTxHash, rpcPayload, weiToEth, chainName, formatScan,
  buildSearchUrl, buildRestSearchUrl, rankResults,
} from './nose_tools.js';

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; console.log(`✅ ${name}`); } catch (e) { fail++; console.error(`❌ ${name}: ${e.message}`); } };

test('classifyLatency grades round-trip time', () => {
  assert.equal(classifyLatency(20), 'excellent');
  assert.equal(classifyLatency(90), 'good');
  assert.equal(classifyLatency(200), 'fair');
  assert.equal(classifyLatency(500), 'poor');
  assert.equal(classifyLatency(-1), 'unknown');
});

test('pingStats summarises samples with jitter + grade', () => {
  const s = pingStats([40, 42, 38, 44, 41]);
  assert.equal(s.n, 5); assert.equal(s.min, 38); assert.equal(s.max, 44);
  assert.ok(Math.abs(s.avg - 41) < 1e-9); assert.ok(s.jitter > 0); assert.equal(s.grade, 'excellent');
  assert.equal(pingStats([]).grade, 'unknown');
});

test('connectionSummary reads a navigator-like object', () => {
  const c = connectionSummary({ onLine: true, connection: { effectiveType: '4g', downlink: 10, rtt: 50 } });
  assert.equal(c.online, true); assert.equal(c.effectiveType, '4g'); assert.equal(c.downlinkMbps, 10); assert.equal(c.rttMs, 50);
  assert.equal(connectionSummary({ onLine: false }).online, false);
});

test('address + tx-hash validation', () => {
  assert.ok(isAddress('0x' + '1'.repeat(40)));
  assert.ok(!isAddress('0x123'));
  assert.ok(isTxHash('0x' + 'a'.repeat(64)));
  assert.ok(!isTxHash('0x' + 'a'.repeat(63)));
});

test('rpcPayload is a valid JSON-RPC 2.0 request', () => {
  const p = rpcPayload('eth_getBalance', ['0xabc', 'latest'], 7);
  assert.deepEqual(p, { jsonrpc: '2.0', id: 7, method: 'eth_getBalance', params: ['0xabc', 'latest'] });
});

test('weiToEth converts at conventional EVM 18-dp (1e18 wei = 1 ETH)', () => {
  assert.equal(weiToEth('0xde0b6b3a7640000'), '1.000000000000000000', '1e18 wei → 1 ETH');
  assert.equal(weiToEth(0n), '0.000000000000000000');
  assert.equal(weiToEth(1500000000000000000n), '1.500000000000000000', '1.5 ETH');
  assert.equal(weiToEth('nonsense'), '0.000000000000000000', 'bad input → zero, never throws');
  const [, frac] = weiToEth(1n).split('.'); assert.equal(frac.length, 18, 'always 18 decimals');
});

test('chainName maps ids and formatScan shapes a readout', () => {
  assert.equal(chainName('0x1'), 'Ethereum');
  assert.equal(chainName('0x2105'), 'Base');
  const scan = formatScan({ address: '0xabc', balanceWei: '0xde0b6b3a7640000', nonceHex: '0x5', chainIdHex: '0x89' });
  assert.equal(scan.eth, '1.000000000000000000'); assert.equal(scan.nonce, 5); assert.equal(scan.chain, 'Polygon');
});

test('RAGE search: URLs are well-formed and results rank by title match', () => {
  assert.equal(buildSearchUrl('https://rage.pythai.net/', 'mindx protocol'), 'https://rage.pythai.net/?s=mindx%20protocol');
  assert.ok(buildRestSearchUrl('https://rage.pythai.net', 'x402').includes('/wp-json/wp/v2/search?search=x402'));
  const ranked = rankResults([
    { title: 'The x402 payment rail' }, { title: 'mindX as a protocol' }, { title: 'x402 protocol deep dive' },
  ], 'x402 protocol');
  assert.equal(ranked[0].title, 'x402 protocol deep dive', 'both terms → top');
  assert.ok(ranked[0].score >= ranked[1].score && ranked[1].score >= ranked[2].score, 'sorted desc');
});

console.log(`\nnose_tools: ${pass} passed, ${fail} failed`);
if (fail) process.exit(1);
