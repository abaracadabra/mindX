/**
 * PersonhoodOracle — abstract interface with two implementations.
 *
 *   VouchingOracle   — pre-BONA-FIDE-mint. Reads personhood.jsonl ledger;
 *                       grants personhood when an address has K signed
 *                       vouches from existing persons.
 *   BonaFideOracle   — post-mint. Reads Algorand indexer for the ASA
 *                       balance and derives personhood from threshold.
 *
 * Switch via env: `MINDX_BONA_FIDE_LIVE=1` flips to BonaFideOracle.
 * Both can co-run during migration audits — the operator can construct a
 * temporary "audit oracle" that delegates to both and warns on divergence
 * (Phase F2 follow-up; not in scope here).
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { CONFIG } from '../config.js';
import { appendJsonl, log } from '../log.js';

export type PersonhoodStatus = 'none' | 'pending' | 'granted';

export interface PersonhoodOracle {
  /** Current personhood status for `address`. */
  status(address: string): Promise<PersonhoodStatus>;
  /** Tier score (for future use in dojo ranks). Pre-BONA-FIDE returns 0 or 1. */
  tier_score(address: string): Promise<number>;
  /** Add a self-declaration (creates pending). */
  declare(address: string): Promise<{ status: PersonhoodStatus; vouches_needed: number; vouches_have: number }>;
  /** Add a vouch from a person for `target`. Returns updated state. */
  vouch(voucher: string, target: string): Promise<{ status: PersonhoodStatus; vouches_have: number; vouches_needed: number }>;
  /** Sovereign grant — overrides vouch flow. */
  grant(target: string, grantor: string): Promise<{ status: PersonhoodStatus }>;
}

// ── VouchingOracle (active pre-BONA-FIDE) ─────────────────────────────

interface VouchEntry {
  ts: string;          // ISO
  op: 'declare' | 'vouch' | 'grant';
  target: string;      // lowercase 0x address
  by?: string;         // voucher / grantor address
}

class VouchingOracleImpl implements PersonhoodOracle {
  private path = resolve(CONFIG.dataDir, 'personhood.jsonl');

  private readAll(): VouchEntry[] {
    if (!existsSync(this.path)) return [];
    const out: VouchEntry[] = [];
    for (const line of readFileSync(this.path, 'utf-8').split('\n')) {
      const t = line.trim();
      if (!t) continue;
      try { out.push(JSON.parse(t)); } catch { /* skip */ }
    }
    return out;
  }

  private computeState(address: string): { status: PersonhoodStatus; vouches: Set<string>; declared: boolean; granted: boolean } {
    const addr = address.toLowerCase();
    const all = this.readAll();
    let declared = false;
    let granted = false;
    const vouches = new Set<string>();
    for (const e of all) {
      if (e.target?.toLowerCase() !== addr) continue;
      if (e.op === 'declare') declared = true;
      else if (e.op === 'grant') granted = true;
      else if (e.op === 'vouch' && e.by) vouches.add(e.by.toLowerCase());
    }
    let status: PersonhoodStatus = 'none';
    if (granted) status = 'granted';
    else if (vouches.size >= CONFIG.vouchingK) status = 'granted';
    else if (declared) status = 'pending';
    return { status, vouches, declared, granted };
  }

  async status(address: string): Promise<PersonhoodStatus> {
    return this.computeState(address).status;
  }

  async tier_score(address: string): Promise<number> {
    return (await this.status(address)) === 'granted' ? 1 : 0;
  }

  async declare(address: string) {
    const cur = this.computeState(address);
    if (cur.status === 'granted') {
      return { status: 'granted' as const, vouches_needed: 0, vouches_have: cur.vouches.size };
    }
    if (!cur.declared) {
      appendJsonl(this.path, { ts: new Date().toISOString(), op: 'declare', target: address.toLowerCase() });
      log('info', 'personhood', 'self-declared', { address });
    }
    const updated = this.computeState(address);
    return {
      status: updated.status,
      vouches_needed: Math.max(0, CONFIG.vouchingK - updated.vouches.size),
      vouches_have: updated.vouches.size,
    };
  }

  async vouch(voucher: string, target: string) {
    const v = voucher.toLowerCase();
    const t = target.toLowerCase();
    if (v === t) {
      return { status: this.computeState(t).status, vouches_have: 0, vouches_needed: CONFIG.vouchingK };
    }
    // Voucher must themselves be a person.
    const voucherStatus = await this.status(v);
    if (voucherStatus !== 'granted') {
      log('warn', 'personhood', 'vouch rejected — voucher not granted', { voucher: v, target: t, voucher_status: voucherStatus });
      const cur = this.computeState(t);
      return { status: cur.status, vouches_have: cur.vouches.size, vouches_needed: Math.max(0, CONFIG.vouchingK - cur.vouches.size) };
    }
    const cur = this.computeState(t);
    if (!cur.vouches.has(v)) {
      appendJsonl(this.path, { ts: new Date().toISOString(), op: 'vouch', target: t, by: v });
      log('info', 'personhood', 'vouch recorded', { voucher: v, target: t });
    }
    const upd = this.computeState(t);
    return {
      status: upd.status,
      vouches_have: upd.vouches.size,
      vouches_needed: Math.max(0, CONFIG.vouchingK - upd.vouches.size),
    };
  }

  async grant(target: string, grantor: string) {
    const t = target.toLowerCase();
    appendJsonl(this.path, { ts: new Date().toISOString(), op: 'grant', target: t, by: grantor.toLowerCase() });
    log('info', 'personhood', 'sovereign grant', { target: t, by: grantor });
    return { status: 'granted' as const };
  }
}

// ── BonaFideOracle (post-mint, stub) ──────────────────────────────────
// Phase F ships the interface + a placeholder implementation that always
// returns 'none'. Phase F2 wires the real Algorand indexer read.

class BonaFideOracleImpl implements PersonhoodOracle {
  async status(_address: string): Promise<PersonhoodStatus> {
    if (!CONFIG.bonaFideAsaId || !CONFIG.bonaFideIndexer) return 'none';
    // Real impl lands when ASA is on testnet — for now defer to vouching.
    return 'none';
  }
  async tier_score(_address: string): Promise<number> { return 0; }
  async declare(address: string) {
    return { status: 'none' as PersonhoodStatus, vouches_needed: 1, vouches_have: 0 };
  }
  async vouch(_voucher: string, _target: string) {
    return { status: 'none' as PersonhoodStatus, vouches_have: 0, vouches_needed: 1 };
  }
  async grant(target: string, grantor: string) {
    log('info', 'personhood', 'sovereign grant (bona-fide stub)', { target, by: grantor });
    return { status: 'granted' as const };
  }
}

// ── Singleton ─────────────────────────────────────────────────────────

let ORACLE: PersonhoodOracle | null = null;

export function oracle(): PersonhoodOracle {
  if (ORACLE) return ORACLE;
  ORACLE = CONFIG.bonaFideLive ? new BonaFideOracleImpl() : new VouchingOracleImpl();
  log('info', 'personhood', 'oracle initialized', {
    impl: CONFIG.bonaFideLive ? 'BonaFideOracle' : 'VouchingOracle',
    k: CONFIG.vouchingK,
  });
  return ORACLE;
}
