/**
 * DAIO sanction layer — cross-room joint-action gate.
 *
 * When `MINDX_DAIO_SANCTIONING_ENABLED=1`, certain actions cannot land
 * without a DAIO multisig signature:
 *
 *   - Convening in a room whose `daio_sanctioned` flag must be set
 *   - Promoting a DAIO observer seat to voting (war-council side)
 *   - Cross-service joint convene (boardroom ↔ warcouncil ↔ dojo)
 *   - Sovereign personhood grants on the dojo
 *
 * A DAIO sanction is an EIP-191 signature from any wallet listed in
 * `daio_signers.jsonl` (the on-chain multisig recovered into the local
 * cache). Multisig threshold is K-of-N where K defaults to ceil(N/2).
 *
 * Sanctions are bundled into a token shape:
 *
 *   sanction = {
 *     action: 'convene_cross_room' | 'promote_daio_voting' | 'grant_personhood' | ...,
 *     target: { room_id?, address? },
 *     issued_at: <unix>,
 *     exp: <unix>,
 *     signatures: [{ signer, sig }, ...],
 *   }
 *
 * The verifier reads daio_signers.jsonl, recovers each sig, requires K
 * unique signers from the allowlist. Sanctions are recorded to
 * daio_sanctions.jsonl on first successful verify so the audit trail is
 * complete.
 *
 * Off-by-default: when `MINDX_DAIO_SANCTIONING_ENABLED=0`, every check
 * passes through. This is the toggle the operator flips after DAIO is
 * on mainnet.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { verifyMessage } from 'viem';
import { CONFIG } from '../config.js';
import { appendJsonl, log } from '../log.js';

const SIGNERS_PATH    = resolve(CONFIG.dataDir, 'daio_signers.jsonl');
const SANCTIONS_PATH  = resolve(CONFIG.dataDir, 'daio_sanctions.jsonl');
const REJECTED_PATH   = resolve(CONFIG.dataDir, 'daio_sanctions_rejected.jsonl');
const NONCE_TTL_S     = 3600;

interface SignerEntry {
  wallet: string;       // lowercase 0x address
  role: 'multisig' | 'sovereign';
  added_at: number;
  added_by?: string;
}

export interface Sanction {
  action: string;
  target: Record<string, unknown>;
  issued_at: number;
  exp: number;
  nonce: string;
  signatures: Array<{ signer: string; sig: `0x${string}` }>;
}

function readSigners(): SignerEntry[] {
  if (!existsSync(SIGNERS_PATH)) return [];
  const out: SignerEntry[] = [];
  for (const line of readFileSync(SIGNERS_PATH, 'utf-8').split('\n')) {
    const t = line.trim();
    if (!t) continue;
    try {
      const e = JSON.parse(t);
      if (e?.wallet) out.push({ ...e, wallet: String(e.wallet).toLowerCase() });
    } catch { /* skip */ }
  }
  return out;
}

function threshold(signerCount: number): number {
  const k = Number(process.env.MINDX_DAIO_SANCTION_K ?? '0');
  if (k > 0) return k;
  return Math.max(1, Math.ceil(signerCount / 2));
}

function canonicalPreimage(s: Sanction): string {
  return (
    `daio-sanction v1\n` +
    `action: ${s.action}\n` +
    `target: ${JSON.stringify(s.target)}\n` +
    `issued_at: ${s.issued_at}\n` +
    `exp: ${s.exp}\n` +
    `nonce: ${s.nonce}\n`
  );
}

const seenNonces = new Map<string, number>();
function reapNonces(): void {
  const now = Math.floor(Date.now() / 1000);
  for (const [n, t] of seenNonces) {
    if (now - t > NONCE_TTL_S * 2) seenNonces.delete(n);
  }
  if (seenNonces.size > 10_000) {
    const it = seenNonces.keys();
    for (let i = 0; i < 1000; i++) { const k = it.next().value; if (k === undefined) break; seenNonces.delete(k); }
  }
}

export interface SanctionVerdict {
  ok: boolean;
  reason: string;
  /** Number of unique valid signers found. */
  signers_valid: number;
  /** Required signer threshold. */
  threshold: number;
}

/** Quick gate — returns true to short-circuit checks when sanctioning is off. */
export function sanctioningEnabled(): boolean {
  return process.env.MINDX_DAIO_SANCTIONING_ENABLED === '1';
}

export async function verifySanction(s: Sanction | null | undefined, expectedAction: string): Promise<SanctionVerdict> {
  // If the flag is off, anything passes — the operator opts in.
  if (!sanctioningEnabled()) {
    return { ok: true, reason: 'sanctioning_disabled', signers_valid: 0, threshold: 0 };
  }
  if (!s || typeof s !== 'object') {
    return audit({ ok: false, reason: 'sanction_missing', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  if (s.action !== expectedAction) {
    return audit({ ok: false, reason: 'action_mismatch', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  const now = Math.floor(Date.now() / 1000);
  if (typeof s.exp !== 'number' || s.exp < now) {
    return audit({ ok: false, reason: 'sanction_expired', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  if (typeof s.issued_at !== 'number' || s.issued_at > now + 300) {
    return audit({ ok: false, reason: 'sanction_future_dated', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  if (!s.nonce || typeof s.nonce !== 'string') {
    return audit({ ok: false, reason: 'missing_nonce', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  reapNonces();
  if (seenNonces.has(s.nonce)) {
    return audit({ ok: false, reason: 'nonce_replay', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  const signers = readSigners();
  const allowed = new Set(signers.map(x => x.wallet));
  if (allowed.size === 0) {
    return audit({ ok: false, reason: 'no_signers_configured', signers_valid: 0, threshold: 0 }, s, expectedAction);
  }
  const thr = threshold(allowed.size);
  const message = canonicalPreimage(s);
  const validSigners = new Set<string>();
  for (const entry of s.signatures ?? []) {
    const addr = String(entry?.signer ?? '').toLowerCase();
    if (!allowed.has(addr)) continue;
    if (validSigners.has(addr)) continue;
    try {
      const ok = await verifyMessage({ address: addr as `0x${string}`, message, signature: entry.sig });
      if (ok) validSigners.add(addr);
    } catch { /* skip bad sig */ }
  }
  if (validSigners.size < thr) {
    return audit({ ok: false, reason: 'insufficient_signatures', signers_valid: validSigners.size, threshold: thr }, s, expectedAction);
  }
  // Commit nonce, persist audit row.
  seenNonces.set(s.nonce, now);
  appendJsonl(SANCTIONS_PATH, {
    ts: new Date().toISOString(),
    action: s.action, target: s.target,
    issued_at: s.issued_at, exp: s.exp, nonce: s.nonce,
    signers_valid: Array.from(validSigners), threshold: thr,
  });
  log('info', 'daio', 'sanction verified', {
    action: s.action, signers_valid: validSigners.size, threshold: thr,
  });
  return { ok: true, reason: 'verified', signers_valid: validSigners.size, threshold: thr };
}

function audit(v: SanctionVerdict, s: Sanction | null | undefined, expectedAction: string): SanctionVerdict {
  appendJsonl(REJECTED_PATH, {
    ts: new Date().toISOString(),
    reason: v.reason,
    expected_action: expectedAction,
    presented_action: s?.action,
    signers_valid: v.signers_valid,
    threshold: v.threshold,
  });
  return v;
}
