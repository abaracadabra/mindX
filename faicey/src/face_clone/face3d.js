/**
 * face3d.js — in-house three.js renderer for the cloned face (point cloud / wireframe / themed).
 *
 * Brings the three.js example techniques to the cloned 478-landmark geometry:
 *   - PCD / Kinect point cloud  → THREE.Points of the landmarks ('points', 'glow', 'normal')
 *   - materials_wireframe       → LineSegments from the MediaPipe contour loops ('wireframe')
 *   - morphtargets_webcam       → update(landmarks) per webcam frame = the live talking face
 *   - audio                     → setMouth(open) pushes the lower-face points (lip-sync)
 *
 * Pure three.js (vendored locally, no CDN). The clone studio drives it from lastProfile.landmarks,
 * the live webcam, and the cloned-voice audio. WebGL — needs a browser to render.
 */

import * as THREE from '/static/vendor/three.module.js';
import { CONTOURS, } from './contours.js';
import { LM } from './geometry.js';

export const FACE3D_THEMES = ['points', 'glow', 'normal', 'wireframe', 'reflective', 'modified'];

// lip/jaw indices pushed open by setMouth()
const MOUTH = [LM.lipBot, LM.upperLip, 17, LM.mouthR, LM.mouthL, LM.chin];

export class Face3D {
  constructor(canvas) {
    this.canvas = canvas;
    this.theme = 'points';
    this.hue = 150;
    this.base = null;        // base landmark positions (THREE space) Float32
    this.mouth = 0;
    this.spin = true;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    this.camera.position.set(0, 0, 3);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.group = new THREE.Group();
    this.scene.add(this.group);
    // lights (for the reflective/standard material) + a procedural environment cube map
    this.scene.add(new THREE.HemisphereLight(0x88ffcc, 0x081018, 1.1));
    const dir = new THREE.DirectionalLight(0xffffff, 0.7); dir.position.set(1, 1, 2); this.scene.add(dir);
    this._env = this._makeEnv();
    this._resize();
    this._loop();
  }

  /** Build a self-contained reflective environment cube map from canvas gradients (no CDN/HDR). */
  _makeEnv() {
    const C = 128, faces = [];
    for (let f = 0; f < 6; f++) {
      const cv = document.createElement('canvas'); cv.width = cv.height = C; const c = cv.getContext('2d');
      const g = c.createLinearGradient(0, 0, 0, C);
      g.addColorStop(0, `hsl(${this.hue},80%,60%)`); g.addColorStop(0.5, '#0a1a14'); g.addColorStop(1, '#02060c');
      c.fillStyle = g; c.fillRect(0, 0, C, C);
      c.fillStyle = 'rgba(255,255,255,.55)';
      for (let i = 0; i < 8; i++) c.fillRect((Math.sin(f * 7 + i) * 0.5 + 0.5) * C, (Math.cos(f * 5 + i) * 0.5 + 0.5) * C, 3, 3);
      faces.push(cv);
    }
    const tex = new THREE.CubeTexture(faces); tex.needsUpdate = true; tex.mapping = THREE.CubeReflectionMapping;
    return tex;
  }

  _resize() {
    const w = this.canvas.clientWidth || 300, h = this.canvas.clientHeight || 300;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  /** Map MediaPipe landmarks → centered THREE positions (x right, y up, z toward camera). */
  _toPositions(landmarks) {
    const n = landmarks.length, p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const lm = landmarks[i] || { x: 0.5, y: 0.5, z: 0 };
      p[i * 3] = (lm.x - 0.5) * 2.2;
      p[i * 3 + 1] = -(lm.y - 0.5) * 2.2;
      p[i * 3 + 2] = -(lm.z || 0) * 3.2;
    }
    return p;
  }

  /** Per-vertex rainbow colours from position (a texture-free matcap-ish look). */
  _colors(pos) {
    const c = new Float32Array(pos.length);
    for (let i = 0; i < pos.length; i += 3) {
      c[i] = 0.3 + 0.7 * (pos[i] * 0.5 + 0.5);
      c[i + 1] = 0.3 + 0.7 * (pos[i + 1] * 0.5 + 0.5);
      c[i + 2] = 0.6 + 0.4 * (pos[i + 2] * 0.5 + 0.5);
    }
    return c;
  }

  /** Contour loops → a line index array for the wireframe theme. */
  _lineIndex() {
    const idx = [];
    const closed = new Set(['faceOval', 'rightEye', 'leftEye', 'lipsOuter']);
    for (const [name, loop] of Object.entries(CONTOURS)) {
      for (let i = 0; i < loop.length - 1; i++) idx.push(loop[i], loop[i + 1]);
      if (closed.has(name)) idx.push(loop[loop.length - 1], loop[0]);
    }
    return idx;
  }

  setLandmarks(landmarks) {
    this.base = this._toPositions(landmarks);
    this._build();
  }

