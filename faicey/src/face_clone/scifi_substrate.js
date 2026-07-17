/**
 * scifi_substrate.js — a shared sci-fi HUD substrate for faicey AND voicey.
 *
 * Evolved from the DeltaVerse participant-field substrate (dapp/deltaverse.js —
 * drifting glowing "stars are people") and fused with instrument-HUD chrome
 * (corner brackets, a reticle, a grid, a sweep line). Same DeltaVerse doctrine:
 * raw canvas, no dependencies, always shows. A single dependency-free ES module
 * that drops into faicey's face demo and voaice's voice lab alike — one visual
 * language across the constellation.
 *
 * The layout geometry + the drifting field are pure and headless-tested; the
 * canvas draw (SciFiHUD) is browser-only.
 *
 * © Professor Codephreak - rage.pythai.net
 */

export const SCIFI_PALETTE = Object.freeze({
  bg: '#02080c', cyan: '#22e0ff', dim: '#0a4b5c',
  grid: 'rgba(34,224,255,0.10)', ok: '#22ffa0', warn: '#ff6a3d', text: '#8fd8e6',
});

/** Four L-shaped corner brackets for a HUD frame → array of 4 polylines. */
export function cornerBrackets(w, h, len = 16, inset = 5) {
  const L = inset, R = w - inset, T = inset, B = h - inset;
  return [
    [{ x: L, y: T + len }, { x: L, y: T }, { x: L + len, y: T }],       // top-left
    [{ x: R - len, y: T }, { x: R, y: T }, { x: R, y: T + len }],       // top-right
    [{ x: L, y: B - len }, { x: L, y: B }, { x: L + len, y: B }],       // bottom-left
    [{ x: R - len, y: B }, { x: R, y: B }, { x: R, y: B - len }],       // bottom-right
  ];
}

/** Reticle: four ticks around a centre point → array of [{x,y},{x,y}] segments. */
export function reticleSegments(cx, cy, r = 10, gap = 3) {
  return [
    [{ x: cx, y: cy - r }, { x: cx, y: cy - gap }],
    [{ x: cx, y: cy + gap }, { x: cx, y: cy + r }],
    [{ x: cx - r, y: cy }, { x: cx - gap, y: cy }],
    [{ x: cx + gap, y: cy }, { x: cx + r, y: cy }],
  ];
}

/**
 * A drifting particle field — the DeltaVerse "stars are people" substrate, in
 * normalised [0,1] space, seedable + deterministic so it's testable and
 * resume-safe (no Math.random in the step).
 */
export class ParticleField {
  constructor(opts = {}) {
    const count = opts.count ?? 80;
    let s = opts.seed ?? 1;
    const u = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    this.p = [];
    for (let i = 0; i < count; i++) this.p.push({ x: u(), y: u(), vx: (u() - 0.5) * 0.003, vy: (u() - 0.5) * 0.003, hue: u(), size: 0.5 + u() * 1.8 });
  }
  step() {
    for (const q of this.p) {
      q.x += q.vx; q.y += q.vy;
      if (q.x < 0 || q.x > 1) { q.vx *= -1; q.x = Math.max(0, Math.min(1, q.x)); }
      if (q.y < 0 || q.y > 1) { q.vy *= -1; q.y = Math.max(0, Math.min(1, q.y)); }
    }
    return this;
  }
  particles() { return this.p; }
}

/** Browser-only HUD renderer using the substrate above. */
export class SciFiHUD {
  constructor(canvas, opts = {}) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d');
    this.field = opts.field === false ? null : new ParticleField({ count: opts.count ?? 70, seed: opts.seed ?? 7 });
    this.pal = opts.palette || SCIFI_PALETTE; this.t = 0;
  }
  resize() { const dpr = Math.min(2, (typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1); this.canvas.width = this.canvas.clientWidth * dpr; this.canvas.height = this.canvas.clientHeight * dpr; }
  /** One frame: faint grid + drifting field + a slow sweep + corner brackets. */
  draw() {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height; if (!W || !H) return;
    this.t += 0.016;
    ctx.clearRect(0, 0, W, H);
    // grid
    ctx.strokeStyle = this.pal.grid; ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 26) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 26) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    // drifting field — stars are people
    if (this.field) {
      this.field.step();
      for (const q of this.field.particles()) {
        const pulse = 0.6 + 0.4 * Math.sin(this.t * 2 + q.x * 12);
        ctx.fillStyle = `hsla(${180 + q.hue * 40},90%,65%,${0.5 * pulse})`;
        ctx.beginPath(); ctx.arc(q.x * W, q.y * H, q.size * pulse, 0, 7); ctx.fill();
      }
    }
    // a slow horizontal sweep line
    const sy = (0.5 + 0.5 * Math.sin(this.t * 0.6)) * H;
    ctx.strokeStyle = 'rgba(34,224,255,.18)'; ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(W, sy); ctx.stroke();
    // corner brackets
    ctx.strokeStyle = this.pal.cyan; ctx.lineWidth = 1.5;
    for (const poly of cornerBrackets(W, H, 18, 6)) { ctx.beginPath(); poly.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.stroke(); }
  }
}

export default SciFiHUD;
