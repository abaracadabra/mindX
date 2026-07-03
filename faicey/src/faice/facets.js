/**
 * facets.js — resolve the seven facets of an agent for the Faice FACE service.
 *
 *   .model · .agent · .prompt · .persona · .skill · .attribute · .reputation
 *
 * Reads what mindX actually exposes (identity registry, .agent files, dojo reputation
 * snapshot, skills manifest, prompt registry) with graceful fallbacks, so the loader
 * works standalone (every facet degrades to a sane default) and richer when run inside
 * the mindX tree. Pure Node, zero external deps (in-house, isolated-build friendly).
 *
 * The returned object is the exact input shape `faceFromFacets()` expects, and the same
 * resolved `reputation` drives the x402 privilege gate — one source of truth.
 */

import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
// faicey/src/faice -> mindX root is three up; override with MINDX_ROOT.
const MINDX_ROOT = process.env.MINDX_ROOT || join(__dirname, '..', '..', '..');

function readJSON(path) {
  try {
    return existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
  } catch {
    return null;
  }
}

// --- registry / identity ---------------------------------------------------
function loadRegistry() {
  return (
    readJSON(join(MINDX_ROOT, 'data', 'identity', 'production_registry.json')) || {
      agents: [],
    }
  );
}

function findRegistryEntry(registry, agentId) {
  const id = String(agentId).toLowerCase();
  return (
    registry.agents.find((a) => (a.entity_id || '').toLowerCase() === id) ||
    registry.agents.find((a) => (a.address || '').toLowerCase() === id) ||
    null
  );
}

// --- reputation (dojo) -----------------------------------------------------
function loadReputation(agentId, address) {
  const snap =
    readJSON(join(MINDX_ROOT, 'data', 'governance', 'dojo_snapshot.json')) || {};
  const scores = snap.scores || {};
  const keys = [address, agentId].filter(Boolean).map((k) => String(k).toLowerCase());
  for (const k of Object.keys(scores)) {
    if (keys.includes(k.toLowerCase())) return { score: Number(scores[k]) || 0 };
  }
  return { score: 0 };
}

// --- skills ----------------------------------------------------------------
function loadSkillCount() {
  const manifest = readJSON(join(MINDX_ROOT, 'data', 'skills', 'manifest.json'));
  if (manifest && Array.isArray(manifest.skills)) {
    return { count: manifest.skills.length };
  }
  if (manifest && typeof manifest === 'object') {
    return { count: Object.keys(manifest).length };
  }
  return { count: 0 };
}

// --- .agent file -----------------------------------------------------------
// derive a persona role enum + traits from the registry role text / .agent file
const ROLE_KEYWORDS = [
  [/secur|guardian|threat|access/i, 'governance'],
  [/strateg|ceo|mastermind|director|board/i, 'governance'],
  [/coordinat|infrastruct|deploy|host|ops/i, 'worker'],
  [/market|publish|author|content/i, 'marketing'],
  [/develop|coder|engineer|build/i, 'development'],
  [/research|analy|reason|cogn/i, 'expert'],
  [/communit|persona|avatar/i, 'community'],
];

function roleFromText(text) {
  if (!text) return 'meta';
  for (const [re, role] of ROLE_KEYWORDS) if (re.test(text)) return role;
  return 'meta';
}

function parseAgentFile(agentId) {
  // .agent files use dotted names (agents/hostinger.vps.agent). Try a few forms.
  const candidates = [
    agentId,
    String(agentId).replace(/_agent_main$/, '').replace(/_/g, '.'),
    String(agentId).replace(/_/g, '.'),
  ];
  for (const c of candidates) {
    const path = join(MINDX_ROOT, 'agents', `${c}.agent`);
    if (existsSync(path)) {
      const text = readFileSync(path, 'utf8');
      const domain = (text.match(/^DOMAIN:\s*(.+)$/m) || [])[1]?.trim();
      const voice = (text.match(/voice:\s*(.+)$/m) || [])[1]?.trim();
      return { domain, voice, found: true };
    }
  }
  return { found: false };
}

/**
 * Resolve all seven facets for `agentId`.
 * @param {string} agentId entity_id (e.g. "guardian_agent_main") or 0x address
 * @param {object} [overrides] explicit facet overrides (e.g. for testing / quotes):
 *        { reputation, skill, model, prompt, persona, attribute }
 * @returns {{facets: object, source: object}} facets for faceFromFacets + provenance
 */
export function loadFacets(agentId, overrides = {}) {
  const registry = loadRegistry();
  const entry = findRegistryEntry(registry, agentId);
  const address = entry?.address || (String(agentId).startsWith('0x') ? agentId : undefined);
  const roleText = entry?.role;
  const agentFile = parseAgentFile(agentId);

  const role = roleFromText(roleText || agentFile.domain);
  const reputation =
    overrides.reputation !== undefined
      ? typeof overrides.reputation === 'object'
        ? overrides.reputation
        : { score: Number(overrides.reputation) || 0 }
      : loadReputation(agentId, address);

  const skill = overrides.skill !== undefined ? overrides.skill : loadSkillCount();

  // attributes: pull salient tokens from the role description
  const attribute =
    overrides.attribute ||
    (roleText
      ? roleText
          .split(/[\s,—–\-]+/)
          .filter((w) => w.length > 3)
          .slice(0, 5)
          .map((w) => w.toLowerCase())
      : []);

  const facets = {
    model: overrides.model || { task_class: role === 'expert' ? 'reasoning' : 'general', logical_model: 'auto' },
    agent: { id: agentId, name: entry?.entity_id || agentId, domain: agentFile.domain, address },
    prompt: overrides.prompt || { type: 'agent', category: role },
    persona: overrides.persona || { id: address ? 'professor-codephreak' : 'mindx-base', role, traits: attribute },
    skill,
    attribute,
    reputation,
  };

  return {
    facets,
    source: {
      registryHit: !!entry,
      agentFileFound: agentFile.found,
      hasReputationData: existsSync(
        join(MINDX_ROOT, 'data', 'governance', 'dojo_snapshot.json')
      ),
      address: address || null,
      roleText: roleText || null,
      mindxRoot: MINDX_ROOT,
    },
  };
}

/** List known agent ids from the identity registry (for /api/faice index). */
export function listAgents() {
  const registry = loadRegistry();
  return registry.agents.map((a) => ({
    id: a.entity_id,
    role: a.role,
    address: a.address,
  }));
}
