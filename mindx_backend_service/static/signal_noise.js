/* signal_noise.js — mindX signal/noise depth tiering (shared, progressive enhancement)
 *
 * Doctrine: "truth, and its repair, instead of hiding it. Warts-and-all."
 * So this NEVER deletes content — it tiers it. The honest verdict + anything
 * currently alerting stay visible (signal); exhaustive detail collapses one or
 * two clicks deeper (noise, on demand).
 *
 * Auto-adapts to two page shapes, additively, after DOM ready:
 *   A. feedback-style — >=3  <section id="sec-*">  → wrap into Essential/Detailed/
 *      Advanced tiers, each section its own accordion, live pill mirrored to summary.
 *   B. dashboard-style — togglable .section-hdr[onclick] → add a depth toolbar that
 *      drives the existing toggleSec accordions (skips display:none always-on headers).
 *
 * Per-page config (optional), set BEFORE this script loads:
 *   window.SN_CONFIG = { tiers:{ 'sec-foo':'ess', 'sec-bar':'adv', ... }, persist:true }
 * Unmapped sections fall back to 'detail'. The card-populating JS is untouched —
 * it uses getElementById, which survives DOM re-parenting.
 */
(function () {
  'use strict';
  var CFG = window.SN_CONFIG || {};
  var TIERMAP = CFG.tiers || {};
  var PERSIST = CFG.persist !== false;
  var PFX = 'sn:' + location.pathname + ':';
  var TIERS = [
    { key: 'ess',    label: 'ESSENTIAL — the honest verdict', cls: 'sn-ess', open: true,  note: 'always-on signal' },
    { key: 'detail', label: 'DETAILED — operational watch',   cls: '',       open: false, note: 'one click deeper' },
    { key: 'adv',    label: 'ADVANCED — deep internals',      cls: 'sn-adv', open: false, note: 'full warts-and-all' }
  ];
  var ALERT_RE = /\b(fail|failing|failed|stuck|error|errors|err|stall|stalled|down|offline|critical|broken|dead|timeout)\b|✗|⚠/i;

  function $all(s, r) { return [].slice.call((r || document).querySelectorAll(s)); }
  function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function ready(fn) { document.readyState !== 'loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }
  function lsGet(k) { try { return localStorage.getItem(PFX + k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(PFX + k, v); } catch (e) {} }

  function pillAlert(pill) {
    if (!pill) return false;
    if (ALERT_RE.test(pill.textContent || '')) return true;
    try {
      var m = getComputedStyle(pill).color.match(/\d+/g);
      if (m) { var r = +m[0], g = +m[1], b = +m[2]; if (r > 180 && g < 115 && b < 115) return true; } // reddish
    } catch (e) {}
    return false;
  }

  function titleOf(sec) {
    var h = sec.querySelector('.sec-head h2') || sec.querySelector('h2') || sec.querySelector('h3');
    if (!h) return sec.id;
    var c = h.cloneNode(true), p = c.querySelector('.pill'); if (p) p.remove();
    return (c.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function injectCSS() {
    if (document.getElementById('sn-css')) return;
    var css = [
      '.sn-toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0;font-family:var(--mono);font-size:11px;align-items:center}',
      '.sn-toolbar .sn-tt{color:var(--text3);margin-right:4px;letter-spacing:.1em;text-transform:uppercase}',
      '.sn-toolbar button{cursor:pointer;background:var(--surface2);border:1px solid var(--border);color:var(--text2);padding:5px 11px;border-radius:6px;font-family:var(--mono);font-size:11px;transition:.15s}',
      '.sn-toolbar button:hover{color:var(--blue);border-color:rgba(121,192,255,.35)}',
      '.sn-toolbar button.sn-on{color:var(--green);border-color:rgba(86,211,100,.4)}',
      '.sn-tier{margin:0 0 12px;border:1px solid var(--border);border-radius:10px;background:var(--surface2);overflow:hidden}',
      '.sn-tier>summary{cursor:pointer;list-style:none;padding:13px 16px;display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12px;letter-spacing:.6px;color:var(--violet);user-select:none}',
      '.sn-tier>summary::-webkit-details-marker{display:none}',
      '.sn-tier>summary .sn-caret{transition:transform .18s;color:var(--text3);font-size:11px}',
      '.sn-tier[open]>summary .sn-caret{transform:rotate(90deg)}',
      '.sn-tier>summary .sn-label{font-weight:700}',
      '.sn-tier>summary .sn-meta{color:var(--text3);font-weight:400;margin-left:auto;display:flex;gap:8px;align-items:center}',
      '.sn-tier>summary .sn-alert{color:var(--red);font-weight:700}',
      '.sn-ess>summary{color:var(--green)}',
      '.sn-adv>summary{color:var(--amber)}',
      '.sn-tier-body{padding:8px 14px 14px}',
      '.sn-sec{margin:8px 0;border:1px solid var(--border);border-radius:8px;background:var(--surface);overflow:hidden}',
      '.sn-sec.sn-alerting{border-color:rgba(248,81,73,.45)}',
      '.sn-sec>summary{cursor:pointer;list-style:none;padding:10px 14px;display:flex;align-items:center;gap:9px;font-family:var(--mono);font-size:13px;color:var(--text);user-select:none}',
      '.sn-sec>summary::-webkit-details-marker{display:none}',
      '.sn-sec>summary .sn-caret{transition:transform .18s;color:var(--text3);font-size:11px}',
      '.sn-sec[open]>summary .sn-caret{transform:rotate(90deg)}',
      '.sn-sec>summary .sn-title{font-weight:600}',
      '.sn-sec>summary .sn-stat{margin-left:auto;font-size:10px;font-family:var(--mono);padding:1px 8px;border-radius:10px;border:1px solid var(--border);color:var(--text3);white-space:nowrap}',
      '.sn-sec .sn-body{padding:2px 12px 10px}',
      '.sn-sec .sn-body>section{margin:0!important}',
      '.sn-sec .sn-body .sec-head{border-bottom:none;margin-bottom:8px}',
      /* station tuner — signal(mindx) / learn(docs+book) / noise(rage) */
      '.sn-tuner{margin-left:auto;display:flex;align-items:center;gap:0;border:1px solid var(--border);border-radius:8px;overflow:hidden;font-family:var(--mono);font-size:10.5px}',
      '.sn-tuner .sn-st{display:flex;align-items:center;gap:6px;padding:5px 12px;color:var(--text3);text-decoration:none;letter-spacing:.12em;text-transform:uppercase;border-right:1px solid var(--border);transition:.15s;white-space:nowrap}',
      '.sn-tuner .sn-st:last-child{border-right:none}',
      '.sn-tuner .sn-st .sn-dest{font-size:9px;letter-spacing:.04em;text-transform:none;opacity:.6}',
      '.sn-tuner a.sn-st:hover{background:var(--surface);color:var(--text)}',
      '.sn-tuner .sn-here{color:var(--green);cursor:default;background:rgba(86,211,100,.07)}',
      '.sn-tuner .sn-here .sn-wave{color:var(--green)}',
      '.sn-tuner .sn-learn:hover{color:var(--blue)}',
      '.sn-tuner .sn-learnmain{color:inherit;text-decoration:none}',
      '.sn-tuner .sn-learn:hover .sn-learnmain{color:var(--blue)}',
      '.sn-tuner a.sn-noise:hover{color:var(--amber);box-shadow:inset 0 -2px 0 var(--amber)}',
      '.sn-tuner .sn-sep{opacity:.4;padding:0 2px}',
      '.sn-tuner a.sn-sub{color:var(--text3);text-decoration:none}',
      '.sn-tuner a.sn-sub:hover{color:var(--blue)}'
    ].join('');
    var st = document.createElement('style'); st.id = 'sn-css'; st.textContent = css;
    document.head.appendChild(st);
  }

  // ── Generic tiering: works for <section id="sec-*"> (Pattern A) and any
  //    configured selector with a data-sn tier attribute (Pattern C). ──
  function enhanceItems(secs, tierOf) {
    var anchor = secs[0], parent = anchor.parentNode, bodies = {};
    TIERS.forEach(function (t) {
      var d = document.createElement('details');
      d.className = 'sn-tier ' + t.cls; if (t.open) d.open = true;
      d.dataset.tier = t.key;
      d.innerHTML = '<summary><span class="sn-caret">▸</span><span class="sn-label">' + t.label +
        '</span><span class="sn-meta"><span class="sn-count"></span><span class="sn-alert"></span>' +
        '<span class="sn-note">' + t.note + '</span></span></summary>' +
        '<div class="sn-tier-body" data-body="' + t.key + '"></div>';
      bodies[t.key] = d.querySelector('.sn-tier-body');
      parent.insertBefore(d, anchor);
    });

    function rollup() {
      TIERS.forEach(function (t) {
        var box = document.querySelector('.sn-tier[data-tier="' + t.key + '"]');
        if (!box) return;
        var kids = $all('.sn-sec', box), alerts = kids.filter(function (s) { return s.classList.contains('sn-alerting'); }).length;
        box.style.display = kids.length ? '' : 'none';   // hide an empty tier
        box.querySelector('.sn-count').textContent = kids.length + ' item' + (kids.length === 1 ? '' : 's');
        box.querySelector('.sn-alert').textContent = alerts ? ('● ' + alerts + ' alert' + (alerts === 1 ? '' : 's')) : '';
        if (alerts && !box.open) box.open = true;        // problems force their tier open
      });
    }

    secs.forEach(function (sec, i) {
      var tier = tierOf(sec) || 'detail';
      var det = document.createElement('details');
      det.className = 'sn-sec'; det.dataset.sid = sec.id || ('sn-' + i); det.dataset.tier = tier;
      var persisted = PERSIST ? lsGet(sec.id) : null;
      det.open = persisted != null ? persisted === '1' : (tier === 'ess');
      det.innerHTML = '<summary><span class="sn-caret">▸</span><span class="sn-title">' +
        esc(titleOf(sec)) + '</span><span class="sn-stat" data-stat>—</span></summary><div class="sn-body"></div>';
      det.querySelector('.sn-body').appendChild(sec);    // move live node — getElementById still works
      bodies[tier].appendChild(det);

      if (PERSIST) det.addEventListener('toggle', function () { lsSet(sec.id, det.open ? '1' : '0'); });

      var pill = sec.querySelector('.pill'), stat = det.querySelector('[data-stat]');
      var sync = function () {
        if (pill) {
          stat.textContent = (pill.textContent || '').replace(/\s+/g, ' ').trim() || '—';
          try { stat.style.color = getComputedStyle(pill).color; } catch (e) {}
        }
        var alerting = pillAlert(pill);
        det.classList.toggle('sn-alerting', alerting);
        if (alerting) det.open = true;                   // surface the problem
        rollup();
      };
      sync();
      if (pill) { try { new MutationObserver(sync).observe(pill, { childList: true, characterData: true, subtree: true, attributes: true }); } catch (e) {} }
    });
    rollup();
    addToolbar(parent, parent.querySelector('.sn-tier'), 'A');
  }

  // ── Pattern B: dashboard-style .section-hdr[onclick] + toggleSec ──
  function togglableHdrs() {
    return $all('.section-hdr[onclick]').filter(function (h) { return h.style.display !== 'none'; });
  }
  function setOpen(hdr, open) {
    var body = hdr.nextElementSibling, isOpen = hdr.classList.contains('open');
    if (open && !isOpen) {
      hdr.classList.add('open');
      if (body) { body.classList.add('open'); if (window._refreshSec) { try { _refreshSec(body.id); } catch (e) {} } }
    } else if (!open && isOpen) {
      hdr.classList.remove('open'); if (body) body.classList.remove('open');
    }
  }
  function enhanceToggle() {
    var anchor = document.getElementById('L1b') || document.querySelector('.layer') || document.querySelector('.section-hdr');
    if (!anchor || !anchor.parentNode) return;
    togglableHdrs().forEach(function (h) { if (ALERT_RE.test(h.textContent || '')) setOpen(h, true); }); // problems auto-open
    addToolbar(anchor.parentNode, anchor, 'B');
  }

  function addToolbar(parent, before, mode) {
    var bar = document.createElement('div'); bar.className = 'sn-toolbar';
    // Left: depth filter over THIS page's signal. Right: the station tuner —
    // signal/noise is a radio metaphor. You are tuned to SIGNAL (mindx.pythai.net,
    // the live machine); LEARN is the reference station (docs + the book); NOISE
    // is the broadcast (rage.pythai.net, mindX's published voice).
    // Depth filter only on tiered pages (Pattern A). The dashboard landing page
    // (Pattern B) is kept ALL SIGNAL — no depth option — just the station tuner.
    var depth = (mode === 'A')
      ? '<span class="sn-tt">depth</span>' +
        '<button data-act="ess">signal only</button>' +
        '<button data-act="all">expand all</button>' +
        '<button data-act="none">collapse all</button>'
      : '';
    bar.innerHTML = depth +
      '<nav class="sn-tuner" aria-label="stations">' +
        '<span class="sn-st sn-here" title="You are tuned to SIGNAL — the live mindX machine">' +
          '<span class="sn-wave">◉</span> signal<span class="sn-dest">mindx.pythai.net</span></span>' +
        '<span class="sn-st sn-learn" title="The reference station — documentation and the Book of mindX">' +
          '▤ <a class="sn-sub sn-learnmain" href="/docs.html">learn</a>' +
          '<span class="sn-dest"><a class="sn-sub" href="/docs.html">docs</a>' +
          '<span class="sn-sep">·</span><a class="sn-sub" href="/book">book</a></span></span>' +
        '<a class="sn-st sn-noise" href="https://rage.pythai.net" rel="noopener" title="The broadcast — mindX&apos;s published voice on rage.pythai.net">' +
          '◴ noise<span class="sn-dest">rage.pythai.net ↗</span></a>' +
      '</nav>';
    parent.insertBefore(bar, before);
    bar.addEventListener('click', function (e) {
      var a = e.target.getAttribute && e.target.getAttribute('data-act'); if (!a) return;
      if (mode === 'A') {
        $all('.sn-tier').forEach(function (t) { t.open = (a === 'all') || (a === 'ess' && t.dataset.tier === 'ess'); });
        $all('.sn-sec').forEach(function (s) {
          if (s.classList.contains('sn-alerting')) { s.open = true; return; }   // never bury an alert
          s.open = (a === 'all') ? true : (a === 'none') ? false : (s.dataset.tier === 'ess');
          if (PERSIST) lsSet(s.dataset.sid, s.open ? '1' : '0');
        });
      } else {
        togglableHdrs().forEach(function (h) {
          if (ALERT_RE.test(h.textContent || '')) { setOpen(h, true); return; }
          setOpen(h, a === 'all' ? true : a === 'none' ? false : h.id === 'hdr-selfdiag');
        });
      }
      $all('button', bar).forEach(function (b) { b.classList.toggle('sn-on', b.getAttribute('data-act') === a); });
    });
  }

  ready(function () {
    injectCSS();
    var secs = $all('section[id^="sec-"]');
    if (secs.length >= 3) { enhanceItems(secs, function (el) { return TIERMAP[el.id] || 'detail'; }); return; }
    if (CFG.selector) {                                   // Pattern C: configured selector + data-sn tiers
      var items = $all(CFG.selector);
      if (items.length >= 2) { enhanceItems(items, function (el) { return el.getAttribute('data-sn') || TIERMAP[el.id] || 'detail'; }); return; }
    }
    if (togglableHdrs().length >= 2) { enhanceToggle(); }
  });
})();
