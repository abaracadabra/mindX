/**
 * voaice standalone server — spectrometer + oscilloscope demo.
 *
 * Pure Node.js: built-in `http` + Server-Sent Events (no express, no ws). d3 is served
 * locally from node_modules when present (never a CDN). Streams synthetic audio frames
 * analysed in real time by the in-house VoiceAnalyzer. Proves voaice runs independently
 * of faicey (the face) — voice is its own peer.
 *
 *   node server.js            # http://localhost:7350
 */

import { createServer } from 'node:http';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { VoiceAnalyzer } from './src/VoiceAnalyzer.js';
import { waveformPath, spectrumBars } from './src/Oscilloscope.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.VOAICE_PORT || '7350', 10);
const analyzer = new VoiceAnalyzer({ sampleRate: 44100, fftSize: 1024 });

// Locate a local d3 browser build (no CDN). Try voaice, then sibling faicey node_modules.
const d3Candidates = [
  join(__dirname, 'node_modules', 'd3', 'dist', 'd3.min.js'),
  join(__dirname, '..', 'faicey', 'node_modules', 'd3', 'dist', 'd3.min.js'),
];
const d3Path = d3Candidates.find(existsSync) || null;

/** Generate one synthetic audio frame (mix of tones + noise), evolving over time. */
function synthFrame(t, n = 1024) {
  const f = new Float32Array(n);
  const base = 110 + 40 * Math.sin(t / 1.7); // wandering fundamental
  for (let i = 0; i < n; i++) {
    const x = (i / 44100) + t;
    f[i] =
      0.5 * Math.sin(2 * Math.PI * base * x) +
      0.25 * Math.sin(2 * Math.PI * base * 2 * x) +
      0.12 * Math.sin(2 * Math.PI * base * 3 * x) +
      0.05 * (Math.sin(i * 12.9898 + t) * 43758.5453 % 1); // cheap deterministic noise
  }
  return f;
}

const PAGE = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<title>voaice — spectrometer + oscilloscope</title>
<style>
 body{margin:0;background:#05060a;color:#0f8;font-family:'Courier New',monospace}
 h1{color:#0f8;text-align:center;margin:12px}
 .wrap{display:grid;grid-template-rows:1fr 1fr;gap:8px;padding:12px;height:calc(100vh - 70px)}
 svg{width:100%;height:100%;border:1px solid #0f8;background:#001008}
 .feat{position:fixed;top:8px;right:12px;font-size:12px;color:#0fa;text-align:right}
 .feat b{color:#fff}
</style></head><body>
<h1>voaice · live spectrometer + oscilloscope</h1>
<div class="feat" id="feat"></div>
<div class="wrap"><svg id="scope"></svg><svg id="spectrum"></svg></div>
${d3Path
  ? `<script src="/vendor/d3.min.js"></script>`
  : `<!-- d3 not vendored locally; run npm i in voaice or faicey. Falling back to canvas-free SVG. -->`}
<script>
const es = new EventSource('/stream');
const scope = document.getElementById('scope');
const spec = document.getElementById('spectrum');
es.onmessage = (e) => {
  const m = JSON.parse(e.data);
  // oscilloscope (server already computed the SVG path)
  scope.innerHTML = '<path d="'+m.wavePath+'" fill="none" stroke="#0f8" stroke-width="2"/>';
  // spectrum bars
  const W = spec.clientWidth, H = spec.clientHeight, bw = W/m.bars.length;
  spec.innerHTML = m.bars.map((v,i)=>'<rect x="'+(i*bw)+'" y="'+((1-v)*H)+'" width="'+(bw-1)+'" height="'+(v*H)+'" fill="#0fa"/>').join('');
  document.getElementById('feat').innerHTML =
    'pitch <b>'+m.f.pitch.toFixed(1)+'</b> Hz · dom <b>'+m.f.dominantFrequency.toFixed(0)+'</b> Hz<br>'+
    'centroid <b>'+m.f.spectralCentroid.toFixed(0)+'</b> · rolloff <b>'+m.f.spectralRolloff.toFixed(0)+'</b><br>'+
    'rms <b>'+m.f.rms.toFixed(3)+'</b> · flatness <b>'+m.f.flatness.toFixed(3)+'</b>';
};
</script></body></html>`;

const server = createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(PAGE);
    return;
  }
  if (req.url === '/vendor/d3.min.js' && d3Path) {
    res.writeHead(200, { 'Content-Type': 'application/javascript' });
    res.end(readFileSync(d3Path));
    return;
  }
  if (req.url === '/stream') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    let t = 0;
    const timer = setInterval(() => {
      t += 0.05;
      const frame = synthFrame(t, 1024);
      const f = analyzer.analyze(frame);
      const payload = {
        wavePath: waveformPath(frame, 800, 240),
        bars: spectrumBars(f.magnitude, 64),
        f: {
          pitch: f.pitch,
          dominantFrequency: f.dominantFrequency,
          spectralCentroid: f.spectralCentroid,
          spectralRolloff: f.spectralRolloff,
          rms: f.rms,
          flatness: f.flatness,
        },
      };
      res.write(`data: ${JSON.stringify(payload)}\n\n`);
    }, 100);
    req.on('close', () => clearInterval(timer));
    return;
  }
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found', service: 'voaice' }));
});

server.listen(PORT, () => {
  console.log(`🎙️  voaice listening on http://localhost:${PORT}`);
  console.log(`    spectrometer + oscilloscope · d3 ${d3Path ? 'vendored locally' : 'NOT found (run npm i)'} · no CDN`);
});
