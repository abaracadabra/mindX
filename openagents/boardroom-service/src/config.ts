/**
 * Configuration & shared constants for boardroom-service.
 *
 * Reads daio/agents/agent_map.json (the canonical seven-soldier registry)
 * idempotently — Python mindX and this Node service read the same file
 * so the consensus layer stays in lockstep across the transport hop.
 *
 * Environment overrides:
 *   BOARDROOM_PORT          (default 8771)
 *   BOARDROOM_DATA_DIR      (default ../../data/governance)
 *   BOARDROOM_AGENT_MAP     (default ../../daio/agents/agent_map.json)
 *   BOARDROOM_JWT_SECRET    (required in production; falls back to a dev key)
 *   BOARDROOM_DOMAIN        (default boardroom.mindx.pythai.net — used in EIP-191)
 *   BOARDROOM_VAULT_DIR     (default ../../mindx_backend_service/vault_bankon)
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(__dirname, '..', '..', '..');

export const CONFIG = {
  port: Number(process.env.BOARDROOM_PORT ?? 8771),
  dataDir: process.env.BOARDROOM_DATA_DIR ?? resolve(ROOT, 'data', 'governance'),
  agentMapPath:
    process.env.BOARDROOM_AGENT_MAP ?? resolve(ROOT, 'daio', 'agents', 'agent_map.json'),
  jwtSecret:
    process.env.BOARDROOM_JWT_SECRET ??
    (() => {
      // Dev-only fallback — log loudly so this is never confused for prod.
      if (process.env.NODE_ENV === 'production') {
        throw new Error('BOARDROOM_JWT_SECRET must be set in production');
      }
      return 'dev-secret-do-not-use-in-production-' + Math.random().toString(36).slice(2);
    })(),
  domain: process.env.BOARDROOM_DOMAIN ?? 'boardroom.mindx.pythai.net',
  vaultDir:
    process.env.BOARDROOM_VAULT_DIR ?? resolve(ROOT, 'mindx_backend_service', 'vault_bankon'),
  // Tier-upgrade poll interval (clients re-issue JWT when personhood changes).
  authRefreshSeconds: 30,
  // Challenge TTL — EIP-191 message must be signed within this window.
  challengeTtlSeconds: 300,
  // JWT lifetime — must outlast a long convene session, but not by much.
  sessionTtlSeconds: 12 * 60 * 60,
} as const;

// ── Seven-soldier registry — load once at startup, refresh on SIGHUP.
// Same shape as Python boardroom.py's soldier_configs. We don't import; we
// re-read the JSON so Python and Node never drift through a stale in-memory
// copy on either side.

export interface SoldierConfig {
  inference_provider: string;
  weight: number;
  veto?: boolean;
  local_model?: string;
  cloud_model?: string;
  cloud_fallback?: string[];
  role: string;
  description?: string;
  eth_address?: string;
  algo_address?: string;
  capabilities?: string[];
}

export interface AgentMap {
  ceo: SoldierConfig;
  soldiers: Record<string, SoldierConfig>;
  warcouncil?: Record<string, SoldierConfig>;
}

let _agentMap: AgentMap | null = null;

export function loadAgentMap(force = false): AgentMap {
  if (_agentMap && !force) return _agentMap;
  const raw = readFileSync(CONFIG.agentMapPath, 'utf-8');
  const parsed = JSON.parse(raw) as AgentMap;
  // Sanity — refuse to boot without the seven soldiers.
  const required = ['coo_operations', 'cfo_finance', 'cto_technology',
                    'ciso_security', 'clo_legal', 'cpo_product', 'cro_risk'];
  for (const r of required) {
    if (!parsed.soldiers?.[r]) {
      throw new Error(`agent_map.json missing required soldier: ${r}`);
    }
  }
  _agentMap = parsed;
  return parsed;
}

process.on('SIGHUP', () => {
  console.log('[boardroom] SIGHUP — reloading agent_map.json');
  try { loadAgentMap(true); } catch (e) { console.error('[boardroom] reload failed:', e); }
});
