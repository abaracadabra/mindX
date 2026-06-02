/**
 * Hono middleware — Bearer token → TieredSession on c.var.session.
 *
 * Usage in routes:
 *   import { requireSession, requireTier } from './auth/middleware.js';
 *   app.get('/rooms', requireSession(), async (c) => { ... });
 *   app.post('/rooms', requireTier(TIERS.person), async (c) => { ... });
 */

import type { MiddlewareHandler } from 'hono';
import type { Tier, TieredSession } from './tiers.js';
import { TIERS } from './tiers.js';
import { verifySession } from './session.js';

declare module 'hono' {
  interface ContextVariableMap {
    session: TieredSession;
  }
}

export const requireSession = (): MiddlewareHandler => async (c, next) => {
  const auth = c.req.header('Authorization');
  if (!auth?.startsWith('Bearer ')) {
    return c.json({ error: 'missing_bearer' }, 401);
  }
  const session = await verifySession(auth.slice(7));
  if (!session) {
    return c.json({ error: 'invalid_session' }, 401);
  }
  if (session.exp < Math.floor(Date.now() / 1000)) {
    return c.json({ error: 'session_expired' }, 401);
  }
  c.set('session', session);
  await next();
};

export const requireTier = (required: Tier): MiddlewareHandler => async (c, next) => {
  const auth = c.req.header('Authorization');
  if (!auth?.startsWith('Bearer ')) {
    return c.json({ error: 'missing_bearer', required_tier: required }, 401);
  }
  const session = await verifySession(auth.slice(7));
  if (!session) {
    return c.json({ error: 'invalid_session', required_tier: required }, 401);
  }
  if (session.exp < Math.floor(Date.now() / 1000)) {
    return c.json({ error: 'session_expired', required_tier: required }, 401);
  }
  if (session.tier < required) {
    return c.json({ error: 'insufficient_tier', have: session.tier, required }, 403);
  }
  c.set('session', session);
  await next();
};

export { TIERS };
