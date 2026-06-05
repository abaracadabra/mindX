/**
 * overlord.js — overlord privilege for the Faice FACE service.
 *
 * Verifies the overlord-session JWT issued by mindX's overlord model
 * (mindx_backend_service/overlord/routes.py): HS256, scope "overlord.session",
 * claims { sub, role, level, scope, jti, iat, exp }. Secret is MINDX_OVERLORD_JWT_SECRET
 * (or SHADOW_JWT_SECRET) — the SAME secret the backend signs with, so a token minted by
 * `POST /overlord/verify` is honored here.
 *
 * In-house HS256 (Node crypto, no jsonwebtoken dependency) — isolated-build friendly.
 *
 * Roles (ascending): public < member < overseer < overlord. "overlord" is the ultimate
 * privilege — it bypasses every other FACE gate (reputation, x402).
 */

import { createHmac, timingSafeEqual } from 'node:crypto';

export const OVERLORD_SESSION_SCOPE = 'overlord.session';

export const ROLE_ORDINAL = { public: 0, member: 1, overseer: 2, overlord: 3 };

// The overlord of the mindx/agenticplace/bankon cryptosystem is **bankon.eth**: its wallet
// public key (resolved address) holds the overlord role, granted from signature. The ENS
// name is canonical; the resolved address is configured via FAICE_OVERLORD_ADDRESS (set it
// to bankon.eth's address). When configured, the 'overlord' role is BOUND to that address —
// an overlord-session token whose subject isn't bankon.eth is not honored as overlord.
export const OVERLORD_ENS = process.env.FAICE_OVERLORD_ENS || 'bankon.eth';

export function overlordAddress() {
  const a = process.env.FAICE_OVERLORD_ADDRESS || '';
  return a ? a.toLowerCase() : null;
}

export function overlordIdentity() {
  return { ens: OVERLORD_ENS, address: process.env.FAICE_OVERLORD_ADDRESS || null };
}

export function isPrivilegedRole(role) {
  return (ROLE_ORDINAL[role] ?? 0) >= ROLE_ORDINAL.member;
}

function secret() {
  const s = process.env.MINDX_OVERLORD_JWT_SECRET || process.env.SHADOW_JWT_SECRET || '';
  if (s.length < 32) {
    const err = new Error('overlord JWT secret not configured (32+ chars)');
    err.code = 'OVERLORD_SECRET_MISSING';
    throw err;
  }
  return s;
}

// --- base64url helpers ------------------------------------------------------
function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64urlJSON(obj) {
  return b64url(Buffer.from(JSON.stringify(obj)));
}
function fromB64url(str) {
  return Buffer.from(str.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

// --- verify (mirror of Python verify_overlord_token) -----------------------
/**
 * Verify an overlord-session JWT. Returns the claims, or throws with .code.
 * @param {string} token
 * @param {{now?: number}} [opts]
 */
export function verifyOverlordToken(token, opts = {}) {
  const parts = String(token || '').split('.');
  if (parts.length !== 3) {
    const e = new Error('malformed token');
    e.code = 'OVERLORD_INVALID';
    throw e;
  }
  const [h, p, sig] = parts;
  const expected = b64url(createHmac('sha256', secret()).update(`${h}.${p}`).digest());
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    const e = new Error('bad signature');
    e.code = 'OVERLORD_INVALID';
    throw e;
  }
  let claims;
  try {
    claims = JSON.parse(fromB64url(p).toString('utf8'));
  } catch {
    const e = new Error('bad payload');
    e.code = 'OVERLORD_INVALID';
    throw e;
  }
  const now = opts.now ?? Math.floor(Date.now() / 1000);
  if (claims.exp && now >= claims.exp) {
    const e = new Error('overlord token expired');
    e.code = 'OVERLORD_EXPIRED';
    throw e;
  }
  if (claims.scope !== OVERLORD_SESSION_SCOPE) {
    const e = new Error('not an overlord session token');
    e.code = 'OVERLORD_SCOPE';
    throw e;
  }
  return claims;
}

// --- issue (mirror of Python issue_overlord_token) — for tests / local mint -
/**
 * Mint an overlord-session JWT. Production tokens come from the backend's /overlord/verify;
 * this exists so tests (and trusted local tooling) can mint with the shared secret.
 * @param {{sub: string, role?: string, level?: number, ttlSec?: number, now?: number}} a
 */
export function issueOverlordToken(a) {
  const now = a.now ?? Math.floor(Date.now() / 1000);
  const header = { alg: 'HS256', typ: 'JWT' };
  const claims = {
    sub: a.sub,
    role: a.role || 'overlord',
    level: a.level ?? 1,
    scope: OVERLORD_SESSION_SCOPE,
    jti: `${now.toString(16)}${Math.floor((now * 2654435761) % 0xffffffff).toString(16)}`,
    iat: now,
    exp: now + (a.ttlSec ?? 300),
  };
  const signingInput = `${b64urlJSON(header)}.${b64urlJSON(claims)}`;
  const sig = b64url(createHmac('sha256', secret()).update(signingInput).digest());
  return `${signingInput}.${sig}`;
}

// --- request helpers --------------------------------------------------------
/** Pull a raw token from Authorization: Bearer, X-Overlord-Token, or ?overlord= */
export function readOverlordToken(req) {
  const auth = req.headers?.['authorization'] || '';
  if (auth.startsWith('Bearer ')) return auth.slice(7).trim();
  const x = req.headers?.['x-overlord-token'];
  if (x) return String(x).trim();
  if (req.query?.overlord) return String(req.query.overlord).trim();
  return null;
}

/**
 * Resolve overlord privilege for a request, or null if none/invalid.
 * @returns {{role, level, address, isOverlord, privileged, reason}|null}
 */
export function overlordPrivilege(req) {
  const token = readOverlordToken(req);
  if (!token) return null;
  try {
    const claims = verifyOverlordToken(token);
    let role = claims.role;
    let reason = `overlord token (${role} L${claims.level})`;

    // Bind the overlord role to bankon.eth when its address is configured: a signature-proven
    // overlord token MUST have bankon.eth as its subject to wield overlord power here.
    const bound = overlordAddress();
    if (role === 'overlord' && bound) {
      if (String(claims.sub || '').toLowerCase() === bound) {
        reason = `overlord = ${OVERLORD_ENS} (${claims.sub}), signature-proven`;
      } else {
        role = 'overseer'; // authentic token, but not bankon.eth → not THE overlord
        reason = `token subject is not ${OVERLORD_ENS}; downgraded from overlord`;
      }
    }

    return {
      role,
      level: claims.level,
      address: claims.sub,
      ens: role === 'overlord' ? OVERLORD_ENS : undefined,
      isOverlord: role === 'overlord',
      privileged: isPrivilegedRole(role),
      reason,
    };
  } catch (e) {
    return { role: 'public', error: e.code || 'OVERLORD_INVALID', privileged: false };
  }
}
