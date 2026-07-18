/**
 * webgl_face.js — the geometry the WebGL renderer draws.
 *
 * The 2D path (contours.js / render_surface.js) paints triangles with the CPU
 * and an affine per-triangle texture warp — which leaves faint seams and has no
 * true perspective. WebGL draws the SAME mesh on the GPU: real depth, a
 * perspective camera, and perspective-correct texture interpolation (no seams).
 *
 * This module is the pure, headless-testable core — it turns landmarks + a
 * triangle topology into the four buffers three.js needs (positions, indices,
 * uvs, normals). It imports NO three.js, so it is fully unit-tested; the actual
 * WebGL draw lives in face3d.js (Face3D, browser-only).
 *
 *   MediaPipe space (x,y ∈ [0,1] image, y DOWN; z relative depth)
 *     → centred, unit-scaled THREE space (x right, y UP, z toward the viewer)
 *
 * © Professor Codephreak - rage.pythai.net
 */

/**
 * Build the render buffers for a WebGL face mesh.
 * @param {Array<{x,y,z?}|null>} landmarks
 * @param {{topology:Array<[number,number,number]>, uvSource?:Array<{x,y}|null>, scale?:number}} opts
 *   topology  — triangle index list (from render_surface.triangulate); required for a surface
 *   uvSource  — landmarks in the texture's normalized [0,1] space (capture frame); for photoreal
 * @returns {{positions:Float32Array, indices:Uint32Array, uvs:Float32Array,
 *            normals:Float32Array, count:number, center:number[], scale:number}}
 */
export function buildFaceGeometry(landmarks, opts = {}) {
  const n = landmarks.length;
  const topology = opts.topology || [];

  // centroid + scale over the valid landmarks (skip nulls)
  let cx = 0, cy = 0, cz = 0, k = 0;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const lm of landmarks) {
    if (!lm) continue;
    cx += lm.x; cy += lm.y; cz += lm.z || 0; k++;
    if (lm.x < minX) minX = lm.x; if (lm.x > maxX) maxX = lm.x;
    if (lm.y < minY) minY = lm.y; if (lm.y > maxY) maxY = lm.y;
  }
  if (k) { cx /= k; cy /= k; cz /= k; }
  const scale = opts.scale || Math.max(maxX - minX, maxY - minY) || 1;

  const positions = new Float32Array(n * 3);
  const uvs = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    const lm = landmarks[i];
    if (lm) {
      positions[i * 3] = (lm.x - cx) / scale;
      positions[i * 3 + 1] = -(lm.y - cy) / scale;   // flip Y: image-down → GL-up
      positions[i * 3 + 2] = -((lm.z || 0) - cz) / scale; // nose toward the viewer
    }
    // UVs: from the capture frame if given, else the landmark's own image position
    const s = (opts.uvSource && opts.uvSource[i]) || lm;
    if (s) { uvs[i * 2] = clamp01(s.x); uvs[i * 2 + 1] = clamp01(1 - s.y); } // GL texture origin is bottom-left
  }

  const indices = new Uint32Array(topology.length * 3);
  for (let t = 0; t < topology.length; t++) {
    indices[t * 3] = topology[t][0]; indices[t * 3 + 1] = topology[t][1]; indices[t * 3 + 2] = topology[t][2];
  }

  const normals = computeSmoothNormals(positions, topology, n);
  return { positions, indices, uvs, normals, count: topology.length, center: [cx, cy, cz], scale };
}

/** Per-vertex smooth normals accumulated from triangle face normals. */
export function computeSmoothNormals(positions, topology, n) {
  const normals = new Float32Array(n * 3);
  for (const [i, j, k] of topology) {
    const ax = positions[i * 3], ay = positions[i * 3 + 1], az = positions[i * 3 + 2];
    const bx = positions[j * 3], by = positions[j * 3 + 1], bz = positions[j * 3 + 2];
    const cx = positions[k * 3], cy = positions[k * 3 + 1], cz = positions[k * 3 + 2];
    const ux = bx - ax, uy = by - ay, uz = bz - az;
    const vx = cx - ax, vy = cy - ay, vz = cz - az;
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    for (const idx of [i, j, k]) { normals[idx * 3] += nx; normals[idx * 3 + 1] += ny; normals[idx * 3 + 2] += nz; }
  }
  for (let i = 0; i < n; i++) {
    let x = normals[i * 3], y = normals[i * 3 + 1], z = normals[i * 3 + 2];
    const m = Math.hypot(x, y, z);
    if (m > 1e-9) { normals[i * 3] = x / m; normals[i * 3 + 1] = y / m; normals[i * 3 + 2] = z / m; }
    else { normals[i * 3] = 0; normals[i * 3 + 1] = 0; normals[i * 3 + 2] = 1; } // isolated vertex faces viewer
  }
  return normals;
}

