/**
 * service.js — the Faice FACE-as-a-service: facets -> canonical engine -> FACE.
 *
 * Resolves an agent's seven facets (facets.js), maps them to a wireframe FACE via the
 * canonical engine's faceFromFacets() (imported from the built engine bundle — the same
 * code FaceRig and the browser render), and exposes:
 *   - attachFaice : Express middleware loading req.faice = { agentId, facets, profile }
 *   - faiceDescriptor : JSON FACE descriptor
 *   - renderFacePage  : HTML that renders the FACE in-browser from the local engine
 *
 * The engine is consumed as the served bundle (static/vendor/faicey-engine.js) so server
 * and browser share one implementation. faceFromFacets is pure (no DOM) — safe in Node.
 */

import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadFacets, listAgents } from './facets.js';
import { loadPricing } from './x402.js';
import { overlordIdentity } from './overlord.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ENGINE = join(__dirname, '..', '..', 'static', 'vendor', 'faicey-engine.js');

// Import faceFromFacets from the canonical built engine (single source of truth).
const { faceFromFacets } = await import(ENGINE);

/** Parse optional facet overrides from query (for quotes / demos / testing). */
function overridesFromQuery(q = {}) {
  const o = {};
  if (q.reputation !== undefined) o.reputation = Number(q.reputation);
  if (q.skill !== undefined) o.skill = Number(q.skill);
  if (q.role !== undefined) o.persona = { role: String(q.role) };
  return o;
}

/** Express middleware: resolve facets + FACE profile onto req.faice. */
export function attachFaice(req, res, next) {
  const agentId = req.params.agent;
  if (!agentId) return res.status(400).json({ error: 'agent id required' });
  try {
    const overrides = overridesFromQuery(req.query);
    const { facets, source } = loadFacets(agentId, overrides);
    const pricing = loadPricing();
    const profile = faceFromFacets(facets, { privilegeFloor: pricing.privilegeFloor });
    req.faice = { agentId, facets, profile, source };
    next();
  } catch (e) {
    res.status(500).json({ error: 'faice resolution failed', detail: e.message });
  }
}

/** JSON FACE descriptor for an agent (post-gate). */
export function faiceDescriptor(req) {
  const { agentId, facets, profile, source } = req.faice;
  return {
    service: 'faice',
    agent: agentId,
    signature: profile.signature,
    face: {
      ...profile.options,
      faceColorHex: '#' + (profile.options.faceColor ?? 0).toString(16).padStart(6, '0'),
      expression: profile.expression,
      intensity: profile.intensity,
      persona: profile.persona,
      hue: profile.hue,
    },
    facets,
    privilege: profile.privilege,
    drivers: profile.drivers,
    access: req.faiceAccess || null,
    source,
  };
}

/** Free index: what the service is + known agents + how the gate works. */
export function faiceIndex() {
  const pricing = loadPricing();
  return {
    service: 'faice',
    description:
      'The FACE of an AI service. Renders an agent\'s identity from its seven facets ' +
      '(.model .agent .prompt .persona .skill .attribute .reputation) as a wireframe FACE.',
    facets: ['model', 'agent', 'prompt', 'persona', 'skill', 'attribute', 'reputation'],
    privilege: {
      rule: 'FACE as privilege — rank >= ' + pricing.privilegeFloor + ' (or BONA FIDE) renders free; otherwise settle via x402.',
      floor: pricing.privilegeFloor,
      overlord: {
        rule: 'The overlord (' + overlordIdentity().ens + ', signature-proven) bypasses every gate and may interact with any FACE.',
        identity: overlordIdentity(),
        interact: 'POST /api/faice/:agent/interact (Authorization: Bearer <overlord-session token>)',
      },
    },
    rails: Object.keys(pricing.rails),
    railSource: pricing.railSource,
    endpoints: {
      'GET /api/faice': 'this index (free)',
      'GET /api/faice/:agent/quote': 'price + privilege verdict for an agent (free)',
      'GET /api/faice/:agent': 'FACE descriptor JSON (privilege or x402)',
      'GET /faice/:agent': 'rendered wireframe FACE page (privilege or x402)',
    },
    agents: listAgents(),
  };
}

/** Free quote: show the privilege verdict + the 402 price for an agent, without gating. */
export function faiceQuote(req) {
  const { agentId, profile } = req.faice;
  const pricing = loadPricing();
  const cfg = pricing.endpoints['/api/faice/:agent'] || { max_amount_microusd: 1000 };
  return {
    service: 'faice',
    agent: agentId,
    signature: profile.signature,
    privilege: profile.privilege,
    free: profile.privilege.granted,
    price: profile.privilege.granted
      ? null
      : {
          max_amount_microusd: cfg.max_amount_microusd,
          rails: Object.keys(pricing.rails),
          note: 'present X-PAYMENT settled on a rail, or raise reputation to rank >= ' + pricing.privilegeFloor,
        },
  };
}

