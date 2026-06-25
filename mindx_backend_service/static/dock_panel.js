/* dock_panel.js — mindX live activity + system panel: dockable, resizable,
 * double-click to expand. Progressive enhancement; self-contained.
 *
 * - Compact "system bar" sits under the page top bar: key vitals + the latest
 *   live public activity message (mindX activity feed).
 * - Double-click / double-tap expands to full system diagnostics + a scrolling
 *   activity feed; double-click again reverts.
 * - Drag the header to dock to any of the 4 sides (top/left/right/bottom) or
 *   float; a vertical resize handle resizes with auto display correction.
 * - Dock side / size / expanded state persist in localStorage.
 * Data: /insight/agentic/activity (public activity) + /diagnostics/live (vitals).
 */
(function () {
  'use strict';
  var LS = 'mindx-dock:' + location.pathname;
  function ls(k, v) { try { return v === undefined ? localStorage.getItem(LS + k) : localStorage.setItem(LS + k, v); } catch (e) { return null; } }
  function ready(fn) { document.readyState !== 'loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }
  function esc(s) { return (s == null ? '' : String(s)).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }

  function css() {
    if (document.getElementById('dock-css')) return;
    var s = document.createElement('style'); s.id = 'dock-css';
    s.textContent = [
      '#mx-dock{position:fixed;z-index:60;background:var(--surface,rgba(12,16,24,.97));border:1px solid var(--border,rgba(121,192,255,.18));',
      'border-radius:10px;box-shadow:0 10px 40px rgba(0,0,0,.5);font-family:var(--mono,ui-monospace,monospace);color:var(--text,#e6edf3);',
      'backdrop-filter:blur(14px);display:flex;flex-direction:column;overflow:hidden;transition:opacity .15s}',
      '#mx-dock.dock-top{top:8px;left:50%;transform:translateX(-50%);width:min(880px,94vw)}',
      '#mx-dock.dock-bottom{bottom:8px;left:50%;transform:translateX(-50%);width:min(880px,94vw)}',
      '#mx-dock.dock-left{top:64px;left:8px;width:320px}',
      '#mx-dock.dock-right{top:64px;right:8px;width:340px}',
      '#mx-dock.dock-float{top:80px;left:80px;width:380px}',
      '#mx-dock .dh{display:flex;align-items:center;gap:8px;padding:7px 10px;cursor:grab;user-select:none;',
      'background:linear-gradient(180deg,rgba(20,26,38,.9),rgba(12,16,24,.7));border-bottom:1px solid var(--border,rgba(121,192,255,.12))}',
      '#mx-dock .dh:active{cursor:grabbing}',
      '#mx-dock .dh .dt{font-size:11px;letter-spacing:.8px;font-weight:700;color:var(--violet,#d2a8ff)}',
      '#mx-dock .dh .dpulse{width:7px;height:7px;border-radius:50%;background:var(--green,#56d364);animation:dpz 1.4s infinite}',
      '@keyframes dpz{0%,100%{opacity:1}50%{opacity:.3}}',
      '#mx-dock .dh .dsp{margin-left:auto;display:flex;gap:4px}',
      '#mx-dock .dh button{background:rgba(121,192,255,.08);border:1px solid var(--border,rgba(121,192,255,.18));color:var(--text2,#b1bac4);',
      'border-radius:4px;font-size:10px;padding:2px 6px;cursor:pointer;font-family:var(--mono,monospace)}',
      '#mx-dock .dh button:hover{color:var(--blue,#79c0ff)}#mx-dock .dh button.on{color:var(--green,#56d364);border-color:var(--green,#56d364)}',
      '#mx-dock .db{padding:8px 10px;overflow:auto;font-size:11px;line-height:1.55}',
      '#mx-dock.compact .db{max-height:46px;white-space:nowrap;text-overflow:ellipsis}',
      '#mx-dock.expanded .db{max-height:min(60vh,440px)}',
      '#mx-dock .sysrow{display:flex;flex-wrap:wrap;gap:5px 12px;margin-bottom:8px;color:var(--text2,#b1bac4)}',
      '#mx-dock .sysrow b{color:var(--blue,#79c0ff)}',
      '#mx-dock .feed .ev{display:flex;gap:7px;padding:3px 0;border-top:1px solid rgba(121,192,255,.06)}',
      '#mx-dock .feed .ev .ag{color:var(--violet,#d2a8ff);min-width:96px}',
      '#mx-dock .feed .ev .hl{color:var(--text2,#b1bac4);flex:1}',
      '#mx-dock .feed .ev .tm{color:var(--text3,#6e7681);font-size:9px}',
      '#mx-dock .rz{height:7px;cursor:ns-resize;background:transparent;flex:0 0 auto}',
      '#mx-dock .rz:hover{background:rgba(121,192,255,.15)}',
      '#mx-dock .latest .ag{color:var(--violet,#d2a8ff)}#mx-dock .latest .hl{color:var(--text2,#b1bac4)}'
    ].join('');
    document.head.appendChild(s);
  }

  ready(function () {
    if (document.getElementById('mx-dock')) return;
    css();
    var dock = ls('dock') || 'top';
    var expanded = ls('exp') === '1';
    var el = document.createElement('div');
    el.id = 'mx-dock';
    el.className = (expanded ? 'expanded' : 'compact') + ' dock-' + dock;
    el.innerHTML =
      '<div class="dh"><span class="dpulse"></span><span class="dt">mindX activity</span>' +
      '<span class="dsp">' +
      '<button data-d="top" title="dock top">▲</button>' +
      '<button data-d="bottom" title="dock bottom">▼</button>' +
      '<button data-d="left" title="dock left">◀</button>' +
      '<button data-d="right" title="dock right">▶</button>' +
      '<button data-d="float" title="float">◇</button>' +
      '<button data-x="exp" title="expand / revert (or double-click)">⤢</button>' +
      '</span></div>' +
      '<div class="db" id="mx-dock-body"><div class="latest">connecting…</div></div>' +
      '<div class="rz" title="drag to resize"></div>';
    document.body.appendChild(el);
    var body = el.querySelector('#mx-dock-body');
    var savedH = ls('h'); if (savedH && expanded) body.style.maxHeight = savedH + 'px';

    function setDock(d) {
      ['top', 'bottom', 'left', 'right', 'float'].forEach(function (x) { el.classList.remove('dock-' + x); });
      el.classList.add('dock-' + d); ls('dock', d);
      el.style.left = el.style.right = el.style.top = el.style.bottom = el.style.transform = '';
      // re-apply class-based positioning by toggling (clears inline float coords)
      el.className = (el.classList.contains('expanded') ? 'expanded' : 'compact') + ' dock-' + d;
      clampViewport();
    }
    function toggleExpand(force) {
      var exp = force != null ? force : !el.classList.contains('expanded');
      el.classList.toggle('expanded', exp); el.classList.toggle('compact', !exp);
      ls('exp', exp ? '1' : '0'); render();
    }
    function clampViewport() {  // auto display correction: keep on-screen
      var r = el.getBoundingClientRect();
      if (r.right > innerWidth) el.style.left = Math.max(4, innerWidth - r.width - 8) + 'px';
      if (r.bottom > innerHeight) el.style.top = Math.max(4, innerHeight - r.height - 8) + 'px';
    }

    // controls
    el.querySelector('.dsp').addEventListener('click', function (e) {
      var d = e.target.getAttribute('data-d'); if (d) { setDock(d); return; }
      if (e.target.getAttribute('data-x') === 'exp') toggleExpand();
    });
    el.querySelector('.dh').addEventListener('dblclick', function (e) { if (!e.target.closest('.dsp')) toggleExpand(); });

    // drag → dock to nearest edge (or float)
    var hdr = el.querySelector('.dh'), drag = null;
    hdr.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.dsp')) return;
      drag = { x: e.clientX, y: e.clientY, r: el.getBoundingClientRect() };
      hdr.setPointerCapture(e.pointerId);
    });
    hdr.addEventListener('pointermove', function (e) {
      if (!drag) return;
      el.className = (el.classList.contains('expanded') ? 'expanded' : 'compact') + ' dock-float';
      el.style.transform = ''; el.style.left = (drag.r.left + e.clientX - drag.x) + 'px';
      el.style.top = (drag.r.top + e.clientY - drag.y) + 'px'; el.style.right = el.style.bottom = '';
    });
    hdr.addEventListener('pointerup', function (e) {
      if (!drag) return; drag = null;
      var r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      var dl = cx, dr = innerWidth - cx, dt = cy, dbm = innerHeight - cy;
      var m = Math.min(dl, dr, dt, dbm), EDGE = 90;
      if (m > EDGE) { ls('dock', 'float'); clampViewport(); return; }   // stay floating
      setDock(m === dt ? 'top' : m === dbm ? 'bottom' : m === dl ? 'left' : 'right');
    });

    // vertical resize
    var rz = el.querySelector('.rz'), rs = null;
    rz.addEventListener('pointerdown', function (e) { rs = { y: e.clientY, h: body.getBoundingClientRect().height }; rz.setPointerCapture(e.pointerId); toggleExpand(true); });
    rz.addEventListener('pointermove', function (e) {
      if (!rs) return; var h = Math.max(46, Math.min(innerHeight * 0.8, rs.h + e.clientY - rs.y));
      body.style.maxHeight = h + 'px'; ls('h', Math.round(h));
    });
    rz.addEventListener('pointerup', function () { rs = null; clampViewport(); });

    // data
    var sys = {}, events = [];
    function fmtTime(ts) { try { return new Date(ts * 1000).toTimeString().slice(0, 8); } catch (e) { return ''; } }
    function render() {
      if (!el.classList.contains('expanded')) {
        var e0 = events[0];
        body.innerHTML = '<div class="latest">' + (e0
          ? '<span class="ag">' + esc(e0.agent || '?') + '</span> <span class="hl">' + esc(e0.headline || e0.type || '') + '</span>'
          : '<span class="hl">awaiting activity…</span>') + '</div>';
        return;
      }
      var sr = Object.keys(sys).slice(0, 8).map(function (k) {
        var v = sys[k]; if (v && typeof v === 'object') return '';
        return '<span>' + esc(k) + ' <b>' + esc(v) + '</b></span>';
      }).filter(Boolean).join('');
      var feed = events.slice(0, 30).map(function (ev) {
        return '<div class="ev"><span class="ag">' + esc(ev.agent || '?') + '</span>' +
          '<span class="hl">' + esc(ev.headline || ev.type || '') + '</span>' +
          '<span class="tm">' + fmtTime(ev.timestamp) + '</span></div>';
      }).join('');
      body.innerHTML = (sr ? '<div class="sysrow">' + sr + '</div>' : '') +
        '<div class="feed">' + (feed || '<div class="ev"><span class="hl">no recent activity</span></div>') + '</div>';
    }
    function pull() {
      fetch('/insight/agentic/activity', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.events) { events = d.events.slice().reverse(); render(); } }).catch(function () {});
    }
    function pullSys() {
      fetch('/diagnostics/live', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d) { sys = {}; Object.keys(d).forEach(function (k) { if (typeof d[k] !== 'object') sys[k] = d[k]; }); if (el.classList.contains('expanded')) render(); } }).catch(function () {});
    }
    pull(); pullSys(); render();
    setInterval(pull, 10000); setInterval(pullSys, 15000);
    addEventListener('resize', clampViewport);
  });
})();
