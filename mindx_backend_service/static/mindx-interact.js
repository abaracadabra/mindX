/**
 * mindx-interact.js — Shared interaction engine for all mindX canvas pages.
 *
 * Adds deep mouse/touch/wheel interactivity to any particle canvas:
 *   - Mouse hover: attraction/repulsion field with visible radius
 *   - Click: particle burst + shockwave ring + node activation
 *   - Drag: create persistent force streams (paint with particles)
 *   - Wheel: zoom the force field radius
 *   - Touch: full parity (attraction, burst, drag)
 *   - Double-click: gravity well that persists and orbits particles
 *   - Shift+click: repulsion bomb (pushes everything away)
 *   - Hover glow: cursor has a visible glow aura
 *
 * Usage:
 *   const interact = mindxInteract(canvas, {particles, nodes, edges, flashEdge});
 *   // In your draw loop:  interact.draw(ctx, t);
 *   // interact.mx, interact.my give cursor position
 */
function mindxInteract(canvas, opts = {}) {
  const PHI = (1 + Math.sqrt(5)) / 2; // Golden ratio 1.618...
  let mx = -1, my = -1, pmx = -1, pmy = -1;
  let dragging = false, dragTrail = [];
  let forceRadius = 180;
  let wells = [];       // Persistent gravity wells from double-click
  let shockwaves = [];  // Expanding ring animations
  let glowIntensity = 0;
  let clickCount = 0;

  const particles = opts.particles || [];
  const nodes = opts.nodes || [];
  const flashEdge = opts.flashEdge || (() => {});

  // ── Unified pointer tracking (mouse + touch) ──
  function onMove(x, y) {
    pmx = mx; pmy = my;
    mx = x; my = y;
    glowIntensity = Math.min(glowIntensity + .05, 1);
  }
  function onLeave() { mx = -1; my = -1; glowIntensity = 0; dragging = false; }

  canvas.addEventListener('mousemove', e => { onMove(e.clientX, e.clientY); if (dragging) addDragTrail(e.clientX, e.clientY); });
  canvas.addEventListener('mouseleave', onLeave);
  canvas.addEventListener('touchmove', e => { e.preventDefault(); const t = e.touches[0]; onMove(t.clientX, t.clientY); if (dragging) addDragTrail(t.clientX, t.clientY); }, {passive: false});
  canvas.addEventListener('touchend', () => { dragging = false; });

  // ── Click: burst + shockwave ──
  function handleClick(x, y, shift) {
    clickCount++;
    if (shift) {
      // Repulsion bomb
      shockwaves.push({x, y, r: 0, maxR: 300, life: 1, type: 'repulse'});
      applyForce(x, y, 300, -2);
    } else {
      shockwaves.push({x, y, r: 0, maxR: 200, life: 1, type: 'attract'});
      // Fibonacci burst: spawn particles in golden angle spiral
      const n = 12;
      for (let i = 0; i < n; i++) {
        const angle = i * Math.PI * 2 / PHI; // Golden angle
        const dist = Math.sqrt(i / n) * 40;
        const speed = .5 + Math.random() * 1.5;
        particles.push({
          x: x + Math.cos(angle) * dist,
          y: y + Math.sin(angle) * dist,
          s: Math.random() * 2.5 + .5,
          vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
          ph: Math.random() * 6.28,
          cl: ['rgba(210,168,255,', 'rgba(88,166,255,', 'rgba(63,185,80,', 'rgba(210,153,34,'][i % 4],
          life: 1,
        });
      }
      // Activate nearby nodes
      for (const n of nodes) {
        const dx = x - n.x, dy = y - n.y;
        if (Math.sqrt(dx * dx + dy * dy) < forceRadius) n.act = 1;
      }
      // Flash edges
      for (let i = 0; i < 4; i++) setTimeout(flashEdge, i * 50);
    }
    while (particles.length > 350) particles.shift();
  }

  canvas.addEventListener('click', e => handleClick(e.clientX, e.clientY, e.shiftKey));
  canvas.addEventListener('touchstart', e => { dragging = true; const t = e.touches[0]; onMove(t.clientX, t.clientY); });

  // ── Double-click: persistent gravity well ──
  canvas.addEventListener('dblclick', e => {
    e.preventDefault();
    wells.push({x: e.clientX, y: e.clientY, strength: 1, life: 1, born: Date.now()});
    shockwaves.push({x: e.clientX, y: e.clientY, r: 0, maxR: 250, life: 1, type: 'well'});
    if (wells.length > 5) wells.shift();
  });

  // ── Wheel: zoom force radius ──
  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    forceRadius = Math.max(60, Math.min(400, forceRadius - e.deltaY * .3));
  }, {passive: false});

  // ── Drag: paint trail of particles ──
  canvas.addEventListener('mousedown', e => { if (!e.shiftKey) dragging = true; });
  canvas.addEventListener('mouseup', () => { dragging = false; dragTrail = []; });

  function addDragTrail(x, y) {
    dragTrail.push({x, y, life: 1});
    if (dragTrail.length > 40) dragTrail.shift();
    // Spawn trail particles
    if (Math.random() > .5) {
      particles.push({
        x: x + (Math.random() - .5) * 10, y: y + (Math.random() - .5) * 10,
        s: Math.random() * 1.5 + .3,
        vx: (Math.random() - .5) * .5, vy: (Math.random() - .5) * .5,
        ph: Math.random() * 6.28,
        cl: 'rgba(210,168,255,',
        life: 1,
      });
    }
    while (particles.length > 350) particles.shift();
  }

  // ── Apply force to all particles ──
  function applyForce(fx, fy, radius, strength) {
    for (const p of particles) {
      const dx = fx - p.x, dy = fy - p.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < radius && dist > 1) {
        const f = (radius - dist) / radius * strength * .03;
        p.vx += dx / dist * f;
        p.vy += dy / dist * f;
      }
    }
  }

  // ── Physics update (call from your draw loop) ──
  function update() {
    // Mouse force field
    if (mx > 0) {
      applyForce(mx, my, forceRadius, 1);
    }

    // Gravity wells
    for (let i = wells.length - 1; i >= 0; i--) {
      const w = wells[i];
      w.life -= .002;
      if (w.life <= 0) { wells.splice(i, 1); continue; }
      applyForce(w.x, w.y, 200 * w.life, w.strength * w.life);
    }

    // Shockwave expansion
    for (let i = shockwaves.length - 1; i >= 0; i--) {
      const s = shockwaves[i];
      s.r += (s.maxR - s.r) * .08;
      s.life -= .02;
      if (s.life <= 0) { shockwaves.splice(i, 1); continue; }
      // Shockwave pushes particles at its wavefront
      if (s.type === 'repulse') {
        for (const p of particles) {
          const dx = p.x - s.x, dy = p.y - s.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (Math.abs(dist - s.r) < 20) {
            p.vx += dx / dist * s.life * .5;
            p.vy += dy / dist * s.life * .5;
          }
        }
      }
    }

    // Drag trail decay
    for (let i = dragTrail.length - 1; i >= 0; i--) {
      dragTrail[i].life -= .03;
      if (dragTrail[i].life <= 0) dragTrail.splice(i, 1);
    }

    // Particle life decay (for spawned particles)
    for (const p of particles) {
      if (p.life !== undefined) {
        p.life -= .003;
      }
    }

    glowIntensity *= .98;
  }

  // ── Draw interaction visuals (call from your draw loop after particles) ──
  function draw(ctx, t) {
    // Cursor glow aura
    if (mx > 0 && glowIntensity > .01) {
      const gr = ctx.createRadialGradient(mx, my, 0, mx, my, forceRadius);
      gr.addColorStop(0, `rgba(210,168,255,${glowIntensity * .04})`);
      gr.addColorStop(.5, `rgba(88,166,255,${glowIntensity * .02})`);
      gr.addColorStop(1, 'transparent');
      ctx.fillStyle = gr;
      ctx.beginPath(); ctx.arc(mx, my, forceRadius, 0, 6.28); ctx.fill();

      // Force field ring
      ctx.beginPath(); ctx.arc(mx, my, forceRadius, 0, 6.28);
      ctx.strokeStyle = `rgba(210,168,255,${glowIntensity * .06})`;
      ctx.lineWidth = 1; ctx.stroke();
    }

    // Drag trail
    if (dragTrail.length > 1) {
      ctx.beginPath();
      ctx.moveTo(dragTrail[0].x, dragTrail[0].y);
      for (const pt of dragTrail) {
        ctx.lineTo(pt.x, pt.y);
      }
      ctx.strokeStyle = `rgba(210,168,255,.12)`;
      ctx.lineWidth = 2; ctx.stroke();
    }

    // Shockwave rings
    for (const s of shockwaves) {
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.28);
      const col = s.type === 'repulse' ? `rgba(248,81,73,${s.life * .3})` :
                  s.type === 'well' ? `rgba(210,153,34,${s.life * .3})` :
                  `rgba(88,166,255,${s.life * .3})`;
      ctx.strokeStyle = col;
      ctx.lineWidth = 2 * s.life; ctx.stroke();
    }

    // Gravity wells
    for (const w of wells) {
      const wr = 15 + Math.sin(t * .003) * 5;
      ctx.beginPath(); ctx.arc(w.x, w.y, wr * w.life, 0, 6.28);
      ctx.fillStyle = `rgba(210,153,34,${w.life * .08})`; ctx.fill();
      ctx.beginPath(); ctx.arc(w.x, w.y, 4 * w.life, 0, 6.28);
      ctx.fillStyle = `rgba(210,153,34,${w.life * .3})`; ctx.fill();
      // Orbital ring
      ctx.beginPath(); ctx.arc(w.x, w.y, 60 * w.life, 0, 6.28);
      ctx.strokeStyle = `rgba(210,153,34,${w.life * .05})`;
      ctx.lineWidth = .5; ctx.stroke();
    }
  }

  return {
    update, draw,
    get mx() { return mx; }, get my() { return my; },
    get forceRadius() { return forceRadius; },
    get clickCount() { return clickCount; },
    get wells() { return wells; },
    handleClick,
  };
}

if (typeof module !== 'undefined') module.exports = mindxInteract;
