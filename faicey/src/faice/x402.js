/**
 * x402.js — x402 payment rails for the Faice FACE service (Express, in-house).
 *
 * Mirrors mindX's x402 contract (mindx_backend_service/x402_middleware.py): a triple-rail
 * HTTP 402 envelope, an `X-PAYMENT` settlement header, and a facilitator /verify round-trip.
 * Rails + facilitator are read from mindX's data/config/x402_pricing.json when present
 * (single source of truth); a bundled fallback keeps faicey runnable standalone.
 *
 * "FACE as privilege": the gate grants free access when the REQUESTED agent's reputation
 * rank meets the privilege floor (or it is BONA FIDE) — privilege earned by reputation,
 * exactly the reputation bypass mindX's x402 design reserves. Otherwise the FACE is a
 * cost-bearing resource and the caller must settle on a rail (or present X-PAYMENT).
 *
 * No external x402 library — hand-rolled to keep isolated builds minimal.
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { overlordPrivilege } from './overlord.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MINDX_ROOT = process.env.MINDX_ROOT || join(__dirname, '..', '..', '..');
const FAICE_PRICING = join(__dirname, 'faice_pricing.json');
const MINDX_PRICING = join(MINDX_ROOT, 'data', 'config', 'x402_pricing.json');

function readJSON(path) {
  try {
    return existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
  } catch {
    return null;
  }
}

// --- pricing (hot-reloaded by mtime, like the python middleware) -----------
let _cache = { mtime: 0, pricing: null };

export function loadPricing() {
  const facePricing = readJSON(FAICE_PRICING) || {};
  const mindxPricing = readJSON(MINDX_PRICING);
  const mtime =
    (existsSync(FAICE_PRICING) ? statSync(FAICE_PRICING).mtimeMs : 0) +
    (existsSync(MINDX_PRICING) ? statSync(MINDX_PRICING).mtimeMs : 0);
  if (_cache.pricing && _cache.mtime === mtime) return _cache.pricing;

  const rails = mindxPricing?.rails || facePricing.fallback_rails || {};
  const facilitator = mindxPricing?.facilitator || facePricing.fallback_facilitator || {};
  const pricing = {
    privilegeFloor: facePricing.privilegeFloor || 'expert',
    endpoints: facePricing.endpoints || {},
    rails,
    facilitator,
    railSource: mindxPricing?.rails ? 'mindx:data/config/x402_pricing.json' : 'faicey:fallback',
  };
  _cache = { mtime, pricing };
  return pricing;
}

// --- 402 envelope (triple-rail) --------------------------------------------
function isZeroPayTo(payTo) {
  return (
    !payTo ||
    payTo === '' ||
    /^0x0+$/i.test(String(payTo))
  );
}

export function build402Envelope(endpointId, maxAmount, profile, agentId) {
  const pricing = loadPricing();
  const paymentRequirements = Object.values(pricing.rails)
    .map((rail) => ({
      scheme: rail.scheme || 'exact',
      network: rail.network,
      asset: rail.asset,
      maxAmountRequired: String(maxAmount),
      payTo: rail.payTo,
      resource: endpointId,
      description: rail._comment || `${rail.network} settlement`,
      mimeType: 'application/json',
      extra: rail.extra || {},
      // advertise even when payTo is a placeholder, but flag it so clients pick a live rail
      settleable: !isZeroPayTo(rail.payTo),
    }))
    .filter((r) => r.network);

  return {
    code: 'x402_payment_required',
    message:
      'This FACE is a privilege. Settle on any offered rail and re-submit with X-PAYMENT, ' +
      'or acquire reputation (rank >= ' + pricing.privilegeFloor + ') to render it for free.',
    endpoint: endpointId,
    paymentRequirements,
    x402Version: 1,
    faice: {
      agent: agentId,
      signature: profile?.signature,
      privilege: profile?.privilege,
    },
    _note: 'Mirrors docs/services/x402_as_a_service.md. Rails: ' + pricing.railSource,
  };
}

// --- X-PAYMENT verification ------------------------------------------------
const _settleCache = new Map(); // key -> {ts, record}
const SETTLE_TTL_MS = 60_000;

function testMode() {
  return process.env.MINDX_X402_TEST_MODE === '1' || process.env.FAICE_X402_TEST_MODE === '1';
}

export async function verifyXPayment(headerValue, endpointId, maxAmount) {
  let envelope;
  try {
    envelope = JSON.parse(Buffer.from(headerValue, 'base64').toString('utf8'));
  } catch {
    return { ok: false, reason: 'X-PAYMENT is not valid base64 JSON' };
  }
  if (!envelope || envelope.scheme !== 'exact' || !envelope.network || !envelope.payload) {
    return { ok: false, reason: 'X-PAYMENT envelope must have {scheme:"exact", network, payload}' };
  }

  const cacheKey = `${envelope.network}:${JSON.stringify(envelope.payload)}`;
  const cached = _settleCache.get(cacheKey);
  if (cached && Date.now() - cached.ts < SETTLE_TTL_MS) {
    return { ok: true, record: cached.record, cached: true };
  }

  if (testMode()) {
    const record = {
      rail: envelope.network,
      tx_hash: '0xtest',
      amount_microusd: maxAmount,
      verified_at: new Date(0).toISOString().replace('1970', '2026'),
      facilitator: 'test-mode',
    };
    _settleCache.set(cacheKey, { ts: Date.now(), record });
    return { ok: true, record };
  }

  // production: round-trip to the facilitator
  const pricing = loadPricing();
  const base = pricing.facilitator.url;
  const verifyPath = pricing.facilitator.verify_endpoint || '/verify';
  if (!base) return { ok: false, reason: 'no facilitator configured' };
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 8000);
    const resp = await fetch(base + verifyPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scheme: envelope.scheme,
        network: envelope.network,
        payload: envelope.payload,
        endpoint: endpointId,
        max_amount_microusd: maxAmount,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(t);
    if (!resp.ok) return { ok: false, reason: `facilitator HTTP ${resp.status}` };
    const data = await resp.json();
    if (!data.verified) return { ok: false, reason: data.reason || 'not verified' };
    const record = {
      rail: envelope.network,
      tx_hash: data.txHash,
      amount_microusd: data.amount ?? maxAmount,
      verified_at: new Date().toISOString(),
      facilitator: base,
    };
    _settleCache.set(cacheKey, { ts: Date.now(), record });
    return { ok: true, record };
  } catch (e) {
    return { ok: false, reason: `facilitator unreachable: ${e.message}`, transient: true };
  }
}

/**
 * Express gate for a FACE endpoint. Requires `req.faice = { agentId, profile }` to have
 * been attached upstream (see service.attachFaice). Decides: privilege (free) | x402
 * settled (paid) | 402 required.
 *
 * @param {string} endpointId pricing key, e.g. '/api/faice/:agent'
 */
