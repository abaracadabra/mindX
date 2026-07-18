/**
 * nose_tools.js — the nose smells the network.
 *
 * The face-as-control-surface, continued: the NOSE is networking diagnostics,
 * and its two nostrils sniff two chains of information —
 *   • right nostril → BLOCKCHAIN scanning (an EVM read, at 18-dp)
 *   • left  nostril → RAGE search (the knowledge index at rage.pythai.net)
 *
 * Pure helpers — latency statistics, JSON-RPC payloads, wei→ETH at conventional
 * EVM 18-decimal precision, address validation, search ranking. The live fetch /
 * wallet calls are the browser layer; everything here is headless-tested.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { mean, stddev } from './finmeasure.js';

// ── networking diagnostics (the nose) ───────────────────────────────────────
/** Grade a round-trip latency in ms. */
export function classifyLatency(ms) {
  if (!(ms >= 0)) return 'unknown';
  if (ms < 50) return 'excellent';
  if (ms < 120) return 'good';
  if (ms < 300) return 'fair';
  return 'poor';
}
/** Summarise a set of ping samples → {min,avg,max,jitter,grade,n}. */
export function pingStats(samplesMs) {
  const s = (samplesMs || []).filter((v) => v >= 0);
  if (!s.length) return { min: null, avg: null, max: null, jitter: null, grade: 'unknown', n: 0 };
  const avg = mean(s);
  return { min: Math.min(...s), avg, max: Math.max(...s), jitter: stddev(s), grade: classifyLatency(avg), n: s.length };
}
/** Connectivity summary from a navigator-like object (online + link type). */
export function connectionSummary(nav = (typeof navigator !== 'undefined' ? navigator : {})) {
  const c = nav.connection || nav.mozConnection || nav.webkitConnection || {};
  return {
    online: nav.onLine !== false,
    effectiveType: c.effectiveType || 'unknown',
    downlinkMbps: typeof c.downlink === 'number' ? c.downlink : null,
    rttMs: typeof c.rtt === 'number' ? c.rtt : null,
  };
}

// ── blockchain scanning (right nostril) ─────────────────────────────────────
export const isAddress = (a) => typeof a === 'string' && /^0x[0-9a-fA-F]{40}$/.test(a);
export const isTxHash = (h) => typeof h === 'string' && /^0x[0-9a-fA-F]{64}$/.test(h);

/** A JSON-RPC 2.0 request payload. */
export function rpcPayload(method, params = [], id = 1) {
  return { jsonrpc: '2.0', id, method, params };
}

/** wei → ETH as an 18-decimal fixed-point string (conventional EVM precision). */
export function weiToEth(wei) {
  let v;
  try { v = typeof wei === 'bigint' ? wei : BigInt(wei); } catch { return '0.000000000000000000'; }
  const neg = v < 0n; if (neg) v = -v;
  const ONE = 10n ** 18n;
  return (neg ? '-' : '') + (v / ONE).toString() + '.' + (v % ONE).toString().padStart(18, '0');
}

const CHAINS = { '0x1': 'Ethereum', '0x89': 'Polygon', '0x2105': 'Base', '0xa4b1': 'Arbitrum', '0xa': 'Optimism', '0x7a69': 'anvil' };
export const chainName = (hexId) => CHAINS[(hexId || '').toLowerCase()] || `chain ${hexId}`;

/** Shape an address scan (balance hex + nonce hex + chain) into a readout. */
export function formatScan({ address, balanceWei, nonceHex, chainIdHex }) {
  return {
    address,
    eth: weiToEth(balanceWei ?? 0),
    nonce: nonceHex != null ? Number(BigInt(nonceHex)) : null,
    chain: chainName(chainIdHex),
  };
}

// ── RAGE search (left nostril) ──────────────────────────────────────────────
/** Build a WordPress search URL for the RAGE knowledge index. */
export function buildSearchUrl(base, query) {
  const b = (base || 'https://rage.pythai.net').replace(/\/+$/, '');
  return `${b}/?s=${encodeURIComponent(query || '')}`;
}
/** WP REST search endpoint (titles + links) for a proxy fetch. */
export function buildRestSearchUrl(base, query, perPage = 8) {
  const b = (base || 'https://rage.pythai.net').replace(/\/+$/, '');
  return `${b}/wp-json/wp/v2/search?search=${encodeURIComponent(query || '')}&per_page=${perPage}`;
}
/** Rank results by how many query terms appear in the title (desc). */
export function rankResults(items, query) {
  const terms = String(query || '').toLowerCase().split(/\s+/).filter(Boolean);
  const score = (t) => { const s = String(t || '').toLowerCase(); return terms.reduce((n, w) => n + (s.includes(w) ? 1 : 0), 0); };
  return (items || []).map((r) => ({ ...r, score: score(r.title) }))
    .sort((a, b) => b.score - a.score);
}

export default pingStats;