/**
 * Overlord interaction: drive a FACE (set expression) or override its facets and recompute.
 * Overlord-only (the route is guarded by requireOverlord). Returns the updated descriptor.
 * @param {object} req  has req.faice (attached) + req.overlord (from the guard)
 * @param {object} body { action: 'setExpression'|'override'|'inspect', expression?, intensity?, overrides? }
 */
export function faiceInteract(req, body = {}) {
  const { agentId } = req.faice;
  const action = body.action || 'inspect';
  const pricing = loadPricing();
  let profile = req.faice.profile;
  let applied = {};

  if (action === 'override') {
    // overlord may force any facet (e.g. reputation, role, skill) and recompute the FACE
    const overrides = body.overrides || {};
    const { facets } = loadFacets(agentId, overrides);
    profile = faceFromFacets(facets, { privilegeFloor: pricing.privilegeFloor });
    req.faice.facets = facets;
    req.faice.profile = profile;
    applied = { overrides };
  } else if (action === 'setExpression') {
    const expression = String(body.expression || profile.expression);
    const intensity = body.intensity != null ? Number(body.intensity) : profile.intensity;
    profile = { ...profile, expression, intensity };
    req.faice.profile = profile;
    applied = { expression, intensity };
  }

  return {
    service: 'faice',
    interaction: action,
    applied,
    by: { role: req.overlord?.role, level: req.overlord?.level, address: req.overlord?.address },
    descriptor: faiceDescriptor(req),
  };
}

