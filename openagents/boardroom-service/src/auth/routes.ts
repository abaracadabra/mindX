/**
 * Auth routes — challenge, verify, session, refresh.
 *
 * Mounted at /auth/* by server.ts.
 */

import { Hono } from 'hono';
import { isAddress, verifyMessage } from 'viem';
import { issueChallenge, consumeChallenge } from './challenge.js';
import { issueSession } from './session.js';
import { resolveTier } from './resolver.js';
import { requireSession } from './middleware.js';
import { tierName } from './tiers.js';
import { log } from '../log.js';

export const authRoutes = new Hono();

authRoutes.post('/challenge', async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const wallet = String(body.wallet ?? '').trim().toLowerCase();
  const scope = String(body.scope ?? 'boardroom-service').trim() || 'boardroom-service';

  if (!isAddress(wallet as `0x${string}`)) {
    return c.json({ error: 'invalid_wallet_address' }, 400);
  }

  const ch = issueChallenge(wallet as `0x${string}`, scope);
  log('info', 'auth', 'challenge issued', { wallet, scope, challenge_id: ch.challenge_id });
  return c.json({
    challenge_id: ch.challenge_id,
    message: ch.message,
    exp: ch.exp,
  });
});

authRoutes.post('/verify', async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const challenge_id = String(body.challenge_id ?? '');
  const signature = String(body.signature ?? '') as `0x${string}`;

  if (!challenge_id || !signature) {
    return c.json({ error: 'missing_challenge_or_signature' }, 400);
  }

  const ch = consumeChallenge(challenge_id);
  if (!ch) {
    return c.json({ error: 'challenge_not_found_or_expired' }, 401);
  }

  let valid = false;
  try {
    valid = await verifyMessage({
      address: ch.wallet,
      message: ch.message,
      signature,
    });
  } catch (e) {
    log('warn', 'auth', 'verifyMessage threw', { wallet: ch.wallet, err: String(e) });
  }
  if (!valid) {
    return c.json({ error: 'signature_invalid' }, 401);
  }

  // Resolve the tier for this wallet at this scope.
  // (Room lookup + personhood query land in Phase C/F — for now we resolve
  // against shadow_overlord.jsonl + observer default.)
  const { tier, reason } = resolveTier(ch.wallet, { scope: ch.scope });
  const { token, payload } = await issueSession(ch.wallet, tier, ch.scope);

  log('info', 'auth', 'session issued', {
    wallet: ch.wallet, scope: ch.scope, tier, tier_name: tierName(tier), reason,
  });

  return c.json({
    session_token: token,
    address: payload.address,
    tier,
    tier_name: tierName(tier),
    scope: payload.scope,
    exp: payload.exp,
    resolved_via: reason,
  });
});

authRoutes.get('/session', requireSession(), (c) => {
  const session = c.get('session');
  return c.json({
    address: session.address,
    tier: session.tier,
    tier_name: tierName(session.tier),
    scope: session.scope,
    exp: session.exp,
  });
});

// Tier-refresh — re-resolves the tier without forcing a full challenge cycle.
// Useful when personhood lands or a sovereign promotes the wallet to cabinet
// in shadow_overlord.jsonl during an active session.
authRoutes.post('/refresh', requireSession(), async (c) => {
  const session = c.get('session');
  const { tier: newTier, reason } = resolveTier(session.address, { scope: session.scope });
  const { token, payload } = await issueSession(session.address, newTier, session.scope, session.personhood);
  return c.json({
    session_token: token,
    address: payload.address,
    tier: newTier,
    tier_name: tierName(newTier),
    scope: payload.scope,
    exp: payload.exp,
    resolved_via: reason,
    previous_tier: session.tier,
  });
});
