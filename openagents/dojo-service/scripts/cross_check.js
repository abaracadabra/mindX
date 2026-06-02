#!/usr/bin/env node
/**
 * dojo-service ExecStartPre cross-check.
 * Verifies the dojo can write its ledger, the agent_map.json is readable,
 * and (when BONA FIDE is live) the indexer + ASA ID are set.
 */

import { readFileSync, accessSync, existsSync, constants } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(__dirname, '..', '..', '..');

const ERRORS = [];
const fail = (m) => ERRORS.push(m);

// agent_map.json readable
try {
  const mapPath = process.env.DOJO_AGENT_MAP ?? resolve(ROOT, 'daio', 'agents', 'agent_map.json');
  JSON.parse(readFileSync(mapPath, 'utf-8'));
} catch (e) {
  fail(`agent_map.json read/parse failed: ${e.message}`);
}

// data/governance writable
const dataDir = process.env.DOJO_DATA_DIR ?? resolve(ROOT, 'data', 'governance');
try {
  if (!existsSync(dataDir)) fail(`data/governance missing: ${dataDir}`);
  else accessSync(dataDir, constants.W_OK);
} catch (e) {
  fail(`data/governance not writable: ${e.message}`);
}

// JWT secret in prod
if (process.env.NODE_ENV === 'production' && !process.env.DOJO_JWT_SECRET) {
  fail('DOJO_JWT_SECRET unset in production');
}

// BONA FIDE: if live, must have indexer + ASA id
if (process.env.MINDX_BONA_FIDE_LIVE === '1') {
  if (!process.env.DOJO_BONA_FIDE_INDEXER) fail('MINDX_BONA_FIDE_LIVE=1 but DOJO_BONA_FIDE_INDEXER unset');
  if (!process.env.DOJO_BONA_FIDE_ASA_ID)  fail('MINDX_BONA_FIDE_LIVE=1 but DOJO_BONA_FIDE_ASA_ID unset');
}

if (ERRORS.length > 0) {
  console.error('dojo-service cross-check FAILED:');
  for (const e of ERRORS) console.error('  -', e);
  process.exit(1);
}
console.log('dojo-service cross-check OK');
process.exit(0);
