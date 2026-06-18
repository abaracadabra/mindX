// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// DatoClient — the UI's view of dato naming + data, mirroring dato/core/{naming,permanence}.
//
// Naming: <handle>.<tier>.<root>; the tier label declares permanence
//   (immortal | immutable | mutable). Roots are extensible and each has a KIND:
//     local — a free dato-registry name (default root "blockchain")
//     arns  — an ar.io ARNS name (root "ar"): registering it is a PURCHASE on
//             ar.io (HyperBEAM/ARIO). The UI surfaces the purchase + hands off
//             to parsec-wallet's ario flow rather than pretending it's free.
//
// Data: commit records at a permanence tier
//   immortal  — permanent Arweave upload (200-yr); proof = Arweave tx id (real
//               upload runs server-side via tools/arweave_turbo / the dato AO
//               process; here we record the intent + sha256 and mark pending).
//   immutable — sha256 hash-locked; re-commit with different bytes is rejected.
//   mutable   — editable, versioned.
//
// Backend is pluggable. Default = browser localStorage (works standalone with no
// server). Pass a backend with {registerName, commit, listRecords, listNames} to
// target the dato AO process (via parsec aoconnect) or the mindX /dato HTTP API.

export const TIERS = ['immortal', 'immutable', 'mutable'];

const DEFAULT_ROOTS = [
  { name: 'blockchain', kind: 'local', purchase: false, note: 'free dato-registry name' },
  { name: 'ar', kind: 'arns', purchase: true, note: 'ar.io ARNS — registration is a purchase (HyperBEAM/ARIO)' },
];

const LABEL_RE = /^[a-z0-9][a-z0-9-]{0,62}$/;
const LS_KEY = 'dato:registry:v1';

function loadLS() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
    return { names: s.names || {}, records: s.records || {}, datos: s.datos || {} };
  } catch { return { names: {}, records: {}, datos: {} }; }
}
function saveLS(s) { try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch {} }

