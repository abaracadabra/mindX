/**
 * mindX Brain — Procedural canvas rendering of the AUTOMINDx cybernetic brain.
 * No background. Transparent. Matches the NFT: mannequin head, coral brain folds,
 * green neon circuit traces, cyan glow.
 *
 * Usage:
 *   <canvas id="brain" width="256" height="320"></canvas>
 *   <script src="/static/mindx-brain.js"></script>
 *   <script>mindxBrain(document.getElementById('brain'));</script>
 *
 * Or for a small favicon-style icon:
 *   mindxBrain(canvas, {size: 64, animate: false});
 */
function mindxBrain(canvas, opts = {}) {
  const W = opts.size || canvas.width || 256;
  const H = opts.sizeH || Math.floor(W * 1.25);
  canvas.width = W; canvas.height = H;
  const c = canvas.getContext('2d');
  const animate = opts.animate !== false;
  const scale = W / 256; // base design is 256px wide

  // ── Brain geometry: sulci (folds) as bezier curves ──
  // Defined at 256x320 base, scaled
  const brainCenter = {x: W / 2, y: H * 0.36};
  const brainRX = 90 * scale, brainRY = 65 * scale;

  // Sulci paths (brain fold grooves) — hand-crafted to match the image
  const sulci = [
    // Central fissure
    [{x:0, y:-55}, {x:-5, y:-30}, {x:5, y:-5}, {x:-3, y:20}, {x:0, y:45}],
    // Left lateral
    [{x:-70, y:0}, {x:-50, y:-15}, {x:-25, y:-10}, {x:-10, y:5}, {x:5, y:15}],
    // Right lateral
    [{x:70, y:0}, {x:50, y:-15}, {x:25, y:-10}, {x:10, y:5}, {x:-5, y:15}],
    // Left frontal
    [{x:-60, y:-30}, {x:-40, y:-40}, {x:-15, y:-45}, {x:0, y:-40}],
    // Right frontal
    [{x:60, y:-30}, {x:40, y:-40}, {x:15, y:-45}, {x:0, y:-40}],
    // Left parietal
    [{x:-55, y:20}, {x:-35, y:10}, {x:-20, y:25}, {x:-5, y:35}],
    // Right parietal
    [{x:55, y:20}, {x:35, y:10}, {x:20, y:25}, {x:5, y:35}],
    // Occipital cross
    [{x:-40, y:35}, {x:-15, y:45}, {x:15, y:45}, {x:40, y:35}],
  ].map(path => path.map(p => ({x: p.x * scale, y: p.y * scale})));

  // Circuit trace paths (green neon lines running through the brain)
  const circuits = [
    // Main bus — left hemisphere
    [{x:-10, y:-50}, {x:-20, y:-30}, {x:-35, y:-15}, {x:-55, y:-5}, {x:-65, y:10}, {x:-50, y:25}, {x:-30, y:35}],
    // Branch right
    [{x:10, y:-50}, {x:25, y:-25}, {x:40, y:-10}, {x:55, y:5}, {x:45, y:20}, {x:25, y:30}],
    // Cross connection
    [{x:-30, y:0}, {x:-10, y:5}, {x:10, y:5}, {x:30, y:0}],
    // Deep trace left
    [{x:-45, y:-25}, {x:-30, y:-20}, {x:-20, y:-5}, {x:-25, y:15}],
    // Deep trace right
    [{x:45, y:-25}, {x:30, y:-20}, {x:20, y:-5}, {x:25, y:15}],
    // Vertical spine
    [{x:0, y:-55}, {x:0, y:-30}, {x:0, y:0}, {x:0, y:30}, {x:0, y:50}],
  ].map(path => path.map(p => ({x: p.x * scale, y: p.y * scale})));

  // Circuit nodes (junction points that glow)
  const circuitNodes = [
    {x: -35, y: -15}, {x: 35, y: -15}, {x: 0, y: -30},
    {x: -55, y: 5}, {x: 55, y: 5}, {x: 0, y: 0},
    {x: -25, y: 25}, {x: 25, y: 25}, {x: 0, y: 45},
    {x: -45, y: -30}, {x: 45, y: -30},
  ].map(p => ({x: p.x * scale, y: p.y * scale, phase: Math.random() * 6.28}));

  function drawFrame(t) {
    c.clearRect(0, 0, W, H);
    const bx = brainCenter.x, by = brainCenter.y;

    // ── Head/neck silhouette (pale blue mannequin) ──
    c.save();
    // Neck
    c.beginPath();
    c.moveTo(bx - 28 * scale, by + 65 * scale);
    c.quadraticCurveTo(bx - 30 * scale, H * 0.85, bx - 22 * scale, H * 0.95);
    c.lineTo(bx + 22 * scale, H * 0.95);
    c.quadraticCurveTo(bx + 30 * scale, H * 0.85, bx + 28 * scale, by + 65 * scale);
    c.closePath();
    const neckGrad = c.createLinearGradient(bx, by + 65 * scale, bx, H);
    neckGrad.addColorStop(0, 'rgba(180,195,215,.25)');
    neckGrad.addColorStop(1, 'rgba(140,155,175,.08)');
    c.fillStyle = neckGrad; c.fill();

    // Face outline
    c.beginPath();
    c.ellipse(bx, by + 35 * scale, 38 * scale, 42 * scale, 0, 0, Math.PI * 2);
    const faceGrad = c.createRadialGradient(bx, by + 25 * scale, 0, bx, by + 35 * scale, 42 * scale);
    faceGrad.addColorStop(0, 'rgba(195,210,230,.2)');
    faceGrad.addColorStop(.7, 'rgba(170,185,205,.12)');
    faceGrad.addColorStop(1, 'rgba(140,155,175,.04)');
    c.fillStyle = faceGrad; c.fill();

    // Eyes (subtle)
    c.globalAlpha = .15;
    c.beginPath(); c.ellipse(bx - 14 * scale, by + 28 * scale, 6 * scale, 2.5 * scale, 0, 0, Math.PI * 2);
    c.fillStyle = '#58a6ff'; c.fill();
    c.beginPath(); c.ellipse(bx + 14 * scale, by + 28 * scale, 6 * scale, 2.5 * scale, 0, 0, Math.PI * 2);
    c.fill();
    c.globalAlpha = 1;

    // Nose line
    c.beginPath(); c.moveTo(bx, by + 35 * scale); c.lineTo(bx - 2 * scale, by + 45 * scale);
    c.strokeStyle = 'rgba(170,185,205,.08)'; c.lineWidth = 1 * scale; c.stroke();

    // Lips
    c.beginPath();
    c.moveTo(bx - 10 * scale, by + 52 * scale);
    c.quadraticCurveTo(bx, by + 49 * scale, bx + 10 * scale, by + 52 * scale);
    c.strokeStyle = 'rgba(180,195,215,.1)'; c.lineWidth = 1.2 * scale; c.stroke();
    c.restore();

    // ── Brain mass (coral/cyan organic shape) ──
    c.save();
    // Outer glow
    const glowR = brainRX * 1.4 + Math.sin(t * .002) * 4 * scale;
    const brainGlow = c.createRadialGradient(bx, by, brainRX * .3, bx, by, glowR);
    brainGlow.addColorStop(0, 'rgba(88,166,255,.06)');
    brainGlow.addColorStop(.5, 'rgba(100,220,230,.03)');
    brainGlow.addColorStop(1, 'transparent');
    c.fillStyle = brainGlow;
    c.beginPath(); c.ellipse(bx, by, glowR, glowR * .75, 0, 0, Math.PI * 2); c.fill();

    // Brain body
    c.beginPath();
    c.ellipse(bx, by, brainRX, brainRY, 0, 0, Math.PI * 2);
    const brainGrad = c.createRadialGradient(bx - 10 * scale, by - 15 * scale, 0, bx, by, brainRX);
    brainGrad.addColorStop(0, 'rgba(140,210,220,.35)');
    brainGrad.addColorStop(.4, 'rgba(120,190,210,.25)');
    brainGrad.addColorStop(.7, 'rgba(100,170,200,.18)');
    brainGrad.addColorStop(1, 'rgba(80,140,180,.1)');
    c.fillStyle = brainGrad; c.fill();

    // Brain border
    c.strokeStyle = 'rgba(100,200,220,.2)';
    c.lineWidth = 1.5 * scale; c.stroke();
    c.restore();

    // ── Sulci (brain fold grooves) ──
    c.save();
    c.lineCap = 'round'; c.lineJoin = 'round';
    for (const path of sulci) {
      c.beginPath();
      c.moveTo(bx + path[0].x, by + path[0].y);
      for (let i = 1; i < path.length - 1; i++) {
        const xm = (path[i].x + path[i + 1].x) / 2;
        const ym = (path[i].y + path[i + 1].y) / 2;
        c.quadraticCurveTo(bx + path[i].x, by + path[i].y, bx + xm, by + ym);
      }
      const last = path[path.length - 1];
      c.lineTo(bx + last.x, by + last.y);
      c.strokeStyle = 'rgba(80,160,190,.2)';
      c.lineWidth = 2 * scale; c.stroke();
      // Inner highlight
      c.strokeStyle = 'rgba(120,210,230,.08)';
      c.lineWidth = 4 * scale; c.stroke();
    }
    c.restore();

    // ── Circuit traces (green neon) ──
    c.save();
    c.lineCap = 'round'; c.lineJoin = 'round';
    for (let ci = 0; ci < circuits.length; ci++) {
      const path = circuits[ci];
      // Animate: pulse travels along the circuit
      const pulsePos = ((t * .001 + ci * 1.2) % 3) / 3; // 0-1 along path

      // Draw the base trace
      c.beginPath();
      c.moveTo(bx + path[0].x, by + path[0].y);
      for (let i = 1; i < path.length - 1; i++) {
        const xm = (path[i].x + path[i + 1].x) / 2;
        const ym = (path[i].y + path[i + 1].y) / 2;
        c.quadraticCurveTo(bx + path[i].x, by + path[i].y, bx + xm, by + ym);
      }
      c.lineTo(bx + path[path.length - 1].x, by + path[path.length - 1].y);
      c.strokeStyle = 'rgba(0,255,120,.15)';
      c.lineWidth = 1.5 * scale; c.stroke();
      // Bright core
      c.strokeStyle = 'rgba(50,255,140,.08)';
      c.lineWidth = 4 * scale; c.stroke();

      // Traveling pulse
      if (animate) {
        const idx = Math.floor(pulsePos * (path.length - 1));
        const frac = pulsePos * (path.length - 1) - idx;
        if (idx < path.length - 1) {
          const px = bx + path[idx].x + (path[idx + 1].x - path[idx].x) * frac;
          const py = by + path[idx].y + (path[idx + 1].y - path[idx].y) * frac;
          const pg = c.createRadialGradient(px, py, 0, px, py, 12 * scale);
          pg.addColorStop(0, 'rgba(0,255,120,.4)');
          pg.addColorStop(.5, 'rgba(0,255,120,.1)');
          pg.addColorStop(1, 'transparent');
          c.fillStyle = pg;
          c.beginPath(); c.arc(px, py, 12 * scale, 0, 6.28); c.fill();
          // Bright core dot
          c.beginPath(); c.arc(px, py, 2 * scale, 0, 6.28);
          c.fillStyle = 'rgba(150,255,200,.6)'; c.fill();
        }
      }
    }
    c.restore();

    // ── Circuit junction nodes ──
    c.save();
    for (const node of circuitNodes) {
      const nx = bx + node.x, ny = by + node.y;
      const pulse = animate ? .4 + Math.sin(t * .003 + node.phase) * .2 : .4;
      // Glow
      c.beginPath(); c.arc(nx, ny, 6 * scale, 0, 6.28);
      c.fillStyle = `rgba(0,255,120,${pulse * .15})`; c.fill();
      // Core
      c.beginPath(); c.arc(nx, ny, 2.5 * scale, 0, 6.28);
      c.fillStyle = `rgba(100,255,180,${pulse})`; c.fill();
    }
    c.restore();

    // ── Top glow (cyan emanation from brain top) ──
    if (animate) {
      const topGlow = c.createRadialGradient(bx, by - brainRY * .5, 0, bx, by - brainRY, brainRX * .8);
      topGlow.addColorStop(0, `rgba(88,166,255,${.03 + Math.sin(t * .0015) * .015})`);
      topGlow.addColorStop(1, 'transparent');
      c.fillStyle = topGlow;
      c.beginPath(); c.ellipse(bx, by - brainRY * .5, brainRX * .8, brainRY * .5, 0, 0, Math.PI * 2); c.fill();
    }
  }

  if (animate) {
    const RM = window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    let af = 0;
    function loop(t) {
      if (!RM || af % 3 === 0) drawFrame(t);
      af++; requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  } else {
    drawFrame(0);
  }

  return {redraw: drawFrame};
}

// Export for module systems
if (typeof module !== 'undefined') module.exports = mindxBrain;
