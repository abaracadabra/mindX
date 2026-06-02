// SPDX-License-Identifier: Apache-2.0
//
// webgl-bg.js — lightweight full-screen WebGL shader background for the BANKON
// dApp (cypherpunk grid + slow flow, cyan/violet). Self-contained, ~1 draw call
// per frame, throttled, and DEGRADES GRACEFULLY: if WebGL is unavailable or the
// user prefers reduced motion, it no-ops and the CSS vignette stands alone.
//
// Usage:  <canvas id="bg-canvas"></canvas> <script type="module" src="./webgl-bg.js"></script>
(function () {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const gl = canvas.getContext("webgl", { antialias: false, alpha: true, premultipliedAlpha: false });
  if (!gl || reduce) { canvas.style.display = "none"; return; }

  const vsrc = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
  // Subtle animated grid + plasma; tuned dark so foreground stays readable.
  const fsrc = `
  precision highp float;
  uniform vec2 R; uniform float T;
  // hash + value noise
  float h(vec2 x){return fract(sin(dot(x,vec2(41.3,289.1)))*43758.5);}
  float n(vec2 x){vec2 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);
    return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
  void main(){
    vec2 uv=(gl_FragCoord.xy-0.5*R)/R.y;
    float t=T*0.04;
    // flowing field
    float f=n(uv*3.0+vec2(t,t*0.6))*0.6+n(uv*7.0-vec2(t*0.8,t))*0.3;
    // perspective grid lines
    vec2 g=abs(fract(uv*8.0+vec2(0.,t*2.0))-0.5);
    float grid=smoothstep(0.0,0.03,min(g.x,g.y));
    vec3 cyan=vec3(0.22,0.88,1.0), violet=vec3(0.55,0.49,1.0);
    vec3 col=mix(violet,cyan,f);
    col*=0.10+0.10*f;                    // overall very dim
    col+=cyan*(1.0-grid)*0.05;           // faint grid glow
    float vig=smoothstep(1.2,0.2,length(uv));
    gl_FragColor=vec4(col*vig,1.0);
  }`;

  function sh(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, vsrc));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fsrc));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { canvas.style.display = "none"; return; }
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const ploc = gl.getAttribLocation(prog, "p");
  gl.enableVertexAttribArray(ploc);
  gl.vertexAttribPointer(ploc, 2, gl.FLOAT, false, 0, 0);
  const uR = gl.getUniformLocation(prog, "R");
  const uT = gl.getUniformLocation(prog, "T");

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.floor(innerWidth * dpr);
    canvas.height = Math.floor(innerHeight * dpr);
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener("resize", resize);
  resize();

  let start = null, raf = 0, last = 0;
  function frame(ts) {
    if (start === null) start = ts;
    // throttle ~30fps to keep it light
    if (ts - last > 33) {
      gl.uniform2f(uR, canvas.width, canvas.height);
      gl.uniform1f(uT, (ts - start) / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      last = ts;
    }
    raf = requestAnimationFrame(frame);
  }
  // pause when tab hidden
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(raf);
    else raf = requestAnimationFrame(frame);
  });
  raf = requestAnimationFrame(frame);
})();
