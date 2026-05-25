/**
 * dojo-service entry point.
 *
 * Reputation deltas, K-of-N personhood vouching (pre-mint), BONA FIDE
 * Algorand ASA balance read (post-mint). NO aisdk — pure ledger logic.
 *
 * Listens on port 8772 by default; Apache fronts it at /dojo-svc/* on
 * mindx.pythai.net.
 */

import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { CONFIG, rankFor } from './config.js';
import { log } from './log.js';

const app = new Hono();

app.get('/healthz', (c) => c.json({
  status: 'ok',
  service: 'dojo-service',
  version: '0.1.0',
  ts: Date.now(),
}));

app.get('/version', (c) => c.json({
  service: 'dojo-service',
  version: '0.1.0',
  domain: CONFIG.domain,
  bona_fide_live: CONFIG.bonaFideLive,
  bona_fide_asa_id: CONFIG.bonaFideAsaId,
  vouching_k: CONFIG.vouchingK,
  rank_thresholds: CONFIG.ranks,
  oracle: CONFIG.bonaFideLive ? 'BonaFideOracle (Algorand)' : 'VouchingOracle (K-of-N JSONL)',
}));

// Sanity smoke: rank computation exposed via /version helper.
app.get('/rank/:score', (c) => {
  const score = Number(c.req.param('score'));
  if (!Number.isFinite(score)) return c.json({ error: 'score must be a number' }, 400);
  return c.json({ score, rank: rankFor(score) });
});

// Subsequent phases will wire:
// app.route('/auth',         authRoutes);
// app.route('/agents',       reputationRoutes);
// app.route('/personhood',   personhoodRoutes);
// app.route('/standings',    standingsRoutes);

serve({
  fetch: app.fetch,
  port: CONFIG.port,
}, (info) => {
  log('info', 'boot', `dojo-service listening on ${info.address}:${info.port}`, {
    port: info.port,
    domain: CONFIG.domain,
    bona_fide_live: CONFIG.bonaFideLive,
    oracle: CONFIG.bonaFideLive ? 'BonaFideOracle' : 'VouchingOracle',
  });
});

const shutdown = (sig: string) => {
  log('info', 'shutdown', `received ${sig}`);
  process.exit(0);
};
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
