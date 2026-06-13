/**
 * Challenge issuance — EIP-191 personal_sign.
 *
 * Client flow:
 *   1. POST /auth/challenge { wallet, scope } -> { challenge_id, message, exp }
 *   2. Client signs message via window.ethereum.request({method:'personal_sign'})
 *   3. POST /auth/verify { challenge_id, signature } -> { session_token, tier, scope, exp }
 *
 * Replay protection: each challenge is consumed exactly once. Bounded
 * in-memory Map with TTL; restart wipes pending challenges (5-min window).
 */

import { randomBytes } from 'node:crypto';
import { CONFIG } from '../config.js';

export interface PendingChallenge {
  challenge_id: string;
  wallet: `0x${string}`;
  scope: string;
  nonce: string;
  message: string;
  issued_at: number;  // seconds
  exp: number;        // seconds
}

const CHALLENGES = new Map<string, PendingChallenge>();

function reap(): void {
  const now = Math.floor(Date.now() / 1000);
  for (const [id, c] of CHALLENGES) {
    if (c.exp < now) CHALLENGES.delete(id);
  }
  // Hard cap so a flood of /auth/challenge can't blow memory.
  if (CHALLENGES.size > 10_000) {
    const overflow = CHALLENGES.size - 10_000;
    const it = CHALLENGES.keys();
    for (let i = 0; i < overflow; i++) {
      const k = it.next().value;
      if (k === undefined) break;
      CHALLENGES.delete(k);
    }
  }
}

export function issueChallenge(wallet: `0x${string}`, scope: string): PendingChallenge {
  reap();
  const challenge_id = randomBytes(16).toString('hex');
  const nonce = randomBytes(16).toString('hex');
  const issued_at = Math.floor(Date.now() / 1000);
  const exp = issued_at + CONFIG.challengeTtlSeconds;
  const message =
    `dojo-service login\n` +
    `domain: ${CONFIG.domain}\n` +
    `wallet: ${wallet.toLowerCase()}\n` +
    `scope: ${scope}\n` +
    `nonce: ${nonce}\n` +
    `issued_at: ${issued_at}\n` +
    `exp: ${exp}\n`;
  const ch: PendingChallenge = { challenge_id, wallet: wallet.toLowerCase() as `0x${string}`, scope, nonce, message, issued_at, exp };
  CHALLENGES.set(challenge_id, ch);
  return ch;
}

export function consumeChallenge(challenge_id: string): PendingChallenge | null {
  reap();
  const ch = CHALLENGES.get(challenge_id);
  if (!ch) return null;
  // Single-use — delete on lookup.
  CHALLENGES.delete(challenge_id);
  const now = Math.floor(Date.now() / 1000);
  if (ch.exp < now) return null;
  return ch;
}