function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

// ── mat4 (column-major, WebGL convention) — pure, testable ──────────────────
export function m4identity() { return new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]); }
export function m4perspective(fovy, aspect, near, far) {
  const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far), o = new Float32Array(16);
  o[0] = f / aspect; o[5] = f; o[10] = (far + near) * nf; o[11] = -1; o[14] = 2 * far * near * nf;
  return o;
}
export function m4rotationY(a) { const c = Math.cos(a), s = Math.sin(a), o = m4identity(); o[0] = c; o[2] = -s; o[8] = s; o[10] = c; return o; }
export function m4translation(x, y, z) { const o = m4identity(); o[12] = x; o[13] = y; o[14] = z; return o; }
/** a·b (column-major): the transform b applied, then a. */
export function m4multiply(a, b) {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
    o[c * 4 + r] = s;
  }
  return o;
}

/**
 * WebGLFaceRenderer — a raw-WebGL surface renderer for the face mesh, in the
 * DeltaVerse substrate style (see dapp/deltaverse.js): `getContext('webgl')`,
 * inline shaders, no three.js. GPU perspective + perspective-correct texture
 * interpolation (seam-free, unlike the 2D affine warp). When WebGL is
 * unavailable, `.ok` is false and the caller falls back to the 2D path — the
 * same always-shows contract the DeltaVerse field renderer uses.
 *
 * Browser-only (touches WebGL); the geometry + matrices above are what's tested.
 */
export class WebGLFaceRenderer {
  constructor(canvas, opts = {}) {
    this.canvas = canvas;
    this.mode = opts.mode || 'surface';
    this.skin = opts.skin || [0.84, 0.66, 0.56];
    this.light = opts.light || [-0.3, 0.55, 0.78];
    this.count = 0; this.tex = null; this.ok = false;
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return; // caller falls back to 2D
    this.gl = gl; this._init(); this.ok = true;
  }

