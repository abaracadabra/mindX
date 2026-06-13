/**
 * Oscilloscope — waveform + spectrum rendering for voaice.
 *
 * Server side: pure functions that turn sample/spectrum arrays into SVG path/bar data
 * (no dependencies — usable in any Node context).
 * Browser side: a d3-powered live renderer (d3 is served locally by voaice, never a CDN).
 */

/**
 * Build an SVG polyline path for a waveform frame. Pure; no d3 required.
 * @param {Float32Array|number[]} samples values in [-1, 1]
 * @param {number} width  px
 * @param {number} height px
 * @returns {string} SVG path `d` attribute
 */
export function waveformPath(samples, width, height) {
  const n = samples.length;
  if (!n) return '';
  const mid = height / 2;
  let d = '';
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * width;
    const y = mid - samples[i] * mid;
    d += (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2) + ' ';
  }
  return d.trim();
}

/**
 * Reduce a magnitude spectrum to `bins` bar heights (0..1), log-spaced for readability.
 * @param {Float64Array|number[]} mag
 * @param {number} bins
 * @returns {number[]} normalised bar heights
 */
export function spectrumBars(mag, bins = 64) {
  const out = new Array(bins).fill(0);
  if (!mag.length) return out;
  let max = 0;
  for (let b = 0; b < bins; b++) {
    const lo = Math.floor(Math.pow(mag.length, b / bins));
    const hi = Math.max(lo + 1, Math.floor(Math.pow(mag.length, (b + 1) / bins)));
    let acc = 0;
    let c = 0;
    for (let i = lo; i < hi && i < mag.length; i++) {
      acc += mag[i];
      c++;
    }
    const v = c ? acc / c : 0;
    out[b] = v;
    if (v > max) max = v;
  }
  if (max > 0) for (let b = 0; b < bins; b++) out[b] /= max;
  return out;
}

/**
 * Browser-side d3 live oscilloscope script. Returns a <script type="module"> body that
 * connects to a WebSocket emitting {timeData:[], magnitude:[]} and renders both traces.
 * d3 is imported from a local path (default /vendor/d3.min.js) — no CDN.
 * @param {{wsUrl: string, svgId?: string, d3Url?: string, color?: string}} cfg
 */
export function browserRenderer(cfg) {
  const svgId = cfg.svgId || 'scope';
  const d3Url = cfg.d3Url || '/vendor/d3.min.js';
  const color = cfg.color || '#00ff88';
  return `
import * as d3 from '${d3Url}';
const ws = new WebSocket('${cfg.wsUrl}');
const svg = d3.select('#${svgId}');
const W = svg.node().clientWidth, H = svg.node().clientHeight;
const wave = svg.append('path').attr('fill','none').attr('stroke','${color}').attr('stroke-width',2);
const x = d3.scaleLinear().domain([0,1024]).range([0,W]);
const y = d3.scaleLinear().domain([-1,1]).range([H,0]);
const line = d3.line().x((d,i)=>x(i)).y(d=>y(d||0)).curve(d3.curveBasis);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  const t = (msg.data && (msg.data.timeData || msg.data.time_domain)) || msg.timeData;
  if (t && t.length) { x.domain([0, t.length-1]); wave.datum(t).attr('d', line); }
};
`.trim();
}

export const Oscilloscope = { waveformPath, spectrumBars, browserRenderer };
export default Oscilloscope;
