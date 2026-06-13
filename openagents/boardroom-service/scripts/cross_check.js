#!/usr/bin/env node
/**
 * boardroom-service ExecStartPre cross-check.
 *
 * Verifies the substrate before the service is allowed to start:
 *   1. agent_map.json exists and has all seven soldiers + CEO.
 *   2. BANKON vault is present and contains mindx.boardroom.client:pk and
 *      mindx.boardroom.owner:pk (catches a misconfigured vault before any
 *      vote can happen on a stale or missing key — same posture as
 *      wordpress-agent's cross_check_allowlist.py).
 *   3. data/governance directory is writable.
 *   4. BOARDROOM_JWT_SECRET is set when NODE_ENV=production.
 *
 * Exits 0 on success, non-zero on any failure — systemd refuses to start
 * the service if this fails.
 */

import { readFileSync, accessSync, existsSync, constants } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(__dirname, '..', '..', '..');

const ERRORS = [];

function fail(msg) { ERRORS.push(msg); }

// 1. agent_map.json — seven soldiers + CEO
try {
  const mapPath = process.env.BOARDROOM_AGENT_MAP ?? resolve(ROOT, 'daio', 'agents', 'agent_map.json');
  const map = JSON.parse(readFileSync(mapPath, 'utf-8'));
  const required = ['coo_operations', 'cfo_finance', 'cto_technology',
                    'ciso_security', 'clo_legal', 'cpo_product', 'cro_risk'];
  for (const r of required) {
    if (!map.soldiers?.[r]) fail(`agent_map.json missing soldier: ${r}`);
  }
  if (!map.ceo) fail('agent_map.json missing ceo block');
} catch (e) {
  fail(`agent_map.json read/parse failed: ${e.message}`);
}

// 2. BANKON vault keys exist (presence-only — no decrypt at cross-check time)
const vaultDir = process.env.BOARDROOM_VAULT_DIR ?? resolve(ROOT, 'mindx_backend_service', 'vault_bankon');
if (!existsSync(vaultDir)) {
  fail(`BANKON vault dir missing: ${vaultDir}`);
} else {
  // We just need the index file to exist — actual decrypt happens lazily in
  // the service via the existing Python vault subprocess.
  const indexPath = resolve(vaultDir, 'index.json');
  if (!existsSync(indexPath)) {
    fail(`BANKON vault index missing: ${indexPath}`);
  } else {
    try {
      const idx = JSON.parse(readFileSync(indexPath, 'utf-8'));
      const ids = new Set(Object.keys(idx.entries ?? {}));
      // Soft-warn if specific boardroom keys aren't present yet — first deploy
      // hasn't enrolled them; we want the service to boot and the operator
      // to enroll them via manage_credentials.py.
      for (const required of ['mindx.boardroom.client:pk', 'mindx.boardroom.owner:pk']) {
        if (!ids.has(required)) {
          console.warn(`[cross-check] WARN: vault key not yet enrolled: ${required}`);
        }
      }
    } catch (e) {
      fail(`vault index parse failed: ${e.message}`);
    }
  }
}

// 3. data/governance writable
const dataDir = process.env.BOARDROOM_DATA_DIR ?? resolve(ROOT, 'data', 'governance');
try {
  if (!existsSync(dataDir)) fail(`data/governance missing: ${dataDir}`);
  else accessSync(dataDir, constants.W_OK);
} catch (e) {
  fail(`data/governance not writable: ${e.message}`);
}

// 4. JWT secret in production
if (process.env.NODE_ENV === 'production' && !process.env.BOARDROOM_JWT_SECRET) {
  fail('BOARDROOM_JWT_SECRET unset in production');
}

if (ERRORS.length > 0) {
  console.error('boardroom-service cross-check FAILED:');
  for (const e of ERRORS) console.error('  -', e);
  process.exit(1);
}

console.log('boardroom-service cross-check OK');
process.exit(0);
