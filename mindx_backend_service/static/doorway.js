/*!
 * mindX doorway — the unified gate, attached to every surface.
 *
 * Imports the DeltaVerse OVERLORD/OVERSEER recognition (DVWalletIdentity multi-wallet sign-in, vendored at
 * /static/identity.js) and follows DeltaVerse's L1/L2 model: this is COSMETIC client recognition over
 * mindX's real server gate (the JWT-enforced endpoints). The gate is NEUTRAL — it never names OVERLORD or
 * OVERSEER publicly. When the OVERLORD (bankon.eth, EVM) or the OVERSEER (mindx.algo, Algorand/Parsec)
 * signs in, they are recognized and privilege is DELIVERED (accent + reveal + the OVERSEER JWT). Set
 * `window.DOORWAY_FOR` to a minimal phrase of what the surface is for before this script loads.
 */
(function () {
  if (window.__mindxDoorway) return; window.__mindxDoorway = 1;
  var FOR = window.DOORWAY_FOR || '';
  function api() { var h = location; return (h.host.indexOf('localhost') >= 0 || h.host.indexOf('127.') === 0)
    ? 'http://localhost:' + (window.MINDX_BACKEND_PORT || '8000') : h.origin; }

  var el = document.createElement('div');
  el.id = 'mx-doorway';
  el.style.cssText = 'position:fixed;bottom:14px;right:14px;z-index:99999;font:11px ui-monospace,SFMono-Regular,monospace;'
    + 'display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;cursor:pointer;'
    + 'background:rgba(12,14,22,.86);border:1px solid rgba(120,140,200,.22);color:#9aa6c8;'
    + 'backdrop-filter:blur(6px);transition:border-color .5s,color .5s,box-shadow .5s';
  el.innerHTML = '<span id="mx-dw-glyph" style="font-size:13px">&#9672;</span><span id="mx-dw-txt">enter</span>';
  el.title = FOR ? ('this doorway — ' + FOR) : 'connect to enter';

  function mount() { if (!document.getElementById('mx-doorway')) { document.body.appendChild(el); restore(); } }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();

  // delivery of privilege — neutral: an accent + reveal, no public tier label at the gate.
  function deliver(tier, address) {
    if (!tier || tier === 'public' || tier === 'participant') return;
    document.body.setAttribute('data-tier', tier);
    var accent = tier === 'overlord' ? '#ffd166' : tier === 'overseer' ? '#d2a8ff' : '#58a6ff';
    el.style.borderColor = accent; el.style.color = accent; el.style.boxShadow = '0 0 18px ' + accent + '55';
    var g = document.getElementById('mx-dw-glyph'); if (g) g.style.color = accent;
    var t = document.getElementById('mx-dw-txt'); if (t) t.textContent = address ? (address.slice(0, 6) + '…') : 'recognized';
    // reveal privileged affordances declared by the surface (no tier named in the markup either)
    var nodes = document.querySelectorAll('[data-privilege]');
    for (var i = 0; i < nodes.length; i++) {
      var need = (nodes[i].getAttribute('data-privilege') || '').toLowerCase();
      if (!need || need === tier || (need === 'overseer' && tier === 'overlord')) nodes[i].style.display = '';
    }
    // a top hairline — the substrate signal that privilege was delivered (the field intensifies)
    var bar = document.getElementById('mx-dw-bar');
    if (!bar) { bar = document.createElement('div'); bar.id = 'mx-dw-bar';
      bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:2px;z-index:99998;opacity:.85;transition:background .8s'; document.body.appendChild(bar); }
    bar.style.background = 'linear-gradient(90deg,transparent,' + accent + ',transparent)';
  }

  function restore() {
    try { var t = sessionStorage.getItem('mx_tier'), a = sessionStorage.getItem('mx_addr'); if (t) deliver(t, a); } catch (e) {}
  }

  function b64(sig) {
    if (typeof sig === 'string') { return /^[A-Za-z0-9+/=]+$/.test(sig) ? sig : btoa(sig); }
    try { var u = new Uint8Array(sig), s = ''; for (var i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return btoa(s); } catch (e) { return ''; }
  }

  el.addEventListener('click', async function () {
    var txt = document.getElementById('mx-dw-txt'); var prev = txt ? txt.textContent : '';
    if (!window.DVWalletIdentity) { if (txt) txt.textContent = 'loading…'; return; }
    if (txt) txt.textContent = 'connecting…';
    try {
      // multi-wallet connect (DeltaVerse): Algorand/Parsec (the OVERSEER) first, else EVM (the OVERLORD).
      var conn = null;
      try { conn = await window.DVWalletIdentity.connect('parsec'); } catch (e) {}
      if (!conn || !conn.address) { try { conn = await window.DVWalletIdentity.connect('evm'); } catch (e2) {} }
      if (!conn || !conn.address) { if (txt) txt.textContent = prev; return; }
      var addr = conn.address, chain = conn.chain, tier = 'participant';

      if (chain === 'algorand') {
        // full OVERSEER flow — mindX challenge -> Ed25519 sign -> verify -> scope-bound JWT (real privilege)
        var ch = await fetch(api() + '/auth/algorand/challenge').then(function (r) { return r.json(); });
        var sig = await window.DVWalletIdentity.sign(ch.message, conn);
        var v = await fetch(api() + '/auth/algorand/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nonce: ch.nonce, signature: b64(sig), address: addr, wallet: conn.wallet || 'parsec' }) });
        if (v.ok) { var d = await v.json(); tier = 'overseer';
          try { localStorage.setItem('mindx_overseer_jwt', d.jwt); localStorage.setItem('mindx_overseer_address', addr); } catch (e) {} }
      } else if (chain === 'evm') {
        // full OVERLORD flow — mindX challenge -> EIP-191 personal_sign -> verify -> admin JWT (bankon.eth)
        var che = await fetch(api() + '/auth/evm/challenge').then(function (r) { return r.json(); });
        var sige = await window.DVWalletIdentity.sign(che.message, conn);   // EVM → hex signature string
        var ve = await fetch(api() + '/auth/evm/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nonce: che.nonce, signature: (typeof sige === 'string' ? sige : b64(sige)), address: addr }) });
        if (ve.ok) { var de = await ve.json(); tier = 'overlord';
          try { localStorage.setItem('mindx_overlord_jwt', de.jwt); localStorage.setItem('mindx_overlord_address', addr); } catch (e) {} }
      }
      // cosmetic recognition via the hierarchy (fallback when no JWT was minted; the server enforces the real gate)
      if (tier !== 'overseer' && tier !== 'overlord') {
        var rq = chain === 'algorand' ? ('algo=' + encodeURIComponent(addr)) : ('evm=' + encodeURIComponent(addr));
        var h = await fetch(api() + '/insight/hierarchy?' + rq).then(function (r) { return r.json(); }).catch(function () { return null; });
        if (h && h.recognized && h.recognized.tier) tier = h.recognized.tier;
      }
      try { sessionStorage.setItem('mx_tier', tier); sessionStorage.setItem('mx_addr', addr); } catch (e) {}
      deliver(tier, addr);
      if (txt && (tier === 'public' || tier === 'participant')) txt.textContent = 'connected';
    } catch (e) { if (txt) txt.textContent = prev; }
  });
})();
