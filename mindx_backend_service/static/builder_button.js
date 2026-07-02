/* builder_button.js — the BUILDER emergence (shared, progressive enhancement)
 *
 * A floating BUILDER control that EMERGES onto the page after load, then on
 * hover/focus reveals the seven mindX archetypes — each a persona role
 * (expert/worker/meta/community/marketing/development/governance) carrying its
 * own wireframe avatar. Selecting one opens the iNFT builder (/inft) seeded with
 * that archetype, so the avatar is born compatible with AgenticPlace iNFT
 * minting (IntelligenceConfig: agent, autonomous, behavior, intelligenceLevel).
 *
 * Self-contained: injects its own CSS + inline-SVG avatars (no API, no assets).
 * Doctrine match: cyberpunk-2048, monospace, the dashboard's own CSS vars.
 */
(function () {
  'use strict';
  if (window.__mindx_builder) return; window.__mindx_builder = true;

  // Archetypes + avatar come from the shared SSOT (/static/archetypes.js) when
  // present, so the BUILDER and the /inft mint page never drift. Embedded
  // fallback keeps the button working if archetypes.js failed to load.
  var ARCHETYPES = window.MINDX_ARCHETYPES || [
    { key: 'expert',      label: 'Expert',      glyph: '◈', accent: '#bc8cff', lvl: 88, auto: false, blurb: 'deep domain reasoning' },
    { key: 'meta',        label: 'Meta',        glyph: '✦', accent: '#56d364', lvl: 92, auto: true,  blurb: 'reasons about reasoning' },
    { key: 'development', label: 'Development', glyph: '⌬', accent: '#79c0ff', lvl: 80, auto: true,  blurb: 'builds and ships code' },
    { key: 'worker',      label: 'Worker',      glyph: '⬡', accent: '#39d3c8', lvl: 60, auto: false, blurb: 'executes bounded tasks' },
    { key: 'governance',  label: 'Governance',  glyph: '⬢', accent: '#e3b341', lvl: 75, auto: false, blurb: 'decides, votes, vetoes' },
    { key: 'community',   label: 'Community',   glyph: '◉', accent: '#f0883e', lvl: 55, auto: false, blurb: 'engages participants' },
    { key: 'marketing',   label: 'Marketing',   glyph: '◴', accent: '#f85149', lvl: 50, auto: false, blurb: 'broadcasts the voice' }
  ];

  var avatarSVG = window.mindxAvatarSVG || function (a, size) {
    size = size || 30;
    var c = size / 2, r = c - 2, nodes = '';
    for (var i = 0; i < 6; i++) {
      var ang = (Math.PI / 3) * i - Math.PI / 2;
      var x = c + Math.cos(ang) * r, y = c + Math.sin(ang) * r;
      nodes += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="1.4" fill="' + a.accent + '"/>';
      var nx = c + Math.cos(ang) * (r - 1), ny = c + Math.sin(ang) * (r - 1);
      nodes += '<line x1="' + c + '" y1="' + c + '" x2="' + nx.toFixed(1) + '" y2="' + ny.toFixed(1) +
               '" stroke="' + a.accent + '" stroke-width="0.5" opacity="0.35"/>';
    }
    var hex = '';
    for (var j = 0; j < 6; j++) {
      var ag = (Math.PI / 3) * j - Math.PI / 2;
      hex += (c + Math.cos(ag) * r).toFixed(1) + ',' + (c + Math.sin(ag) * r).toFixed(1) + ' ';
    }
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
      '<polygon points="' + hex.trim() + '" fill="none" stroke="' + a.accent + '" stroke-width="1" opacity="0.7"/>' +
      nodes +
      '<text x="' + c + '" y="' + (c + 0.5) + '" text-anchor="middle" dominant-baseline="central" ' +
      'font-size="' + (size * 0.42) + '" fill="' + a.accent + '">' + a.glyph + '</text></svg>';
  };

  function injectCSS() {
    if (document.getElementById('mxb-css')) return;
    var css = [
      '@keyframes mxb-emerge{0%{opacity:0;transform:translateY(14px) scale(.7)}60%{opacity:1;transform:translateY(-3px) scale(1.04)}100%{opacity:1;transform:translateY(0) scale(1)}}',
      '@keyframes mxb-halo{0%,100%{box-shadow:0 0 0 0 rgba(188,140,255,.0),0 4px 22px rgba(0,0,0,.5)}50%{box-shadow:0 0 0 4px rgba(188,140,255,.10),0 4px 26px rgba(0,0,0,.6)}}',
      '@keyframes mxb-item{from{opacity:0;transform:translateX(8px)}to{opacity:1;transform:translateX(0)}}',
      '.mxb-wrap{position:fixed;right:20px;bottom:20px;z-index:70;font-family:var(--mono,monospace)}',
      '.mxb-btn{display:flex;align-items:center;gap:9px;cursor:pointer;background:linear-gradient(135deg,rgba(20,16,30,.96),rgba(12,14,20,.96));' +
        'border:1px solid rgba(188,140,255,.45);color:var(--text,#e6edf3);padding:11px 16px;border-radius:12px;font-size:12.5px;' +
        'letter-spacing:.18em;text-transform:uppercase;font-weight:700;animation:mxb-emerge .7s cubic-bezier(.2,1.1,.3,1) both,mxb-halo 3.6s ease-in-out 1s infinite}',
      '.mxb-btn .mxb-spark{width:9px;height:9px;border-radius:50%;background:var(--violet,#bc8cff);box-shadow:0 0 10px var(--violet,#bc8cff)}',
      '.mxb-btn .mxb-tag{font-size:8.5px;letter-spacing:.1em;text-transform:none;color:var(--text3,#7d8590);font-weight:400;margin-left:2px}',
      '.mxb-btn:hover{border-color:rgba(188,140,255,.8);color:#fff}',
      '.mxb-menu{position:absolute;right:0;bottom:calc(100% + 10px);width:288px;background:rgba(10,12,18,.98);border:1px solid var(--border,#30363d);' +
        'border-radius:12px;overflow:hidden;opacity:0;visibility:hidden;transform:translateY(8px);transition:.18s;box-shadow:0 12px 40px rgba(0,0,0,.6)}',
      '.mxb-wrap:hover .mxb-menu,.mxb-wrap:focus-within .mxb-menu{opacity:1;visibility:visible;transform:translateY(0)}',
      '.mxb-head{padding:11px 14px 9px;border-bottom:1px solid var(--border,#30363d);display:flex;align-items:baseline;justify-content:space-between}',
      '.mxb-head .mxb-h{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--violet,#bc8cff);font-weight:700}',
      '.mxb-head .mxb-sub{font-size:8.5px;color:var(--text3,#7d8590);letter-spacing:.04em}',
      '.mxb-item{display:flex;align-items:center;gap:11px;padding:9px 14px;text-decoration:none;color:var(--text2,#c9d1d9);border-bottom:1px solid rgba(48,54,61,.5);transition:.13s;opacity:0}',
      '.mxb-wrap:hover .mxb-item,.mxb-wrap:focus-within .mxb-item{animation:mxb-item .28s ease both}',
      '.mxb-item:last-child{border-bottom:none}',
      '.mxb-item:hover{background:rgba(188,140,255,.06)}',
      '.mxb-av{flex:0 0 auto;line-height:0;filter:drop-shadow(0 0 4px rgba(0,0,0,.4))}',
      '.mxb-meta{flex:1 1 auto;min-width:0}',
      '.mxb-name{font-size:12px;font-weight:600;color:var(--text,#e6edf3);text-transform:capitalize}',
      '.mxb-blurb{font-size:9.5px;color:var(--text3,#7d8590);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.mxb-lvl{flex:0 0 auto;font-size:9px;color:var(--text3,#7d8590)}',
      '.mxb-item:hover .mxb-go{color:var(--text)}',
      '.mxb-go{flex:0 0 auto;font-size:11px;color:var(--text3,#7d8590);transition:.13s}',
      '.mxb-foot{padding:8px 14px;font-size:8.5px;color:var(--text3,#7d8590);letter-spacing:.03em;border-top:1px solid var(--border,#30363d);text-align:center}',
      '.mxb-foot a{color:var(--violet,#bc8cff);text-decoration:none}',
      '.mxb-lock .mxb-name,.mxb-lock .mxb-blurb{opacity:.55}',
      '.mxb-lock .mxb-av{opacity:.4;filter:grayscale(.5)}',
      '.mxb-lock:hover .mxb-name,.mxb-lock:hover .mxb-blurb,.mxb-lock:hover .mxb-av{opacity:1;filter:none}',
      '@media (prefers-reduced-motion: reduce){.mxb-btn{animation:none}.mxb-item{opacity:1;animation:none!important}}'
    ].join('');
    var st = document.createElement('style'); st.id = 'mxb-css'; st.textContent = css;
    document.head.appendChild(st);
  }

  // Sign-in gate. Public participant access is CORPORATE-tier by default and
  // links stay locked until the visitor signs in. A signed-in participant is
  // recorded in localStorage('mindx_participant') by the sign-in flow, or a
  // connected wallet counts as signed in. Until then, every archetype link is
  // a locked prompt that routes to sign-in — no direct mint/build access.
  function isSignedIn() {
    try {
      if (localStorage.getItem('mindx_participant')) return true;
      var eth = window.ethereum;
      if (eth && (eth.selectedAddress || (eth._state && eth._state.accounts && eth._state.accounts.length))) return true;
    } catch (e) {}
    return false;
  }
  // Corporate public-participant settings — the default tier a new sign-in enters.
  var PARTICIPANT = { tier: 'public', profile: 'corporate', signin: '/login?as=participant&profile=corporate&from=/inft' };

  function build() {
    if (document.querySelector('.mxb-wrap')) return;  // idempotent
    injectCSS();
    var signedIn = isSignedIn();
    var wrap = document.createElement('div'); wrap.className = 'mxb-wrap';
    if (!signedIn) wrap.classList.add('mxb-locked');

    var items = ARCHETYPES.map(function (a, i) {
      // Signed in → /inft seeded with the archetype (born AgenticPlace-iNFT compatible).
      // Not signed in → locked; route to corporate public-participant sign-in.
      var href = signedIn
        ? '/inft?archetype=' + a.key + '&level=' + a.lvl + '&autonomous=' + a.auto + '&profile=' + PARTICIPANT.profile
        : PARTICIPANT.signin;
      var lockCls = signedIn ? '' : ' mxb-lock';
      var title = signedIn ? ('Build a ' + a.label + ' iNFT — ' + a.blurb)
                           : ('Sign in as a public participant (corporate) to build a ' + a.label);
      return '<a class="mxb-item' + lockCls + '" href="' + href + '" title="' + title +
        '" style="animation-delay:' + (i * 0.035) + 's">' +
        '<span class="mxb-av">' + avatarSVG(a) + '</span>' +
        '<span class="mxb-meta"><span class="mxb-name">' + a.label + '</span>' +
        '<span class="mxb-blurb">' + a.blurb + '</span></span>' +
        (signedIn ? '<span class="mxb-lvl">iq ' + a.lvl + '</span><span class="mxb-go">&rarr;</span>'
                  : '<span class="mxb-go" aria-label="locked">&#128274;</span>') +
        '</a>';
    }).join('');

    var foot = signedIn
      ? 'avatars are <a href="/inft">AgenticPlace iNFT</a>-compatible &middot; corporate participant'
      : '<a href="' + PARTICIPANT.signin + '">sign in</a> as a public participant (corporate) to unlock building';

    wrap.innerHTML =
      '<div class="mxb-menu" role="menu" aria-label="Build an agent — choose an archetype">' +
        '<div class="mxb-head"><span class="mxb-h">Archetype</span>' +
        '<span class="mxb-sub">' + (signedIn ? 'choose a soul to forge' : 'sign in to forge') + '</span></div>' +
        items +
        '<div class="mxb-foot">' + foot + '</div>' +
      '</div>' +
      '<button class="mxb-btn" type="button" aria-haspopup="true" aria-label="Builder — forge an agent archetype">' +
        '<span class="mxb-spark"></span> Builder <span class="mxb-tag">' +
        (signedIn ? 'forge an agent' : 'sign in to forge') + '</span>' +
      '</button>';

    document.body.appendChild(wrap);
  }

  if (document.readyState !== 'loading') build();
  else document.addEventListener('DOMContentLoaded', build);
})();
