/* archetypes.js — single source of truth for the mindX agent archetypes.
 *
 * The seven archetypes are the PersonaRole taxonomy
 * (expert/meta/development/worker/governance/community/marketing). Each carries
 * the seed for an AgenticPlace iNFT IntelligenceConfig (intelligenceLevel,
 * autonomous, behavior) and a deterministic wireframe avatar (inline SVG, no
 * asset). Consumed by /static/builder_button.js (the BUILDER emergence) and the
 * /inft mint page (archetype prefill), so the two can never drift.
 *
 * Exposes: window.MINDX_ARCHETYPES, window.mindxArchetype(key), window.mindxAvatarSVG(a,size)
 */
(function () {
  'use strict';
  if (window.MINDX_ARCHETYPES) return;  // idempotent

  var ARCHETYPES = [
    { key: 'expert',      label: 'Expert',      glyph: '◈', accent: '#bc8cff', lvl: 88, auto: false, blurb: 'deep domain reasoning' },
    { key: 'meta',        label: 'Meta',        glyph: '✦', accent: '#56d364', lvl: 92, auto: true,  blurb: 'reasons about reasoning' },
    { key: 'development', label: 'Development', glyph: '⌬', accent: '#79c0ff', lvl: 80, auto: true,  blurb: 'builds and ships code' },
    { key: 'worker',      label: 'Worker',      glyph: '⬡', accent: '#39d3c8', lvl: 60, auto: false, blurb: 'executes bounded tasks' },
    { key: 'governance',  label: 'Governance',  glyph: '⬢', accent: '#e3b341', lvl: 75, auto: false, blurb: 'decides, votes, vetoes' },
    { key: 'community',   label: 'Community',   glyph: '◉', accent: '#f0883e', lvl: 55, auto: false, blurb: 'engages participants' },
    { key: 'marketing',   label: 'Marketing',   glyph: '◴', accent: '#f85149', lvl: 50, auto: false, blurb: 'broadcasts the voice' }
  ];

  function avatarSVG(a, size) {
    if (!a) return '';
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
  }

  function lookup(key) {
    key = String(key || '').toLowerCase();
    for (var i = 0; i < ARCHETYPES.length; i++) if (ARCHETYPES[i].key === key) return ARCHETYPES[i];
    return null;
  }

  // SVG → data URI, usable directly as an iNFT imageURI (data:image/svg+xml).
  function avatarDataURI(a, size) {
    try { return 'data:image/svg+xml;utf8,' + encodeURIComponent(avatarSVG(a, size || 64)); }
    catch (e) { return ''; }
  }

  window.MINDX_ARCHETYPES = ARCHETYPES;
  window.mindxArchetype = lookup;
  window.mindxAvatarSVG = avatarSVG;
  window.mindxAvatarDataURI = avatarDataURI;
})();
