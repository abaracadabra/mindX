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
import { NeuralVoiceEngine } from './src/NeuralVoiceEngine.js';
import { EMOTION_LABELS, EMOTIONS, fanOut } from './src/emotion.js';
import { PythonSpeech } from './src/python_speech.js';
import { Forensic } from './src/Forensic.js';
import { VoiceShaper } from './src/VoiceShaper.js';
import { snr } from './src/dsp/noise.js';
import { decodeWav, encodeWav } from './src/audio/wav.js';
import { tmpdir } from 'node:os';
import { readFileSync as _rf, unlinkSync as _rm } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.VOAICE_PORT || '7350', 10);
const analyzer = new VoiceAnalyzer({ sampleRate: 44100, fftSize: 1024 });

// Neural voice engine — the in-house sidecar that voicey2 / faicey call over HTTP. Lazily
// initialised (probes onnxruntime-node + model weights once); degrades to the dependency-free
// fallback source when weights are absent, so /speak always returns valid WAV.
let _neural = null;
async function neural() {
  if (!_neural) {
    _neural = new NeuralVoiceEngine({ agentId: 'voaice-server' });
    await _neural.init();
  }
  return _neural;
}

/** Read a full request body into a Buffer. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function sendJson(res, code, obj) {
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(obj));
}

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

const server = createServer(async (req, res) => {
  const pathname = (req.url || '/').split('?')[0];

  // CORS — let faicey (the FACE peer, different port) POST extracted video audio to /clone etc.
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Reference-Text');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  // Serve the in-house DSP ES modules to the browser (VoiceAnalyzer, Oscilloscope, fft, loudness,
  // vad) so the Voice Lab does REAL analysis client-side — no CDN, same source as the server.
  if (pathname.startsWith('/src/') && pathname.endsWith('.js')) {
    const safe = join(__dirname, 'src', pathname.slice(5).replace(/\.\./g, ''));
    if (existsSync(safe)) {
      res.writeHead(200, { 'Content-Type': 'application/javascript' });
      res.end(readFileSync(safe));
      return;
    }
  }
  // Voice Lab: mic-first scientific oscilloscope + spectrometer + voice editing + 18-dp cloning.
  // the forensic voice lab (elegant corporate panel) — the flagship UI
  if (pathname === '/voicelab' || pathname === '/lab' || pathname === '/forensic' || pathname === '/forensiclab') {
    const p = join(__dirname, 'forensiclab.html');
    if (existsSync(p)) { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end(readFileSync(p)); return; }
  }
  // the original 3-column live oscilloscope lab, kept at /voice
  if (pathname === '/voice') {
    const p = join(__dirname, 'voicelab.html');
    if (existsSync(p)) { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end(readFileSync(p)); return; }
  }

  // ---- forensic voice admin panel routes ----
  const _py = () => (server._pyspeech ||= new PythonSpeech());
  const _measure = (samples, sampleRate) => {
    const buf = Float32Array.from(samples);
    const f = new Forensic({ sampleRate });
    const print = f.voiceprint(buf);
    return { features: print.features, spread: print.spread, precision: print.precision,
      hash: print.hash, integrity: f.integrity(buf).verdict, snr: snr(buf, sampleRate) };
  };
  // every voice/model the installed Python engines expose (all pyttsx3 voices, …)
  if (pathname === '/api/py/voices' && req.method === 'GET') {
    try { sendJson(res, 200, await _py().voices()); }
    catch (e) { sendJson(res, 501, { error: e.message }); }
    return;
  }
  if (pathname === '/api/py/capability' && req.method === 'GET') {
    try { sendJson(res, 200, await _py().capability()); }
    catch (e) { sendJson(res, 501, { error: e.message }); }
    return;
  }
  // synthesise with settings, then MEASURE it (forensic readout travels with the audio)
  if (pathname === '/api/py/tts' && req.method === 'POST') {
    let tmp;
    try {
      const b = JSON.parse((await readBody(req)).toString() || '{}');
      if (!b.text) return sendJson(res, 400, { error: 'text required' });
      tmp = join(tmpdir(), `voicelab-${process.pid}-${Date.now()}.wav`);
      const r = await _py().tts(b.text, tmp, { engine: b.engine, voice: b.voice, rate: b.rate, volume: b.volume });
      let dec = decodeWav(_rf(tmp));
      const measured = _measure(dec.samples, dec.sampleRate);
      sendJson(res, 200, { engine: r.engine, sampleRate: dec.sampleRate,
        samples: Array.from(dec.samples, v => Math.round(v * 1e4) / 1e4), measured });
    } catch (e) { sendJson(res, 500, { error: e.message }); }
    finally { if (tmp && existsSync(tmp)) try { _rm(tmp); } catch { /* */ } }
    return;
  }
  // measure any samples → the six scientific measures + integrity + SNR
  if (pathname === '/api/measure' && req.method === 'POST') {
    try {
      const b = JSON.parse((await readBody(req)).toString() || '{}');
      if (!Array.isArray(b.samples) || !b.samples.length) return sendJson(res, 400, { error: 'samples[] required' });
      sendJson(res, 200, _measure(b.samples, Number(b.sampleRate) || 24000));
    } catch (e) { sendJson(res, 500, { error: e.message }); }
    return;
  }
  // voice MODIFICATION — apply a VoiceShaper chain (pitch/formant/eq/compress/deEss)
  if (pathname === '/api/shape' && req.method === 'POST') {
    try {
      const b = JSON.parse((await readBody(req)).toString() || '{}');
      if (!Array.isArray(b.samples) || !b.samples.length) return sendJson(res, 400, { error: 'samples[] required' });
      const sr = Number(b.sampleRate) || 24000;
      const sh = new VoiceShaper({ samples: Float32Array.from(b.samples), sampleRate: sr });
      const ops = b.ops || {};
      if (ops.pitch) sh.pitchShift(Number(ops.pitch));
      if (ops.formant) sh.formantShift(Number(ops.formant));
      if (ops.eqPeakDb) sh.eq({ type: 'peaking', freq: Number(ops.eqFreq) || 3000, gainDb: Number(ops.eqPeakDb), q: 1 });
      if (ops.compress) sh.compress({ thresholdDb: Number(ops.compress) || -18, ratio: Number(ops.ratio) || 3 });
      if (ops.deEss) sh.deEss();
      const out = sh.toClip();
      sendJson(res, 200, { sampleRate: sr, samples: Array.from(out.samples, v => Math.round(v * 1e4) / 1e4),
        measured: _measure(out.samples, sr) });
    } catch (e) { sendJson(res, 500, { error: e.message }); }
    return;
  }

  // ---- Neural voice engine routes (the in-house /speak sidecar) ----
  if (pathname === '/voices' && req.method === 'GET') {
    const eng = await neural();
    sendJson(res, 200, { voices: eng.listVoices(), capability: eng.capability });
    return;
  }
  // Emotion mapping: the engine-owned emotion model fanned out to voice params + faicey FACE.
  if (pathname === '/emotions' && req.method === 'GET') {
    const u = new URL(req.url, 'http://localhost');
    if (u.searchParams.get('label')) {
      // resolve one (label[,intensity]) → the full fan-out
      sendJson(res, 200, fanOut({ label: u.searchParams.get('label'), intensity: Number(u.searchParams.get('intensity')) }));
      return;
    }
    sendJson(res, 200, { labels: EMOTION_LABELS, table: EMOTIONS });
    return;
  }
  if (pathname === '/speak' && req.method === 'POST') {
    try {
      const body = JSON.parse((await readBody(req)).toString() || '{}');
      const eng = await neural();
      const out = await eng.synthesize({
        text: body.text,
        voiceId: body.voiceId,
        embeddingId: body.embeddingId,
        speed: body.speed,
        numSteps: body.numSteps,
        emotion: body.emotion,
        write: false,
      });
      res.writeHead(200, {
        'Content-Type': 'audio/wav',
        'X-Voaice-Backend': out.backend,
        // the FACE descriptor + tags travel with the audio so consumers (faicey/studio) emote in sync
        'X-Voaice-Emotion': JSON.stringify({ label: out.emotion.label, face: out.emotion.face, tags: out.tags }),
      });
      res.end(out.buffer);
    } catch (err) {
      sendJson(res, 400, { error: err.message, service: 'voaice/speak' });
    }
    return;
  }
  if (pathname === '/clone' && req.method === 'POST') {
    try {
      const ct = req.headers['content-type'] || '';
      const raw = await readBody(req);
      let cloneReq;
      if (ct.includes('application/json')) {
        const body = JSON.parse(raw.toString() || '{}');
        cloneReq = body.wavBase64
          ? { buffer: Buffer.from(body.wavBase64, 'base64'), text: body.referenceText }
          : { wavPath: body.wavPath, text: body.referenceText };
      } else {
        // raw audio/wav upload; transcript (for ZipVoice cloning) via header or query
        const u = new URL(req.url, 'http://localhost');
        cloneReq = { buffer: raw, text: req.headers['x-reference-text'] || u.searchParams.get('referenceText') || '' };
      }
      const eng = await neural();
      const result = await eng.cloneFromReference(cloneReq);
      sendJson(res, 200, {
        embeddingId: result.embeddingId,
        backend: result.backend,
        needsText: result.needsText,
        voiceprint: { hash: result.voiceprint.hash, sampleRate: result.voiceprint.sampleRate },
        registerArgs: eng.scientific.toRegisterArgs(result.voiceprint),
      });
    } catch (err) {
      sendJson(res, 400, { error: err.message, service: 'voaice/clone' });
    }
    return;
  }

  if (req.url === '/' || req.url === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(PAGE);
    return;
  }
  // voaice studio: in-house Persona (oscilloscope-as-mouth) + KITT mode + 18-dp voiceprint.
  if (pathname === '/studio' || pathname === '/studio.html') {
    const studioPath = join(__dirname, 'studio.html');
    if (existsSync(studioPath)) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(readFileSync(studioPath));
      return;
    }
  }
  // emotions showcase: the Persona FACE morphed to every emotion (static grid).
  if (pathname === '/faces' || pathname === '/faces.html') {
    const facesPath = join(__dirname, 'faces.html');
    if (existsSync(facesPath)) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(readFileSync(facesPath));
      return;
    }
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
