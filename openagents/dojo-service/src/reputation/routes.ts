/**
 * Reputation routes.
 *
 *   GET  /agents/:address/reputation
 *   POST /agents/:address/reputation   (tier ≥ cabinet)
 *   GET  /standings
 *   GET  /privileges/:address          (rank-derived flags)
 */

import { Hono } from 'hono';
import { isAddress } from 'viem';
import { requireSession, requireTier, TIERS } from '../auth/middleware.js';
import { getReputation, applyDelta, getStandings, getRankPrivileges } from './ledger.js';

export const reputationRoutes = new Hono();

reputationRoutes.get('/agents/:address/reputation', (c) => {
  const addr = String(c.req.param('address') ?? '').toLowerCase();
  if (!isAddress(addr as `0x${string}`)) return c.json({ error: 'invalid_address' }, 400);
  const rep = getReputation(addr);
  const priv = getRankPrivileges(rep.rank);
  return c.json({ ...rep, privileges: priv });
});

reputationRoutes.post('/agents/:address/reputation', requireTier(TIERS.cabinet), async (c) => {
  const session = c.get('session');
  const addr = String(c.req.param('address') ?? '').toLowerCase();
  if (!isAddress(addr as `0x${string}`)) return c.json({ error: 'invalid_address' }, 400);
  const body = await c.req.json().catch(() => ({}));
  const delta = Number(body.delta ?? 0);
  if (!Number.isFinite(delta) || delta === 0) return c.json({ error: 'delta_required' }, 400);
  const event_type = String(body.event_type ?? 'manual').slice(0, 60);
  const reason = body.reason ? String(body.reason) : undefined;
  const out = applyDelta(addr, delta, event_type, reason, session.address);
  return c.json({ agent_id: addr, ...out });
});

reputationRoutes.get('/standings', (c) => {
  const limit = Math.max(1, Math.min(500, Number(c.req.query('limit') ?? 50)));
  const standings = getStandings(limit);
  return c.json({ standings, count: standings.length });
});

reputationRoutes.get('/privileges/:address', (c) => {
  const addr = String(c.req.param('address') ?? '').toLowerCase();
  if (!isAddress(addr as `0x${string}`)) return c.json({ error: 'invalid_address' }, 400);
  const rep = getReputation(addr);
  const priv = getRankPrivileges(rep.rank);
  return c.json({ address: addr, rank: rep.rank, score: rep.score, privileges: priv });
});