  _init() {
    const gl = this.gl;
    const vs = `attribute vec3 aPos; attribute vec3 aNormal; attribute vec2 aUv;
      uniform mat4 uMVP; uniform mat4 uModel; varying vec3 vN; varying vec2 vUv;
      void main(){ vN = mat3(uModel)*aNormal; vUv = aUv; gl_Position = uMVP*vec4(aPos,1.0); }`;
    const fs = `precision mediump float; varying vec3 vN; varying vec2 vUv;
      uniform vec3 uLight; uniform vec3 uSkin; uniform sampler2D uTex; uniform float uUseTex;
      void main(){ vec3 n=normalize(vN); float d=max(0.0,dot(n,normalize(uLight)));
        float shade=0.35+0.65*d; vec3 base = uUseTex>0.5 ? texture2D(uTex,vUv).rgb : uSkin;
        gl_FragColor=vec4(base*shade,1.0); }`;
    const sh = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p); gl.useProgram(p); this.prog = p;
    this.pos = gl.createBuffer(); this.nrm = gl.createBuffer(); this.uv = gl.createBuffer(); this.idx = gl.createBuffer();
    gl.enable(gl.DEPTH_TEST);
  }

  /** Upload a geometry from buildFaceGeometry(). */
  setGeometry(g) {
    const gl = this.gl; if (!gl) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.pos); gl.bufferData(gl.ARRAY_BUFFER, g.positions, gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.nrm); gl.bufferData(gl.ARRAY_BUFFER, g.normals, gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.uv); gl.bufferData(gl.ARRAY_BUFFER, g.uvs, gl.DYNAMIC_DRAW);
    // 16-bit indices when the mesh fits (< 65536 verts) → no OES_element_index_uint needed on WebGL1
    let maxI = 0; for (let i = 0; i < g.indices.length; i++) if (g.indices[i] > maxI) maxI = g.indices[i];
    this.idxType = maxI < 65536 ? gl.UNSIGNED_SHORT : gl.UNSIGNED_INT;
    const idxArr = maxI < 65536 ? new Uint16Array(g.indices) : g.indices;
    if (this.idxType === gl.UNSIGNED_INT) gl.getExtension('OES_element_index_uint');
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.idx); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idxArr, gl.DYNAMIC_DRAW);
    this.count = g.indices.length;
  }

  /** Bind a captured frame (canvas/video/image) as the photoreal texture. */
  setTexture(src) {
    const gl = this.gl; if (!gl || !src) return;
    if (!this.tex) this.tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); // DOM image row order → GL
    try { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src); } catch { return; }
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  }

  setMode(m) { this.mode = m; }
  resize() { const gl = this.gl; if (!gl) return; const dpr = Math.min(2, (typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1); this.canvas.width = this.canvas.clientWidth * dpr; this.canvas.height = this.canvas.clientHeight * dpr; gl.viewport(0, 0, this.canvas.width, this.canvas.height); }

  /** Draw one frame; rotY spins the head so the real 3D depth reads. */
  render({ rotY = 0, dist = 2.4 } = {}) {
    const gl = this.gl; if (!gl || !this.count) return;
    const aspect = this.canvas.width / (this.canvas.height || 1);
    const model = m4rotationY(rotY);
    const mvp = m4multiply(m4multiply(m4perspective(0.8, aspect, 0.1, 100), m4translation(0, 0, -dist)), model);
    this.lastMVP = mvp; // exposed so overlays (the mouth scope) can project to screen
    gl.clearColor(0.02, 0.024, 0.04, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.prog, 'uMVP'), false, mvp);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.prog, 'uModel'), false, model);
    gl.uniform3fv(gl.getUniformLocation(this.prog, 'uLight'), this.light);
    gl.uniform3fv(gl.getUniformLocation(this.prog, 'uSkin'), this.skin);
    const useTex = this.mode === 'photoreal' && this.tex ? 1 : 0;
    gl.uniform1f(gl.getUniformLocation(this.prog, 'uUseTex'), useTex);
    if (useTex) { gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this.tex); gl.uniform1i(gl.getUniformLocation(this.prog, 'uTex'), 0); }
    const bind = (buf, name, size) => { gl.bindBuffer(gl.ARRAY_BUFFER, buf); const l = gl.getAttribLocation(this.prog, name); gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, size, gl.FLOAT, false, 0, 0); };
    bind(this.pos, 'aPos', 3); bind(this.nrm, 'aNormal', 3); bind(this.uv, 'aUv', 2);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.idx);
    gl.drawElements(gl.TRIANGLES, this.count, this.idxType || gl.UNSIGNED_SHORT, 0);
  }

  dispose() { const gl = this.gl; if (!gl) return; [this.pos, this.nrm, this.uv, this.idx].forEach(b => gl.deleteBuffer(b)); if (this.tex) gl.deleteTexture(this.tex); }
}

/**
 * Project a mesh-space point through an MVP to screen (canvas) pixels.
 * @param {number[]} p    [x,y,z] in the same space as buildFaceGeometry positions
 * @param {Float32Array} mvp  column-major MVP (e.g. renderer.lastMVP)
 * @param {number} W, H   canvas size in device pixels
 * @returns {{x,y,w}|null} null when the point is behind the camera (w ≤ 0)
 */
export function projectPoint(p, mvp, W, H) {
  const [x, y, z] = p;
  const cx = mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12];
  const cy = mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13];
  const cw = mvp[3] * x + mvp[7] * y + mvp[11] * z + mvp[15];
  if (cw <= 1e-6) return null;
  return { x: (cx / cw * 0.5 + 0.5) * W, y: (1 - (cy / cw * 0.5 + 0.5)) * H, w: cw };
}

export default buildFaceGeometry;
