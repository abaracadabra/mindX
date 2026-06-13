// deltaverse.js — DeltaVerse participant field for the SoundWave dApp.
//
// Each participant (a registered voiceprint) is a star in a drifting field: hue from the
// voice's dominant frequency, size from the measurement precision. Rendered with WebGL
// (GL_POINTS) when available, with a 2D-canvas fallback so it always shows. This is the
// dApp's nod to DeltaVerse webGL participant-interaction technology — stars are people.

export class DeltaVerse {
  constructor(canvas) {
    this.canvas = canvas;
    this.participants = [];
    this.t = 0;
    this._seedAmbient(120);
    this.gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    this._resize();
    window.addEventListener('resize', () => this._resize());
    if (this.gl) this._initGL();
  }

  _resize() {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    this.canvas.width = innerWidth * dpr;
    this.canvas.height = innerHeight * dpr;
    if (this.gl) this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
  }

  _seedAmbient(n) {
    for (let i = 0; i < n; i++) {
      this.participants.push({
        x: Math.random() * 2 - 1, y: Math.random() * 2 - 1,
        vx: (Math.random() - 0.5) * 0.0006, vy: (Math.random() - 0.5) * 0.0006,
        hue: Math.random() * 360, size: 1 + Math.random() * 2, ambient: true,
      });
    }
  }

  /** A new voiceprint joins the field. freq → hue, precision → size + brightness. */
  addParticipant({ freq = 220, precision = 0.5, id = '' }) {
    const hue = (Math.log2(Math.max(20, freq) / 20) / 10) * 360 % 360;
    this.participants.push({
      x: (Math.random() - 0.5) * 0.2, y: (Math.random() - 0.5) * 0.2,
      vx: (Math.random() - 0.5) * 0.001, vy: (Math.random() - 0.5) * 0.001,
      hue, size: 4 + precision * 10, bright: 0.5 + precision * 0.5, id,
    });
  }

  start() { if (!this._running) { this._running = true; this._loop(); } }

  _loop() {
    this.t += 0.016;
    for (const p of this.participants) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < -1 || p.x > 1) p.vx *= -1;
      if (p.y < -1 || p.y > 1) p.vy *= -1;
    }
    if (this.gl) this._drawGL(); else this._draw2D();
    requestAnimationFrame(() => this._loop());
  }

  // ── WebGL path ──
  _initGL() {
    const gl = this.gl;
    const vs = `attribute vec2 pos; attribute float size; attribute vec3 col;
      varying vec3 vCol; void main(){ vCol=col; gl_Position=vec4(pos,0.,1.); gl_PointSize=size; }`;
    const fs = `precision mediump float; varying vec3 vCol;
      void main(){ vec2 d=gl_PointCoord-vec2(.5); float a=smoothstep(.5,.0,length(d));
      gl_FragColor=vec4(vCol*a, a); }`;
    const sh = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog); gl.useProgram(prog);
    this.prog = prog;
    this.buf = gl.createBuffer();
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
  }

  _drawGL() {
    const gl = this.gl;
    gl.clearColor(0.02, 0.024, 0.04, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    const data = [];
    for (const p of this.participants) {
      const [r, g, b] = hsl(p.hue, 0.8, (p.bright || 0.6));
      const pulse = p.ambient ? 1 : 1 + 0.3 * Math.sin(this.t * 3 + p.x * 10);
      data.push(p.x, p.y, p.size * pulse * (this.canvas.width / 1200), r, g, b);
    }
    const arr = new Float32Array(data);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buf);
    gl.bufferData(gl.ARRAY_BUFFER, arr, gl.DYNAMIC_DRAW);
    const stride = 6 * 4;
    const loc = (n) => gl.getAttribLocation(this.prog, n);
    gl.enableVertexAttribArray(loc('pos')); gl.vertexAttribPointer(loc('pos'), 2, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(loc('size')); gl.vertexAttribPointer(loc('size'), 1, gl.FLOAT, false, stride, 8);
    gl.enableVertexAttribArray(loc('col')); gl.vertexAttribPointer(loc('col'), 3, gl.FLOAT, false, stride, 12);
    gl.drawArrays(gl.POINTS, 0, this.participants.length);
  }

  // ── 2D fallback ──
  _draw2D() {
    const ctx = this.canvas.getContext('2d');
    const W = this.canvas.width, H = this.canvas.height;
    ctx.fillStyle = '#05060a'; ctx.fillRect(0, 0, W, H);
    for (const p of this.participants) {
      const x = (p.x * 0.5 + 0.5) * W, y = (p.y * 0.5 + 0.5) * H;
      const pulse = p.ambient ? 1 : 1 + 0.3 * Math.sin(this.t * 3 + p.x * 10);
      ctx.beginPath();
      ctx.fillStyle = `hsla(${p.hue},80%,${Math.round((p.bright || 0.6) * 70)}%,0.9)`;
      ctx.arc(x, y, p.size * pulse, 0, 7);
      ctx.fill();
    }
  }
}

function hsl(h, s, l) {
  const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = l - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0]; else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x]; else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c]; else [r, g, b] = [c, 0, x];
  return [r + m, g + m, b + m];
}

export default DeltaVerse;