async function sha256Hex(bytes) {
  const buf = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export class DatoClient {
  constructor(opts = {}) {
    this.backend = opts.backend || null;          // optional remote backend
    this.roots = [...DEFAULT_ROOTS, ...(opts.extraRoots || [])];
    this.arioHandoff = opts.arioHandoff || null;  // (arnsName) => void, set by parsec adapter
  }

  rootList() { return this.roots.map((r) => ({ ...r })); }

  addRoot(name, kind = 'local') {
    name = (name || '').trim().toLowerCase();
    if (!LABEL_RE.test(name)) throw new Error('invalid root label');
    if (!this.roots.find((r) => r.name === name)) {
      this.roots.push({ name, kind, purchase: kind === 'arns', note: kind === 'arns' ? 'ar.io ARNS (purchase)' : 'dato-registry name' });
    }
  }

  validateLabel(label, kind) {
    if (!LABEL_RE.test((label || '').toLowerCase())) throw new Error(`invalid ${kind} (a-z0-9-, ≤63, no leading -)`);
    return label.toLowerCase();
  }

  composeName(handle, tier, root) {
    handle = this.validateLabel(handle, 'handle');
    if (!TIERS.includes(tier)) throw new Error(`tier must be one of ${TIERS.join(', ')}`);
    const r = this.roots.find((x) => x.name === root);
    if (!r) throw new Error(`unknown root ${root}`);
    return { name: `${handle}.${tier}.${root}`, root: r, tier, handle };
  }

  /** Register a name. local → stored free; arns → returns a purchase directive. */
  async registerName(handle, tier, root, { controller } = {}) {
    const composed = this.composeName(handle, tier, root);
    if (composed.root.kind === 'arns') {
      // ar.io ARNS: registration is a PURCHASE — do not pretend otherwise.
      const arnsName = `${handle}_${tier}`; // ARNS undername convention for the dato
      return {
        ok: false, needsPurchase: true, name: composed.name, arnsName,
        message: `Registering ${composed.name} on ar.io ARNS is a purchase (HyperBEAM/ARIO). `
          + `Buy/assign the ARNS name, then bind it to this dato.`,
        handoff: () => (this.arioHandoff ? this.arioHandoff(arnsName) : window.open('https://arns.app/', '_blank')),
      };
    }
    if (this.backend?.registerName) return this.backend.registerName(composed.name, { controller });
    const s = loadLS();
    if (s.names[composed.name] && s.names[composed.name].controller !== controller) {
      throw new Error(`${composed.name} already controlled by another wallet`);
    }
    s.names[composed.name] = { controller: controller || 'local', tier, root, kind: 'local', proof: null, created: Date.now() };
    saveLS(s);
    return { ok: true, name: composed.name, kind: 'local' };
  }

  async listNames() {
    if (this.backend?.listNames) return this.backend.listNames();
    const s = loadLS();
    return Object.entries(s.names).map(([name, v]) => ({ name, ...v }));
  }

  /** Commit data at a permanence tier under <handle>.<tier>.<root>. */
  async commit(handle, tier, root, content) {
    const composed = this.composeName(handle, tier, root);
    const bytes = typeof content === 'string' ? new TextEncoder().encode(content) : new Uint8Array(content);
    const sha256 = await sha256Hex(bytes);
    if (this.backend?.commit) return this.backend.commit(composed.name, { tier, sha256, bytes });

    const s = loadLS();
    const prev = s.records[composed.name];
    if (tier === 'immutable' && prev && prev.tier === 'immutable' && prev.sha256 !== sha256) {
      throw new Error(`immutable lock: ${composed.name} is pinned to ${prev.sha256.slice(0, 12)}…`);
    }
    let proof = null, status = 'committed', version = 1;
    if (tier === 'immortal') {
      // Real ANS-104 upload runs server-side (tools/arweave_turbo) or via the
      // dato AO process. The UI records the intent + sha256 and marks it pending
      // until a backend returns the Arweave tx id.
      proof = null; status = 'pending-arweave-upload';
    } else if (tier === 'immutable') {
      proof = `anchor:${sha256}`;
    } else {
      version = prev && prev.tier === 'mutable' ? (prev.version || 1) + 1 : 1;
    }
    s.records[composed.name] = {
      name: composed.name, tier, sha256, proof, status, version,
      bytes_len: bytes.length, created: Date.now(),
      preview: tier === 'mutable' ? new TextDecoder().decode(bytes).slice(0, 240) : null,
    };
    saveLS(s);
    return s.records[composed.name];
  }

  async listRecords() {
    if (this.backend?.listRecords) return this.backend.listRecords();
    const s = loadLS();
    return Object.values(s.records).sort((a, b) => b.created - a.created);
  }

  // ── commerce: dato instances + request-to-join with fee ──────────────────
  /** Spawn a DAIO-owned dato (a data-DAO) with an optional join fee. */
  async spawnDato(handle, tier, root, { joinFeeMicroUSD = 0, openJoin = true } = {}) {
    const composed = this.composeName(handle, tier, root);
    if (this.backend?.spawnDato) return this.backend.spawnDato(composed.name, { joinFeeMicroUSD, openJoin });
    const s = loadLS();
    const datoId = 'dato_' + composed.name.replace(/[^a-z0-9]/g, '_') + '_' + Date.now().toString(36);
    s.datos[datoId] = {
      datoId, name: composed.name, tier, owner: this.controller || 'daio',
      deployer: this.controller || 'local', joinFeeMicroUSD: Number(joinFeeMicroUSD) || 0,
      openJoin: !!openJoin, members: { [this.controller || 'local']: { joinedAt: Date.now(), feePaid: 0 } },
      created: Date.now(),
    };
    saveLS(s);
    return s.datos[datoId];
  }

  async listDatos() {
    if (this.backend?.listDatos) return this.backend.listDatos();
    const s = loadLS();
    return Object.values(s.datos).sort((a, b) => b.created - a.created);
  }

  /** Quote the join fee + the x402 endpoint that settles it. */
  quoteJoin(datoId) {
    const s = loadLS();
    const d = s.datos[datoId];
    if (!d) throw new Error('unknown dato');
    return { datoId, name: d.name, feeMicroUSD: d.joinFeeMicroUSD, x402Endpoint: '/dato/join', free: d.joinFeeMicroUSD === 0, openJoin: d.openJoin };
  }

  /** Request to join. Paid datos require a settled x402 receipt (feeTx). */
  async joinDato(datoId, wallet, { feeTx = null, feePaidMicroUSD = 0, settings = {} } = {}) {
    if (this.backend?.joinDato) return this.backend.joinDato(datoId, wallet, { feeTx, feePaidMicroUSD, settings });
    const s = loadLS();
    const d = s.datos[datoId];
    if (!d) throw new Error('unknown dato');
    if (!d.openJoin && !d.members[wallet]) throw new Error('closed-join: owner approval required');
    if (d.joinFeeMicroUSD > 0 && (!feeTx || feePaidMicroUSD < d.joinFeeMicroUSD)) {
      const err = new Error(`join requires a ${d.joinFeeMicroUSD} microUSD fee settled on /dato/join (present the x402 receipt)`);
      err.needsFee = true; err.feeMicroUSD = d.joinFeeMicroUSD; throw err;
    }
    d.members[wallet] = { joinedAt: Date.now(), feePaid: Math.max(d.joinFeeMicroUSD, feePaidMicroUSD), feeTx, settings };
    saveLS(s);
    return d.members[wallet];
  }
}