/** HTML page rendering the agent's FACE via the local engine (post-gate). */
export function renderFacePage(req, wsPort) {
  const { agentId, profile } = req.faice;
  const o = profile.options;
  const access = req.faiceAccess?.path || 'privilege';
  const initialToken = req.query?.overlord ? String(req.query.overlord) : '';
  const accessLabel =
    access === 'overlord'
      ? 'OVERLORD (' + (req.faiceAccess?.role || 'overlord') + ')'
      : access === 'x402_settled'
      ? 'x402 SETTLED'
      : 'PRIVILEGE (reputation)';
  const accessClass = access === 'overlord' ? 'overlord' : access === 'privilege' ? 'granted' : 'paid';
  const EXPRESSIONS = ['neutral', 'smile', 'happy', 'laugh', 'thinking', 'coding', 'surprised', 'confused', 'sad', 'speaking'];
  return `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>Faice · ${agentId}</title>
<script type="importmap">{ "imports": {
  "three": "/static/vendor/three.module.js",
  "three/examples/jsm/controls/OrbitControls.js": "/static/vendor/jsm/controls/OrbitControls.js"
}}</script>
<style>
 body{margin:0;background:#05060a;color:#cde;font-family:'Courier New',monospace}
 .grid{display:grid;grid-template-columns:1fr 360px;height:100vh}
 .stage{background:radial-gradient(ellipse at center,#0a0e16,#05060a)}
 canvas{width:100%;height:100%}
 .panel{padding:18px;border-left:2px solid #${(o.faceColor ?? 0).toString(16).padStart(6,'0')};overflow:auto}
 h1{color:#${(o.faceColor ?? 0).toString(16).padStart(6,'0')};margin:.2em 0;font-size:1.6em;word-break:break-all}
 .tag{display:inline-block;padding:2px 8px;border:1px solid #2a3850;border-radius:10px;margin:2px;font-size:11px;color:#9fb}
 .kv{font-size:12px;color:#9ab;margin:6px 0}.kv b{color:#fff}
 .granted{color:#0f8}.paid{color:#fc6}.overlord{color:#f3c;font-weight:bold}
 .ovl{margin-top:14px;padding:12px;border:1px solid #41284a;border-radius:8px;background:#140a17}
 .ovl h3{color:#f3c;margin:.2em 0}
 .ovl input{width:100%;box-sizing:border-box;background:#0a0510;color:#fbd;border:1px solid #41284a;padding:6px;font-family:inherit;font-size:11px}
 .ovl button{background:#2a1430;color:#f9d;border:1px solid #62286a;border-radius:5px;padding:5px 9px;margin:3px 2px;font-family:inherit;cursor:pointer;font-size:11px}
 .ovl button:hover{background:#42204a}
 #ovl-status{font-size:11px;margin-top:6px}
</style></head><body>
<div class="grid">
  <div class="stage"><canvas id="face"></canvas></div>
  <div class="panel">
    <h1>${agentId}</h1>
    <div class="kv">signature <b>${profile.signature}</b></div>
    <div class="kv">access <b class="${accessClass}">${accessLabel}</b></div>
    <div class="kv">rank <b>${profile.privilege.rank}</b> · score <b>${profile.privilege.score}</b></div>
    <div class="kv">expression <b id="cur-expr">${profile.expression}</b> @ <b id="cur-int">${profile.intensity.toFixed(2)}</b></div>
    <div class="kv">hue <b>${profile.hue}°</b> · wire <b>${o.wireframeThickness}px</b></div>
    <h3 style="color:#7ad">facet drivers</h3>
    ${Object.entries(profile.drivers).map(([k, v]) => `<div class="kv"><b>.${k}</b> ${v}</div>`).join('')}

    <div class="ovl">
      <h3>⌁ overlord interaction</h3>
      <div class="kv">Drive this FACE with overlord privilege. Paste an overlord-session token
        (from <code>POST /overlord/verify</code>) or pass <code>?overlord=&lt;token&gt;</code>.</div>
      <input id="ovl-token" placeholder="overlord-session token (Bearer JWT)" value="${initialToken}"/>
      <div style="margin-top:8px">
        ${EXPRESSIONS.map((e) => `<button data-expr="${e}">${e}</button>`).join('')}
      </div>
      <div style="margin-top:6px">
        <button id="ovl-override">override → sovereign</button>
        <button id="ovl-metamask">login via MetaMask</button>
      </div>
      <div id="ovl-status"></div>
    </div>
  </div>
</div>
<script type="module">
  import { Faicey } from '/static/vendor/faicey-engine.js';
  const canvas = document.getElementById('face');
  const c = canvas.parentElement;
  const faicey = new Faicey();
  await faicey.init(canvas, {
    width: c.clientWidth, height: c.clientHeight,
    wireframe: ${o.wireframe ?? true}, renderMode: 'wireframe',
    faceColor: ${o.faceColor ?? 0x00ff88},
    backgroundColor: ${o.backgroundColor ?? 0x05060a},
    wireframeThickness: ${o.wireframeThickness ?? 1},
    cameraZ: ${o.cameraZ ?? 5},
  });
  faicey.setExpression(${JSON.stringify(profile.expression)}, ${profile.intensity});
  // gentle idle rotation so the FACE reads as alive
  const r = faicey.getRenderer();
  let a = 0; setInterval(() => { a += 0.01; r && r.setRotation(0, Math.sin(a) * 0.3, 0); }, 33);

  // ---- overlord interaction (drive the FACE with overlord privilege) ----
  const AGENT = ${JSON.stringify(agentId)};
  const tokenInput = document.getElementById('ovl-token');
  const status = document.getElementById('ovl-status');
  const setStatus = (msg, ok) => { status.textContent = msg; status.style.color = ok ? '#0f8' : '#f88'; };

  async function interact(payload) {
    const token = tokenInput.value.trim();
    if (!token) { setStatus('paste an overlord-session token first', false); return null; }
    const res = await fetch('/api/faice/' + encodeURIComponent(AGENT) + '/interact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setStatus('✗ ' + (data.message || res.status), false); return null; }
    return data;
  }

  document.querySelectorAll('.ovl button[data-expr]').forEach((b) => {
    b.onclick = async () => {
      const expr = b.getAttribute('data-expr');
      const data = await interact({ action: 'setExpression', expression: expr, intensity: 1.0 });
      if (data) {
        faicey.setExpression(expr, 1.0);
        document.getElementById('cur-expr').textContent = expr;
        document.getElementById('cur-int').textContent = '1.00';
        setStatus('✓ ' + data.by.role + ' set expression → ' + expr, true);
      }
    };
  });

  document.getElementById('ovl-override').onclick = async () => {
    const data = await interact({ action: 'override', overrides: { reputation: 60000 } });
    if (data) {
      const p = data.descriptor;
      faicey.setExpression(p.face.expression, p.face.intensity);
      setStatus('✓ overlord override → rank ' + p.privilege.rank + ' (' + p.face.faceColorHex + '; reload to recolor)', true);
    }
  };

  document.getElementById('ovl-metamask').onclick = async () => {
    if (!window.ethereum) { setStatus('no wallet (MetaMask) detected', false); return; }
    try {
      const [addr] = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const ch = await fetch('/overlord/challenge', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, scope: 'overlord.session' }),
      });
      if (!ch.ok) { setStatus('overlord backend not reachable (' + ch.status + ')', false); return; }
      const { nonce, message } = await ch.json();
      const signature = await window.ethereum.request({ method: 'personal_sign', params: [message, addr] });
      const vr = await fetch('/overlord/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nonce, signature }),
      });
      const v = await vr.json();
      if (v.overlord_token) { tokenInput.value = v.overlord_token; setStatus('✓ logged in as ' + v.role + ' (' + addr.slice(0,8) + '…)', true); }
      else setStatus('✗ signature did not grant privilege (role: ' + (v.role || 'public') + ')', false);
    } catch (e) { setStatus('✗ ' + e.message, false); }
  };
</script></body></html>`;
}
