/**
 * Personhood routes.
 *
 *   POST /personhood/declare                  (any tier; wallet self-declares)
 *   POST /personhood/vouch/:target            (tier ≥ person; vouch for another)
 *   GET  /personhood/:address                 (public read)
 *   POST /personhood/grant                    (tier ≥ sovereign; override grant)
 */

import { Hono } from 'hono';
import { isAddress } from 'viem';
import { requireSession, requireTier, TIERS } from '../auth/middleware.js';
import { oracle } from './oracle.js';

export const personhoodRoutes = new Hono();

personhoodRoutes.post('/declare', requireSession(), async (c) => {
  const session = c.get('session');
  const out = await oracle().declare(session.address);
  return c.json({ address: session.address, ...out });
});

personhoodRoutes.post('/vouch/:target', requireTier(TIERS.person), async (c) => {
  const session = c.get('session');
  const target = String(c.req.param('target') ?? '').toLowerCase();
  if (!isAddress(target as `0x${string}`)) return c.json({ error: 'invalid_target' }, 400);
  const out = await oracle().vouch(session.address, target);
  return c.json({ target, voucher: session.address, ...out });
});

personhoodRoutes.get('/:address', async (c) => {
  const addr = String(c.req.param('address') ?? '').toLowerCase();
  if (!isAddress(addr as `0x${string}`)) return c.json({ error: 'invalid_address' }, 400);
  const status = await oracle().status(addr);
  const tier_score = await oracle().tier_score(addr);
  return c.json({ address: addr, status, tier_score });
});

personhoodRoutes.post('/grant', requireTier(TIERS.sovereign), async (c) => {
  const session = c.get('session');
  const body = await c.req.json().catch(() => ({}));
  const target = String(body.target ?? '').toLowerCase();
  if (!isAddress(target as `0x${string}`)) return c.json({ error: 'invalid_target' }, 400);
  const out = await oracle().grant(target, session.address);
  return c.json({ target, grantor: session.address, ...out });
});
