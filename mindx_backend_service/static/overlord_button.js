/* overlord_button.js — the OVERLORD panel (handoff surface)
 *
 * Sibling of builder_button.js, but OVERLORD-gated. A floating control that
 * EMERGES bottom-left and, on hover/focus, reveals the IMMEDIATE LIST OF LIVE
 * CONTRACT DEPLOYMENTS (the handoff) read from /static/overlord_deployments.json.
 *
 * Mint / deploy authority is OVERLORD-ONLY at this time:
 *   - OVERLORD = bankon.eth (0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169) — sole
 *     mint + real-chain deploy authority. An agent cannot sign mainnet.
 *   - OVERSEER = mindx.algo (PARSEC / Algorand).
 * Public participant mint authority is NOT granted yet. The mint button's
 * privilege flips from the OVERLORD hierarchy: it enables only when the connected
 * wallet IS the OVERLORD; otherwise it is disabled with the hierarchy note.
 *
 * Self-contained: injects its own CSS, no assets. Doctrine: cyberpunk-2048,
 * monospace, OVERLORD gold (#e3b341), the dashboard's own CSS vars.
 */
(function () {
  'use strict';
  if (window.__mindx_overlord) return; window.__mindx_overlord = true;

  var OVERLORD = '0x10f7ee226b16bea7f365dc1edef159fc1957d169'; // bankon.eth (lowercased for compare)
  var DATA_URL = '/static/overlord_deployments.json';

  function short(a) { return a ? a.slice(0, 6) + '…' + a.slice(-4) : ''; }

  function connectedOverlord() {
    try {
      var eth = window.ethereum;
      var acct = eth && (eth.selectedAddress || (eth._state && eth._state.accounts && eth._state.accounts[0]));
      return acct && acct.toLowerCase() === OVERLORD;
    } catch (e) { return false; }
  }

  function injectCSS() {
    if (document.getElementById('mxo-css')) return;
    var css = [
      '@keyframes mxo-emerge{0%{opacity:0;transform:translateY(14px) scale(.7)}60%{opacity:1;transform:translateY(-3px) scale(1.04)}100%{opacity:1;transform:translateY(0) scale(1)}}',
      '@keyframes mxo-halo{0%,100%{box-shadow:0 0 0 0 rgba(227,179,65,0),0 4px 22px rgba(0,0,0,.5)}50%{box-shadow:0 0 0 4px rgba(227,179,65,.10),0 4px 26px rgba(0,0,0,.6)}}',
      '@keyframes mxo-item{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}',
      '.mxo-wrap{position:fixed;left:20px;bottom:20px;z-index:70;font-family:var(--mono,monospace)}',
      '.mxo-btn{display:flex;align-items:center;gap:9px;cursor:pointer;background:linear-gradient(135deg,rgba(30,24,10,.96),rgba(14,14,12,.96));' +
        'border:1px solid rgba(227,179,65,.5);color:var(--text,#e6edf3);padding:11px 16px;border-radius:12px;font-size:12.5px;' +
        'letter-spacing:.18em;text-transform:uppercase;font-weight:700;animation:mxo-emerge .7s cubic-bezier(.2,1.1,.3,1) both,mxo-halo 3.6s ease-in-out 1s infinite}',
      '.mxo-btn .mxo-crown{font-size:13px;filter:drop-shadow(0 0 8px rgba(227,179,65,.6))}',
      '.mxo-btn .mxo-tag{font-size:8.5px;letter-spacing:.1em;text-transform:none;color:var(--text3,#7d8590);font-weight:400;margin-left:2px}',
      '.mxo-btn:hover{border-color:rgba(227,179,65,.85);color:#fff}',
      '.mxo-menu{position:absolute;left:0;bottom:calc(100% + 10px);width:320px;background:rgba(10,10,14,.98);border:1px solid var(--border,#30363d);' +
        'border-radius:12px;overflow:hidden;opacity:0;visibility:hidden;transform:translateY(8px);transition:.18s;box-shadow:0 12px 40px rgba(0,0,0,.6)}',
      '.mxo-wrap:hover .mxo-menu,.mxo-wrap:focus-within .mxo-menu{opacity:1;visibility:visible;transform:translateY(0)}',
      '.mxo-head{padding:11px 14px 9px;border-bottom:1px solid var(--border,#30363d);display:flex;align-items:baseline;justify-content:space-between}',
      '.mxo-head .mxo-h{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:#e3b341;font-weight:700}',
      '.mxo-head .mxo-sub{font-size:8.5px;color:var(--text3,#7d8590);letter-spacing:.04em}',
      '.mxo-id{padding:8px 14px;font-size:9px;color:var(--text3,#7d8590);border-bottom:1px solid rgba(48,54,61,.5);line-height:1.6}',
      '.mxo-id b{color:#e3b341;font-weight:700}',
      '.mxo-item{display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:1px solid rgba(48,54,61,.5);opacity:0}',
      '.mxo-wrap:hover .mxo-item,.mxo-wrap:focus-within .mxo-item{animation:mxo-item .28s ease both}',
      '.mxo-item:last-child{border-bottom:none}',
      '.mxo-dot{flex:0 0 auto;width:7px;height:7px;border-radius:50%}',
      '.mxo-dot.live{background:#56d364;box-shadow:0 0 8px #56d364}',
      '.mxo-dot.pending{background:#e3b341;box-shadow:0 0 8px rgba(227,179,65,.6)}',
      '.mxo-meta{flex:1 1 auto;min-width:0}',
      '.mxo-name{font-size:11.5px;font-weight:600;color:var(--text,#e6edf3)}',
      '.mxo-addr{font-size:9px;color:var(--text3,#7d8590);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.mxo-badge{flex:0 0 auto;font-size:8px;letter-spacing:.05em;text-transform:uppercase;padding:2px 6px;border-radius:4px}',
      '.mxo-badge.live{color:#56d364;border:1px solid rgba(86,211,100,.35)}',
      '.mxo-badge.pending{color:#e3b341;border:1px solid rgba(227,179,65,.35)}',
      '.mxo-mint{display:block;margin:10px 14px;padding:10px;text-align:center;border-radius:8px;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border:1px solid rgba(227,179,65,.5);color:#e3b341;background:rgba(227,179,65,.06);cursor:pointer;text-decoration:none}',
      '.mxo-mint.locked{color:var(--text3,#7d8590);border-color:var(--border,#30363d);background:rgba(125,133,144,.05);cursor:not-allowed}',
      '.mxo-mint:not(.locked):hover{background:rgba(227,179,65,.14);color:#fff}',
      '.mxo-foot{padding:8px 14px;font-size:8.5px;color:var(--text3,#7d8590);letter-spacing:.03em;border-top:1px solid var(--border,#30363d);text-align:center;line-height:1.6}',
      '@media (prefers-reduced-motion: reduce){.mxo-btn{animation:none}.mxo-item{opacity:1;animation:none!important}}'
    ].join('');
    var st = document.createElement('style'); st.id = 'mxo-css'; st.textContent = css;
    document.head.appendChild(st);
  }

  function render(data) {
    if (document.querySelector('.mxo-wrap')) return;  // idempotent
    injectCSS();
    var h = (data && data.hierarchy) || {};
    var deps = (data && data.deployments) || [];
    var isOverlord = connectedOverlord();

    var rows = deps.map(function (d, i) {
      var live = !!d.live, cls = live ? 'live' : 'pending';
      return '<div class="mxo-item" style="animation-delay:' + (i * 0.035) + 's">' +
        '<span class="mxo-dot ' + cls + '"></span>' +
        '<span class="mxo-meta"><span class="mxo-name">' + d.name + '</span>' +
        '<span class="mxo-addr" title="' + (d.address || 'address TBD') + '">' +
          (d.address ? short(d.address) : 'addr TBD') + ' &middot; ' + (d.blurb || '') + '</span></span>' +
        '<span class="mxo-badge ' + cls + '">' + (live ? 'live' : 'predicted') + '</span></div>';
    }).join('');

    // Mint button — privilege flips from the OVERLORD hierarchy.
    var mint = isOverlord
      ? '<a class="mxo-mint" href="https://deltaverse.pythai.net/pages/deployer.html" target="_blank" rel="noopener" ' +
          'title="OVERLORD recognized — sign the CREATE2 deploy">◈ mint / sign deploy</a>'
      : '<span class="mxo-mint locked" title="Mint authority is OVERLORD-only at this time. Public participant mint is issued when the OVERLORD hierarchy flips this button.">◈ mint — OVERLORD only</span>';

    var ov = h.OVERLORD || {}, os = h.OVERSEER || {};
    var wrap = document.createElement('div'); wrap.className = 'mxo-wrap';
    wrap.innerHTML =
      '<div class="mxo-menu" role="menu" aria-label="OVERLORD — live contract deployments">' +
        '<div class="mxo-head"><span class="mxo-h">♛ Overlord</span>' +
        '<span class="mxo-sub">live deployments &middot; handoff</span></div>' +
        '<div class="mxo-id">OVERLORD <b>' + (ov.id || 'bankon.eth') + '</b> &middot; ' + short(ov.address || '') + '<br>' +
          'OVERSEER <b>' + (os.id || 'mindx.algo') + '</b> &middot; ' + (os.wallet || 'PARSEC') + '</div>' +
        rows +
        mint +
        '<div class="mxo-foot">' + (isOverlord ? 'OVERLORD recognized — mint authority active' :
          'public mint not yet granted — authority issued by the OVERLORD hierarchy') + '</div>' +
      '</div>' +
      '<button class="mxo-btn" type="button" aria-haspopup="true" aria-label="OVERLORD — live contract deployments">' +
        '<span class="mxo-crown">♛</span> Overlord <span class="mxo-tag">deployments</span>' +
      '</button>';
    document.body.appendChild(wrap);
  }

  function build() {
    fetch(DATA_URL, { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { render(data || { deployments: [] }); })
      .catch(function () { render({ deployments: [] }); });
  }

  if (document.readyState !== 'loading') build();
  else document.addEventListener('DOMContentLoaded', build);
})();
