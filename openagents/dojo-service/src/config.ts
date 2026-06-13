/**
 * Configuration for dojo-service.
 *
 * Reputation ledger + personhood oracle. Reads the same agent_map.json that
 * the boardroom does for default reputation seeds; writes its own
 * dojo_events.jsonl and personhood.jsonl files.
 *
 * Environment overrides:
 *   DOJO_PORT                (default 8772)
 *   DOJO_DATA_DIR            (default ../../data/governance)
 *   DOJO_AGENT_MAP           (default ../../daio/agents/agent_map.json)
 *   DOJO_JWT_SECRET          (required in production)
 *   DOJO_DOMAIN              (default dojo.mindx.pythai.net)
 *   MINDX_BONA_FIDE_LIVE     ("1" to flip from VouchingOracle to BonaFideOracle)
 *   DOJO_BONA_FIDE_INDEXER   (Algorand indexer URL, used when LIVE)
 *   DOJO_BONA_FIDE_ASA_ID    (the BONA FIDE asset ID on Algorand)
 *   DOJO_VOUCHING_K          (default 3 — K-of-N personhood vouches)
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const ROOT = resolve(__dirname, '..', '..', '..');

export const CONFIG = {
  port: Number(process.env.DOJO_PORT ?? 8772),
  dataDir: process.env.DOJO_DATA_DIR ?? resolve(ROOT, 'data', 'governance'),
  agentMapPath: process.env.DOJO_AGENT_MAP ?? resolve(ROOT, 'daio', 'agents', 'agent_map.json'),
  jwtSecret:
    process.env.DOJO_JWT_SECRET ??
    (() => {
      if (process.env.NODE_ENV === 'production') {
        throw new Error('DOJO_JWT_SECRET must be set in production');
      }
      return 'dev-dojo-secret-' + Math.random().toString(36).slice(2);
    })(),
  domain: process.env.DOJO_DOMAIN ?? 'dojo.mindx.pythai.net',
  bonaFideLive: process.env.MINDX_BONA_FIDE_LIVE === '1',
  bonaFideIndexer: process.env.DOJO_BONA_FIDE_INDEXER ?? 'https://mainnet-idx.algonode.cloud',
  bonaFideAsaId: process.env.DOJO_BONA_FIDE_ASA_ID ? Number(process.env.DOJO_BONA_FIDE_ASA_ID) : null,
  vouchingK: Number(process.env.DOJO_VOUCHING_K ?? 3),
  challengeTtlSeconds: 300,
  sessionTtlSeconds: 12 * 60 * 60,
  // Reputation rank thresholds — match daio/governance/dojo.py exactly so
  // the existing dojo_events.jsonl ledger is interpretable across the cutover.
  ranks: {
    novice: 0,
    apprentice: 101,
    journeyman: 501,
    expert: 1501,
    master: 5001,
    grandmaster: 15001,
    sovereign: 50001,
  } as const,
} as const;

export function rankFor(score: number): keyof typeof CONFIG.ranks {
  const entries = Object.entries(CONFIG.ranks) as [keyof typeof CONFIG.ranks, number][];
  let current: keyof typeof CONFIG.ranks = 'novice';
  for (const [name, threshold] of entries) {
    if (score >= threshold) current = name;
  }
  return current;
}