  setTheme(name) { this.theme = FACE3D_THEMES.includes(name) ? name : 'points'; this._build(); }
  setHue(h) { this.hue = h; this._env = this._makeEnv(); this._build(); }
  setMouth(open) { this.mouth = Math.max(0, Math.min(1, open)); }

  _accentColor() { const c = new THREE.Color(); c.setHSL((this.hue % 360) / 360, 0.9, 0.55); return c; }

  _build() {
    if (!this.base) return;
    while (this.group.children.length) { const o = this.group.children.pop(); o.geometry?.dispose?.(); o.material?.dispose?.(); }
    this._inst = null; this._modUniforms = null;
    const pos = this.base.slice();
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    let obj;
    if (this.theme === 'wireframe') {
      geo.setIndex(this._lineIndex());
      obj = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: this._accentColor() }));
    } else if (this.theme === 'normal') {
      geo.setAttribute('color', new THREE.BufferAttribute(this._colors(pos), 3));
      obj = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.03, vertexColors: true, sizeAttenuation: true }));
    } else if (this.theme === 'glow') {
      obj = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.05, color: this._accentColor(), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
    } else if (this.theme === 'reflective') {
      // chrome beads — InstancedMesh spheres reflecting the procedural cube env map (webgl_materials_cubemap)
      const sphere = new THREE.IcosahedronGeometry(0.02, 1);
      const mat = new THREE.MeshStandardMaterial({ color: this._accentColor(), metalness: 1, roughness: 0.06, envMap: this._env, envMapIntensity: 1.3 });
      const n = pos.length / 3; const inst = new THREE.InstancedMesh(sphere, mat, n); const m4 = new THREE.Matrix4();
      for (let i = 0; i < n; i++) { m4.makeTranslation(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]); inst.setMatrixAt(i, m4); }
      inst.instanceMatrix.needsUpdate = true; obj = inst; this._inst = inst;
    } else if (this.theme === 'modified') {
      // onBeforeCompile shader injection — a vertical scan-wave over the points (webgl_materials_modified)
      const mat = new THREE.PointsMaterial({ size: 0.04, color: this._accentColor(), sizeAttenuation: true });
      mat.onBeforeCompile = (sh) => {
        sh.uniforms.uTime = { value: 0 };
        sh.vertexShader = 'uniform float uTime;\nvarying float vY;\n' +
          sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vY = position.y;');
        sh.fragmentShader = 'uniform float uTime;\nvarying float vY;\n' +
          sh.fragmentShader.replace('#include <opaque_fragment>',
            '  float w = 0.5 + 0.5 * sin(vY * 7.0 - uTime * 3.0);\n  outgoingLight *= vec3(w, 1.0, 1.0 - 0.6 * w);\n#include <opaque_fragment>');
        this._modUniforms = sh.uniforms;
      };
      obj = new THREE.Points(geo, mat);
    } else {
      obj = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.025, color: this._accentColor(), sizeAttenuation: true }));
    }
    this.group.add(obj);
    this._geo = geo;
  }

  /** Live update positions (webcam reenactment) — the morphtargets_webcam idea. */
  update(landmarks) {
    this.base = this._toPositions(landmarks);
    if (!this._geo || (this._geo.getAttribute('position').array.length !== this.base.length)) return this._build();
    if (!this._inst) { const a = this._geo.getAttribute('position'); a.array.set(this.base); a.needsUpdate = true; }
    // reflective (instanced) updates its matrices in _applyMouth each frame
  }

  _applyMouth() {
    if (!this.base) return;
    const m = this.mouth;
    if (this._inst) { // reflective: rebuild instance matrices (+ mouth) per frame
      const m4 = new THREE.Matrix4(), drop = new Set(MOUTH);
      for (let i = 0; i < this.base.length / 3; i++) {
        const dy = m > 0.01 && drop.has(i) ? -m * 0.18 : 0;
        m4.makeTranslation(this.base[i * 3], this.base[i * 3 + 1] + dy, this.base[i * 3 + 2]);
        this._inst.setMatrixAt(i, m4);
      }
      this._inst.instanceMatrix.needsUpdate = true; return;
    }
    if (!this._geo) return;
    const a = this._geo.getAttribute('position'); const arr = a.array;
    arr.set(this.base);
    if (m > 0.01) for (const i of MOUTH) arr[i * 3 + 1] -= m * 0.18;
    a.needsUpdate = true;
  }

  _loop() {
    this._raf = requestAnimationFrame(() => this._loop());
    if (this.canvas.clientWidth && this.canvas.width !== this.canvas.clientWidth) this._resize();
    if (this.spin) this.group.rotation.y = Math.sin(Date.now() / 2000) * 0.5;
    this._applyMouth();
    if (this._modUniforms) this._modUniforms.uTime.value = Date.now() / 1000;
    this.renderer.render(this.scene, this.camera);
  }

  dispose() { cancelAnimationFrame(this._raf); this.renderer.dispose(); }
}
