/**
 * Session / JWT issuance + verification.
 *
 * Tokens are HS256 JWTs signed with CONFIG.jwtSecret. Payload shape mirrors
 * the TieredSession interface from tiers.ts. JWT carries tier+scope so every
 * request can be gated without a per-request DB hit.
 *
 * For tier upgrades mid-session (a vouch lands, BONA FIDE balance shifts),
 * clients call /auth/refresh — the server re-resolves the tier and issues
 * a new token. WebSocket clients can request the same via a `auth.refresh`
 * control frame (Phase D wires that into the WS handler).
 */

import { sign, verify } from 'hono/jwt';
import { CONFIG } from '../config.js';
import type { Tier, TieredSession } from './tiers.js';

export async function issueSession(
  address: `0x${string}`,
  tier: Tier,
  scope: string,
  personhood: 'none' | 'pending' | 'granted' = 'none',
): Promise<{ token: string; payload: TieredSession }> {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + CONFIG.sessionTtlSeconds;
  const payload: TieredSession = {
    address: address.toLowerCase() as `0x${string}`,
    tier,
    scope,
    personhood,
    iat,
    exp,
  };
  // hono/jwt's JWTPayload is a loose Record<string, unknown>; the unknown
  // cast bridges our narrower TieredSession shape into it.
  const token = await sign(payload as unknown as Record<string, unknown>, CONFIG.jwtSecret, 'HS256');
  return { token, payload };
}

export async function verifySession(token: string): Promise<TieredSession | null> {
  try {
    const decoded = await verify(token, CONFIG.jwtSecret, 'HS256');
    return decoded as unknown as TieredSession;
  } catch {
    return null;
  }
}
