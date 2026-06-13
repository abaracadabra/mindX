/**
 * DAIO admin + status routes.
 *
 *   GET  /daio/status                  — env flag, signer count, threshold
 *   GET  /daio/signers                 — public read of allowlisted signers
 *   POST /daio/signers                 — add (tier sovereign)
 *   DELETE /daio/signers/:wallet       — remove (tier sovereign)
 *   POST /daio/verify-sanction         — operator-facing verify probe; no side effect
 */

import { Hono } from 'hono';
import { isAddress } from 'viem';
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { requireTier, TIERS } from '../auth/middleware.js';
import { CONFIG } from '../config.js';
import { sanctioningEnabled, verifySanction } from './sanction.js';
import { log } from '../log.js';

export const daioRoutes = new Hono();
const SIGNERS_PATH = resolve(CONFIG.dataDir, 'daio_signers.jsonl');

function readSignersRaw(): Array<{ wallet: string; role: string; added_at: number }> {
  if (!existsSync(SIGNERS_PATH)) return [];
  const out: Array<{ wallet: string; role: string; added_at: number }> = [];
  for (const line of readFileSync(SIGNERS_PATH, 'utf-8').split('\n')) {
    const t = line.trim();
    if (!t) continue;
    try {
      const e = JSON.parse(t);
      if (e?.wallet) out.push({
        wallet: String(e.wallet).toLowerCase(),
        role: String(e.role ?? 'multisig'),
        added_at: Number(e.added_at ?? 0),
      });
    } catch { /* skip */ }
  }
  // Dedup by wallet (latest entry wins).
  const seen = new Map<string, typeof out[number]>();
  for (const e of out) seen.set(e.wallet, e);
  return Array.from(seen.values());
}

daioRoutes.get('/status', (c) => {
  const signers = readSignersRaw();
  const k = Number(process.env.MINDX_DAIO_SANCTION_K ?? '0') || Math.max(1, Math.ceil(signers.length / 2));
  return c.json({
    sanctioning_enabled: sanctioningEnabled(),
    signers_count: signers.length,
    threshold: k,
    signers_sample: signers.slice(0, 5).map(s => s.wallet),
  });
});

daioRoutes.get('/signers', (c) => {
  return c.json({ signers: readSignersRaw() });
});

daioRoutes.post('/signers', requireTier(TIERS.sovereign), async (c) => {
  const session = c.get('session');
  const body = await c.req.json().catch(() => ({}));
  const wallet = String(body.wallet ?? '').toLowerCase();
  if (!isAddress(wallet as `0x${string}`)) return c.json({ error: 'invalid_wallet' }, 400);
  const role = body.role === 'sovereign' ? 'sovereign' : 'multisig';
  appendFileSync(SIGNERS_PATH, JSON.stringify({
    wallet, role, added_at: Math.floor(Date.now() / 1000), added_by: session.address,
  }) + '\n', 'utf-8');
  log('info', 'daio', 'signer added', { wallet, role, by: session.address });
  return c.json({ wallet, role, added: true });
});

daioRoutes.delete('/signers/:wallet', requireTier(TIERS.sovereign), (c) => {
  const session = c.get('session');
  const target = String(c.req.param('wallet') ?? '').toLowerCase();
  if (!isAddress(target as `0x${string}`)) return c.json({ error: 'invalid_wallet' }, 400);
  // We don't truly delete from the JSONL (audit trail); we re-emit a tombstone
  // and rebuild the deduped view from the head. Quick deletion uses a fresh
  // dedup pass.
  const all = readSignersRaw().filter(s => s.wallet !== target);
  // Rewrite the file with kept entries (simple approach for an append-only ledger;
  // a future revision can keep tombstones inline).
  writeFileSync(SIGNERS_PATH, all.map(s => JSON.stringify(s)).join('\n') + (all.length ? '\n' : ''), 'utf-8');
  appendFileSync(SIGNERS_PATH + '.tombstones', JSON.stringify({
    ts: new Date().toISOString(), op: 'remove', wallet: target, by: session.address,
  }) + '\n', 'utf-8');
  log('info', 'daio', 'signer removed', { wallet: target, by: session.address });
  return c.json({ wallet: target, removed: true });
});

daioRoutes.post('/verify-sanction', async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const expectedAction = String(body.expected_action ?? body.action ?? '');
  if (!expectedAction) return c.json({ error: 'expected_action_required' }, 400);
  const sanction = body.sanction ?? null;
  const verdict = await verifySanction(sanction, expectedAction);
  return c.json(verdict);
});