export function faiceX402Gate(endpointId) {
  return async function gate(req, res, next) {
    const pricing = loadPricing();
    const cfg = pricing.endpoints[endpointId] || { max_amount_microusd: 1000 };
    const maxAmount = cfg.max_amount_microusd;
    const profile = req.faice?.profile;
    const agentId = req.faice?.agentId;

    // 0. Overlord — the ultimate privilege. A signature-proven overlord/overseer/member
    //    session (overlord-session JWT) bypasses every other FACE gate.
    const ov = overlordPrivilege(req);
    if (ov?.privileged) {
      req.overlord = ov;
      req.faiceAccess = {
        path: 'overlord',
        role: ov.role,
        level: ov.level,
        address: ov.address,
        reason: ov.reason,
      };
      return next();
    }

    // 1. FACE as privilege — reputation grants free access
    if (profile?.privilege?.granted) {
      req.faiceAccess = {
        path: 'privilege',
        reason: profile.privilege.reason,
        rank: profile.privilege.rank,
      };
      return next();
    }

    // 2. X-PAYMENT settlement on an x402 rail
    const xPayment = req.headers['x-payment'];
    if (xPayment) {
      const result = await verifyXPayment(xPayment, endpointId, maxAmount);
      if (result.ok) {
        req.faiceAccess = { path: 'x402_settled', ...result.record, cached: !!result.cached };
        return next();
      }
      if (result.transient) {
        return res.status(503).json({ code: 'facilitator_unavailable', reason: result.reason });
      }
      // invalid payment falls through to a fresh 402
      res.set('X-Payment-Error', result.reason);
    }

    // 3. Payment required
    const envelope = build402Envelope(endpointId, maxAmount, profile, agentId);
    return res.status(402).json(envelope);
  };
}

/**
 * Express guard requiring overlord privilege (member+). Interaction with a FACE — driving
 * its expression, overriding facets — is an overlord-only capability. Returns 401 otherwise.
 * @param {string} [minRole] minimum role (default 'overlord'); 'member'/'overseer' to relax
 */
export function requireOverlord(minRole = 'overlord') {
  const floor = { public: 0, member: 1, overseer: 2, overlord: 3 }[minRole] ?? 3;
  return function guard(req, res, next) {
    const ov = overlordPrivilege(req);
    if (!ov || !ov.privileged) {
      return res.status(401).json({
        code: 'overlord_required',
        message:
          'This FACE interaction requires an overlord session. Obtain an overlord-session ' +
          'token via POST /overlord/challenge + /overlord/verify (signature-proven), then ' +
          'send it as Authorization: Bearer <token> (or X-Overlord-Token).',
        detail: ov?.error || 'no overlord token',
      });
    }
    const have = { public: 0, member: 1, overseer: 2, overlord: 3 }[ov.role] ?? 0;
    if (have < floor) {
      return res.status(403).json({
        code: 'overlord_role_insufficient',
        message: `requires role >= ${minRole}; have ${ov.role}`,
      });
    }
    req.overlord = ov;
    next();
  };
}
