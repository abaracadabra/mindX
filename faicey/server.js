/**
 * Faicey 2.0 Server - Demo and Development Server
 *
 * © Professor Codephreak - rage.pythai.net
 * Serves faicey demos and provides API endpoints
 *
 * Usage: node server.js [--port PORT] [--demo DEMO_NAME]
 */

import express from 'express';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
// Faice — the FACE-as-a-service surface (facets -> wireframe FACE, x402-gated).
import {
  attachFaice,
  faiceDescriptor,
  faiceIndex,
  faiceQuote,
  faiceInteract,
  renderFacePage,
} from './src/faice/service.js';
import { faiceX402Gate, requireOverlord } from './src/faice/x402.js';
// Legacy voice-reactive demo agents (JaimlaAgent / FaiceyCore) are loaded LAZILY inside
// initializeDemoAgent so the FACE service boots independently of the voice stack — voice
// concerns now live in the agnostic `voaice` peer package.

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class FaiceyServer {
    constructor(options = {}) {
        this.port = options.port || process.env.PORT || 8080;
        this.demo = options.demo || 'jaimla';

        this.app = express();
        this.server = createServer(this.app);
        this.wss = new WebSocketServer({ server: this.server });

        // Active agents
        this.agents = new Map();
        this.clients = new Set();

        // Demo configurations
        this.demos = {
            jaimla: {
                name: 'Jaimla Agent Demo',
                description: 'Interactive Jaimla - The Machine Learning Agent',
                agentType: 'jaimla',
                endpoint: '/jaimla'
            },
            oscilloscope: {
                name: 'Advanced Oscilloscope',
                description: 'D3.js Voice Analysis Visualization (see voaice)',
                agentType: 'faicey',
                endpoint: '/oscilloscope'
            },
            voiceanalysis: {
                name: 'Voice Analysis Lab',
                description: 'Comprehensive Voice Pattern Analysis (see voaice)',
                agentType: 'faicey',
                endpoint: '/voice-analysis'
            }
        };
    }

    async start() {
        console.log('🎭 Starting Faicey 2.0 Server');
        console.log(`© Professor Codephreak - rage.pythai.net`);
        console.log(`🌟 Serving demo: ${this.demo}`);

        try {
            // Setup middleware
            this.setupMiddleware();

            // Setup routes
            this.setupRoutes();

            // Setup WebSocket
            this.setupWebSocket();

            // Initialize demo agent
            await this.initializeDemoAgent();

            // Start server
            this.server.listen(this.port, () => {
                console.log(`🚀 Faicey server running at http://localhost:${this.port}`);
                console.log(`🎯 Active demo: ${this.demos[this.demo]?.name || 'Unknown'}`);
                console.log(`📡 WebSocket endpoint: ws://localhost:${this.port}`);
            });

        } catch (error) {
            console.error('❌ Server startup failed:', error);
            process.exit(1);
        }
    }

    setupMiddleware() {
        // CORS for development
        this.app.use((req, res, next) => {
            res.header('Access-Control-Allow-Origin', '*');
            res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
            next();
        });

        // JSON parsing
        this.app.use(express.json({ limit: '10mb' }));

        // Static files
        this.app.use('/static', express.static(join(__dirname, 'static')));
        this.app.use('/assets', express.static(join(__dirname, 'assets')));
        // Face-clone ES modules (the in-house clone engine, served for the browser studio).
        this.app.use('/src/face_clone', express.static(join(__dirname, 'src/face_clone')));
    }

    setupRoutes() {
        // Main demo route
        this.app.get('/', (req, res) => {
            this.serveDemoSelector(res);
        });

        // Face clone: single image / perspective images / video → cloned wireframe + 18-dp faceprint.
        this.app.get('/clone-face', (req, res) => {
            res.sendFile(join(__dirname, 'face-clone.html'));
        });
        // The live FACE demo — a real procedural face (features + expressions),
        // webcam/mic ON/OFF, and the voiceprint oscilloscope.
        this.app.get('/face', (req, res) => {
            res.sendFile(join(__dirname, 'face-demo.html'));
        });
        // Persist a clone's faceprint (detection is client-side; this stores the result —
        // the visual parallel of voaice's POST /clone).
        this._faceClones = this._faceClones || [];
        this.app.post('/api/clone-face', (req, res) => {
            const { source, faceprint, registerArgs, proportions } = req.body || {};
            if (!faceprint) return res.status(400).json({ error: 'faceprint required' });
            const record = { source, faceprint, registerArgs, proportions, at: Date.now() };
            this._faceClones.push(record);
            if (this._faceClones.length > 200) this._faceClones.shift();
            res.json({ ok: true, faceprint, stored: this._faceClones.length });
        });
        this.app.get('/api/clone-face/recent', (req, res) => {
            res.json({ clones: (this._faceClones || []).slice(-20).map(c => ({ source: c.source, faceprint: c.faceprint, at: c.at })) });
        });
        // Unified persona print (FACE + VOICE) — registerPersona, the union of face/voice prints.
        this._personas = this._personas || [];
        this.app.post('/api/persona', (req, res) => {
            const { persona, modalities, faceHash, voiceHash } = req.body || {};
            if (!persona) return res.status(400).json({ error: 'persona hash required' });
            this._personas.push({ persona, modalities, faceHash, voiceHash, at: Date.now() });
            if (this._personas.length > 200) this._personas.shift();
            res.json({ ok: true, persona, modalities });
        });
        this.app.get('/api/persona/recent', (req, res) => {
            res.json({ personas: (this._personas || []).slice(-20) });
        });
        // Scientific voiceprint — the REAL voaice measurement (18-dp Scientific
        // measures + Forensic integrity), not the browser estimate. Lazy-imports
        // the voaice peer; degrades honestly (501) when it is not a sibling (e.g.
        // a standalone faicey clone) so the client falls back to its own estimate.
        const _loadVoaice = async () => {
            try { return await import('../voaice/src/index.js'); }
            catch { try { return await import('voaice'); } catch { return null; } }
        };
        // Bound + sanitise a samples payload before it becomes a Float32Array +
        // an FFT: cap the length (≤30 s at 96 kHz) and reject a nonsense rate, so
        // a large or malformed body can't allocate unbounded memory or measure
        // garbage. Returns { buf, sampleRate } or throws a client-safe message.
        const _MAX_SAMPLES = 96000 * 30;
        const _prepSamples = (samples, sampleRate) => {
            if (!Array.isArray(samples) || !samples.length) throw new Error('samples[] required');
            if (samples.length > _MAX_SAMPLES) throw new Error(`too many samples (max ${_MAX_SAMPLES})`);
            const sr = Number(sampleRate) || 24000;
            if (!(sr >= 8000 && sr <= 96000)) throw new Error('sampleRate must be 8000–96000');
            const buf = new Float32Array(samples.length);
            for (let i = 0; i < samples.length; i++) {
                const v = +samples[i];
                buf[i] = Number.isFinite(v) ? Math.max(-1, Math.min(1, v)) : 0; // clamp; NaN → 0
            }
            return { buf, sampleRate: sr };
        };
        this.app.post('/api/voice/measure', async (req, res) => {
            const voaice = await _loadVoaice();
            if (!voaice?.Forensic) return res.status(501).json({ error: 'scientific measurement needs the voaice peer (not installed here)' });
            let prep;
            try { prep = _prepSamples((req.body || {}).samples, (req.body || {}).sampleRate); }
            catch (e) { return res.status(400).json({ error: e.message }); }
            try {
                const { buf, sampleRate } = prep;
                const f = new voaice.Forensic({ sampleRate });
                const print = f.voiceprint(buf);
                const integrity = f.integrity(buf).verdict;
                // features/spread let the client run Forensic.compare for matching
                res.json({
                    features: print.features, spread: print.spread,
                    measuresStr: print.measuresStr, precision: print.precision,
                    hash: print.hash, framesUsed: print.framesUsed, integrity,
                });
            } catch (e) { res.status(500).json({ error: e.message }); }
        });
        // Oscilloscope matching — Forensic.compare of two scientific prints.
        this.app.post('/api/voice/match', async (req, res) => {
            const { a, b } = req.body || {};
            if (!a?.features || !b?.features) return res.status(400).json({ error: 'two prints {features,spread} required' });
            const voaice = await _loadVoaice();
            if (!voaice?.Forensic) return res.status(501).json({ error: 'matching needs the voaice peer (not installed here)' });
            try { res.json(voaice.Forensic.compare(a, b)); }
            catch (e) { res.status(500).json({ error: e.message }); }
        });
        // THE AVATAR SPEAKS — synthesise text, shape the voice toward the cloned
        // voiceprint, and return the samples + the emotion→FACE params. The demo
        // plays the audio and drives lip-sync + expression from it: the cloned
        // face expresses from the cloned voice.
        this.app.post('/api/speak', async (req, res) => {
            const { text, emotion = 'neutral', intensity = 0.8, targetF0 } = req.body || {};
            if (!text || !String(text).trim()) return res.status(400).json({ error: 'text required' });
            const voaice = await _loadVoaice();
            if (!voaice?.PythonSpeech || !voaice?.Forensic) return res.status(501).json({ error: 'speaking needs the voaice peer (TTS + forensic)' });
            let tmp;
            try {
                const py = new voaice.PythonSpeech();
                const cap = await py.available().catch(() => ({ tts: false }));
                if (!cap.tts) return res.status(501).json({ error: 'no Python TTS engine — run voaice/python/install.sh' });
                const { tmpdir } = await import('node:os');
                const { readFileSync, unlinkSync } = await import('node:fs');
                tmp = join(dirname(fileURLToPath(import.meta.url)), '..', 'voaice', 'python', `speak-${process.pid}-${Date.now()}.wav`);
                await py.tts(text, tmp, {});
                let dec = voaice.decodeWav(readFileSync(tmp));
                let clip = { samples: dec.samples, sampleRate: dec.sampleRate };
                // shape toward the cloned voice: pitch-shift the TTS toward the
                // captured voiceprint's F0 so the avatar speaks in ~its own voice.
                let shiftedTo = null;
                if (targetF0 && voaice.VoiceShaper) {
                    const f = new voaice.Forensic({ sampleRate: clip.sampleRate });
                    const f0 = f.voiceprint(clip.samples).features.dominantFrequency;
                    // only shift when BOTH F0s are plausible speech fundamentals — a
                    // harmonic misread (e.g. espeak measuring ~1.5 kHz) would over-shift.
                    const ok = (x) => x >= 70 && x <= 350;
                    if (ok(f0) && ok(targetF0)) {
                        const semis = Math.max(-8, Math.min(8, 12 * Math.log2(targetF0 / f0)));
                        if (Math.abs(semis) > 0.4) { clip = new voaice.VoiceShaper(clip).pitchShift(semis).toClip(); shiftedTo = targetF0; }
                    }
                }
                // emotion → face params (voaice's fan-out — the shared vocabulary)
                const face = voaice.toFace ? voaice.toFace({ label: emotion, intensity }) : { expression: emotion, weight: intensity, hue: 150 };
                res.json({ sampleRate: clip.sampleRate, samples: Array.from(clip.samples, v => Math.round(v * 1e4) / 1e4),
                    face, emotion, shiftedTo });
            } catch (e) { res.status(500).json({ error: e.message }); }
            finally { if (tmp) try { const { unlinkSync } = await import('node:fs'); unlinkSync(tmp); } catch { /* */ } }
        });
        // DeltaVerse iNFT-7857 mint payload — bind a faicey print/persona as an
        // Intelligent NFT (ERC-7857). Returns the exact mintAgent(...) args.
        this.app.post('/api/inft/mint-payload', async (req, res) => {
            try {
                const { toInftMint } = await import('./src/face_clone/inft.js');
                const b = req.body || {};
                const artifact = b.artifact || b.persona || b;
                if (!artifact?.hash) return res.status(400).json({ error: 'a print/persona with a 0x hash is required' });
                const payload = await toInftMint(artifact, {
                    to: b.to, storageURI: b.storageURI, tokenURI: b.tokenURI, thotRoot: b.thotRoot,
                    name: b.name, description: b.description, image: b.image, chainId: b.chainId,
                });
                res.json(payload);
            } catch (e) { res.status(500).json({ error: e.message }); }
        });
        // Network diagnostics ping target (the nose) — a tiny same-origin endpoint.
        this.app.get('/api/net/ping', (req, res) => { res.json({ ok: true, t: Date.now() }); });
        // RAGE search proxy (the left nostril) — best-effort fetch of the WP search
        // index; returns a link to fall back on when the fetch is blocked.
        this.app.get('/api/rage/search', async (req, res) => {
            const q = String(req.query.q || '').slice(0, 120);
            const base = 'https://rage.pythai.net';
            const link = `${base}/?s=${encodeURIComponent(q)}`;
            try {
                const r = await fetch(`${base}/wp-json/wp/v2/search?search=${encodeURIComponent(q)}&per_page=8`, { signal: AbortSignal.timeout(4000) });
                if (!r.ok) throw new Error('status ' + r.status);
                const items = (await r.json()).map((x) => ({ title: x.title, url: x.url }));
                res.json({ ok: true, query: q, items, link });
            } catch (e) { res.json({ ok: false, query: q, items: [], link, reason: e.message }); }
        });
        // Neural renderer capability — honest report. Dormant unless an operator has
        // deposited an ONNX runtime + weights (none are shipped); the fidelity gate
        // caps the verdict at realism until a neural render measures through it.
        this.app.get('/api/render/neural/status', async (req, res) => {
            try {
                const { FIDELITY } = await import('./src/face_clone/neural_render.js');
                res.json({
                    neural: { backend: 'dormant', available: false, reason: 'no ONNX runtime or weights on this host — hyperreal is gated' },
                    fallback: { backend: 'classical', available: true, ops: ['seam-feather', 'unsharp', 'tone'], verdict: 'realism' },
                    gate: FIDELITY,
                    note: 'Without a neural model the classical fallback improves the affine composite (caps at realism). Hyperrealism is EARNED: a neural render must clear identity + structural + coverage. Activate by depositing weights + a runtime.',
                });
            } catch (e) { res.status(500).json({ error: e.message }); }
        });
        // Give a cloned face to a .persona: store a face artifact AND, if the named .persona exists,
        // write embodiment.face (faceprint + cloneProportions) into it so the persona's faicey wears it.
        this.app.post('/api/persona/face', (req, res) => {
            const { persona, faceprint, cloneProportions, registerArgs } = req.body || {};
            if (!faceprint || !cloneProportions) return res.status(400).json({ error: 'faceprint + cloneProportions required' });
            const name = String(persona || faceprint).replace(/[^a-z0-9_-]/gi, '_');
            const dir = dirname(fileURLToPath(import.meta.url));
            // 1) always store a portable face artifact in faicey
            const faceDir = join(dir, 'data', 'persona-faces');
            mkdirSync(faceDir, { recursive: true });
            const embodiment = { engine: 'faicey', faceprint, cloneProportions, registerArgs, note: 'cloned via faicey /clone-face' };
            writeFileSync(join(faceDir, name + '.json'), JSON.stringify(embodiment, null, 2));
            // 2) if a matching .persona exists (mindXtrain personas), write embodiment.face into it
            let personaUpdated = false, personaPath = null;
            try {
                const pPath = join(dir, '..', 'mindx', 'godel', 'mindxtrain', 'personas', name + '.persona');
                if (persona && existsSync(pPath)) {
                    const doc = JSON.parse(readFileSync(pPath, 'utf8'));
                    doc.embodiment = doc.embodiment || {};
                    doc.embodiment.face = { engine: 'faicey', faceprint, cloneProportions, note: 'cloned via faicey /clone-face' };
                    writeFileSync(pPath, JSON.stringify(doc, null, 2) + '\n');
                    personaUpdated = true; personaPath = pPath;
                }
            } catch (e) { /* artifact still stored even if the .persona write fails */ }
            res.json({ ok: true, persona: name, faceprint, personaUpdated, personaPath });
        });

        // ============================================================
        // Faice — the FACE of an AI service (facets -> wireframe FACE)
        // ============================================================
        // Free: service index + known agents
        this.app.get('/api/faice', (req, res) => {
            res.json(faiceIndex());
        });
        // Free: price + privilege verdict for an agent (no gating)
        this.app.get('/api/faice/:agent/quote', attachFaice, (req, res) => {
            res.json(faiceQuote(req));
        });
        // Gated: FACE descriptor JSON — privilege (reputation) OR x402 settlement
        this.app.get(
            '/api/faice/:agent',
            attachFaice,
            faiceX402Gate('/api/faice/:agent'),
            (req, res) => {
                res.json(faiceDescriptor(req));
            }
        );
        // Gated: rendered wireframe FACE page
        this.app.get(
            '/faice/:agent',
            attachFaice,
            faiceX402Gate('/faice/:agent'),
            (req, res) => {
                res.set('Content-Type', 'text/html');
                res.send(renderFacePage(req, this.port));
            }
        );
        // Overlord-only: interact with a FACE (drive expression / override facets).
        // The ultimate privilege — bankon.eth, signature-proven — drives the FACE.
        this.app.post(
            '/api/faice/:agent/interact',
            attachFaice,
            requireOverlord('member'),
            (req, res) => {
                res.json(faiceInteract(req, req.body || {}));
            }
        );

        // Individual demo routes
        this.app.get('/jaimla', (req, res) => {
            this.serveJaimlaDemo(res);
        });

        this.app.get('/oscilloscope', (req, res) => {
            this.serveOscilloscopeDemo(res);
        });

        this.app.get('/voice-analysis', (req, res) => {
            this.serveVoiceAnalysisDemo(res);
        });

        // API routes
        this.app.get('/api/status', (req, res) => {
            this.serveStatus(res);
        });

        this.app.get('/api/agents', (req, res) => {
            this.serveAgentList(res);
        });

        this.app.get('/api/agent/:id', (req, res) => {
            this.serveAgentDetails(req.params.id, res);
        });

        this.app.get('/api/nft/:id', (req, res) => {
            this.serveNFTMetadata(req.params.id, res);
        });

        // Voice data endpoint
        this.app.get('/api/voice-data/:id', (req, res) => {
            this.serveVoiceData(req.params.id, res);
        });

        // Demo assets
        this.app.get('/demo-assets/:file', (req, res) => {
            this.serveDemoAssets(req.params.file, res);
        });

        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ status: 'healthy', timestamp: new Date().toISOString() });
        });
    }

    setupWebSocket() {
        this.wss.on('connection', (ws, req) => {
            console.log(`🔗 Client connected from ${req.socket.remoteAddress}`);
            this.clients.add(ws);

            // Send initial status
            ws.send(JSON.stringify({
                type: 'status',
                data: {
                    server: 'faicey-2.0',
                    demo: this.demo,
                    agents: Array.from(this.agents.keys()),
                    timestamp: Date.now()
                }
            }));

            // Handle messages
            ws.on('message', (message) => {
                try {
                    const data = JSON.parse(message);
                    this.handleWebSocketMessage(ws, data);
                } catch (error) {
                    console.error('WebSocket message error:', error);
                }
            });

            ws.on('close', () => {
                console.log('🔗 Client disconnected');
                this.clients.delete(ws);
            });

            ws.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.clients.delete(ws);
            });
        });

        // Start data streaming
        this.startDataStreaming();
    }

    async initializeDemoAgent() {
        const demoConfig = this.demos[this.demo];
        if (!demoConfig) {
            throw new Error(`Unknown demo: ${this.demo}`);
        }

        console.log(`🤖 Initializing ${demoConfig.name}...`);

        try {
            let agent;

            // Lazy-load the legacy voice agent only when a voice demo is actually served.
            // These modules pull in the voice stack (now belonging to voaice); keeping the
            // import here means the FACE service boots even if the voice stack is absent.
            const isJaimla = demoConfig.agentType === 'jaimla';
            this._isJaimla = isJaimla;
            if (isJaimla) {
                const { JaimlaAgent } = await import('./src/agents/JaimlaAgent.js');
                agent = new JaimlaAgent({ debug: true });
            } else {
                const { FaiceyCore } = await import('./src/FaiceyCore.js');
                agent = new FaiceyCore({
                    agentId: this.demo,
                    persona: 'default',
                    debug: true
                });
            }

            // Setup event listeners
            agent.on('initialized', () => {
                console.log(`✅ ${demoConfig.name} initialized`);
            });

            if (isJaimla) {
                this.setupJaimlaEventListeners(agent);
            } else {
                this.setupFaiceyEventListeners(agent);
            }

            // Initialize agent. agent.init() drives the browser-side pipeline
            // (Web Audio, getUserMedia, WebGLRenderer) which has no equivalent under
            // bare Node. The visible wireframe now renders in the browser via the
            // canonical engine (static/vendor/faicey-engine.js), so a Node-side init
            // failure must NOT stop the HTTP/WebSocket server from serving the demo.
            await agent.init();
            this.agents.set(this.demo, agent);

            console.log(`✅ Demo agent ${this.demo} ready`);

        } catch (error) {
            console.warn(
                `⚠️  Demo agent ${this.demo} could not run its browser pipeline under Node ` +
                `(${error?.message || error}). Serving the engine-driven demo page anyway; ` +
                `rendering happens client-side via static/vendor/faicey-engine.js.`
            );
        }
    }

    setupJaimlaEventListeners(jaimla) {
        jaimla.on('triggerActivated', (data) => {
            this.broadcastToClients('trigger', data);
        });

        jaimla.on('modeChange', (data) => {
            this.broadcastToClients('modeChange', data);
        });

        jaimla.on('collaboration', (data) => {
            this.broadcastToClients('collaboration', data);
        });

        jaimla.on('learning', (data) => {
            this.broadcastToClients('learning', data);
        });

        jaimla.on('discovery', (data) => {
            this.broadcastToClients('discovery', data);
        });

        jaimla.on('empathy', (data) => {
            this.broadcastToClients('empathy', data);
        });
    }

    setupFaiceyEventListeners(faicey) {
        faicey.on('triggerActivated', (data) => {
            this.broadcastToClients('trigger', data);
        });
    }

    startDataStreaming() {
        // Stream voice data every 100ms
        setInterval(() => {
            const agent = this.agents.get(this.demo);
            if (agent && this.clients.size > 0) {
                let voiceData = null;

                if (this._isJaimla) {
                    voiceData = agent.faiceyCore.getVoiceData();
                } else {
                    voiceData = agent.getVoiceData();
                }

                if (voiceData) {
                    this.broadcastToClients('voiceData', voiceData);
                }
            }
        }, 100);

        // Stream analysis data every 50ms for oscilloscope demo
        if (this.demo === 'oscilloscope') {
            setInterval(() => {
                const agent = this.agents.get(this.demo);
                if (agent && this.clients.size > 0) {
                    // Generate advanced analysis data
                    const analysisData = this.generateAnalysisData(agent);
                    this.broadcastToClients('analysis', analysisData);
                }
            }, 50);
        }
    }

    generateAnalysisData(agent) {
        const voiceData = agent.getVoiceData();

        // Calculate RMS
        let rms = 0;
        if (voiceData.timeData) {
            let sum = 0;
            for (let i = 0; i < voiceData.timeData.length; i++) {
                sum += voiceData.timeData[i] * voiceData.timeData[i];
            }
            rms = Math.sqrt(sum / voiceData.timeData.length);
        }

        // Calculate peak
        let peak = 0;
        if (voiceData.timeData) {
            for (let i = 0; i < voiceData.timeData.length; i++) {
                peak = Math.max(peak, Math.abs(voiceData.timeData[i]));
            }
        }

        return {
            rms: rms,
            peak: peak,
            spectralCentroid: voiceData.spectralCentroid || 0,
            spectralRolloff: voiceData.rollOff || 0,
            spectralFlux: 0, // Simplified
            pitch: voiceData.pitch || 0,
            inflection: voiceData.inflection || 0,
            timestamp: Date.now()
        };
    }

    handleWebSocketMessage(ws, data) {
        switch (data.type) {
            case 'getStatus':
                const agent = this.agents.get(this.demo);
                if (agent) {
                    ws.send(JSON.stringify({
                        type: 'status',
                        data: this._isJaimla ? agent.getStatus() : { status: 'active' }
                    }));
                }
                break;

            case 'setExpression':
                const expressionAgent = this.agents.get(this.demo);
                if (expressionAgent) {
                    if (this._isJaimla) {
                        expressionAgent.faiceyCore.targetExpression = data.expression;
                    } else {
                        expressionAgent.targetExpression = data.expression;
                    }
                }
                break;

            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    broadcastToClients(type, data) {
        const message = JSON.stringify({ type, data, timestamp: Date.now() });
        this.clients.forEach(client => {
            if (client.readyState === client.OPEN) {
                client.send(message);
            }
        });
    }

    // Route handlers
    serveDemoSelector(res) {
        const html = this.generateDemoSelectorHTML();
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveJaimlaDemo(res) {
        const html = this.generateJaimlaDemoHTML();
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveOscilloscopeDemo(res) {
        const html = this.generateOscilloscopeDemoHTML();
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveVoiceAnalysisDemo(res) {
        const html = this.generateVoiceAnalysisDemoHTML();
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveStatus(res) {
        const status = {
            server: 'faicey-2.0',
            version: '2.0.0',
            demo: this.demo,
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            agents: Array.from(this.agents.entries()).map(([id, agent]) => ({
                id: id,
                type: agent.constructor.name,
                status: this._isJaimla ? agent.getStatus() : { active: true }
            })),
            clients: this.clients.size,
            timestamp: new Date().toISOString()
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(status, null, 2));
    }

    serveAgentList(res) {
        const agents = Array.from(this.agents.entries()).map(([id, agent]) => ({
            id: id,
            name: agent.name || id,
            type: agent.constructor.name,
            description: agent.description || 'Faicey agent',
            capabilities: agent.capabilities || {},
            nftAvailable: agent.nftAvailable || false
        }));

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(agents, null, 2));
    }

    serveAgentDetails(agentId, res) {
        const agent = this.agents.get(agentId);
        if (!agent) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Agent not found' }));
            return;
        }

        const details = this._isJaimla ? agent.getStatus() : {
            id: agentId,
            type: agent.constructor.name,
            status: 'active'
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(details, null, 2));
    }

    serveNFTMetadata(agentId, res) {
        const agent = this.agents.get(agentId);
        if (!agent) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Agent not found' }));
            return;
        }

        let nftData = {};
        if (this._isJaimla) {
            nftData = agent.exportAgentData();
        } else {
            nftData = agent.exportNFTMetadata ? agent.exportNFTMetadata() : {
                error: 'NFT metadata not available'
            };
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(nftData, null, 2));
    }

    serveVoiceData(agentId, res) {
        const agent = this.agents.get(agentId);
        if (!agent) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Agent not found' }));
            return;
        }

        let voiceData = {};
        if (this._isJaimla) {
            voiceData = agent.faiceyCore.getVoiceData();
        } else {
            voiceData = agent.getVoiceData ? agent.getVoiceData() : {
                error: 'Voice data not available'
            };
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(voiceData, null, 2));
    }

    // HTML generators (simplified - full implementations would be in separate files)
    generateDemoSelectorHTML() {
        const secondary = Object.entries(this.demos).map(([key, demo]) => `
            <a class="card" href="${demo.endpoint}">
              <div class="ct">${demo.name}</div>
              <div class="cd">${demo.description}</div>
              <div class="go">${demo.endpoint} ›</div>
            </a>`).join('');
        return `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>faicey · the FACE of an AI service</title>
<style>
  :root { --grn:#0f8; --grn2:#0fa; --bg:#05060a; --panel:#001008; --amber:#ffb000; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--grn); font-family:'Courier New',ui-monospace,monospace;
    background-image:radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0,255,136,.07), transparent); }
  .wrap { max-width:1000px; margin:0 auto; padding:28px 18px 60px; }
  header { text-align:center; padding:26px 0 18px; }
  header h1 { font-size:30px; letter-spacing:6px; margin:0; color:#fff; }
  header h1 b { color:var(--grn); }
  header p { color:#0a6; font-size:12px; letter-spacing:2px; margin:8px 0 0; }
  .badges { margin-top:14px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
  .badge { font-size:10px; color:#0a6; border:1px solid #063; border-radius:10px; padding:3px 9px; }
  .hero { display:grid; grid-template-columns:1.3fr 1fr; gap:16px; margin:22px 0; border:1px solid var(--grn);
    border-radius:8px; background:var(--panel); overflow:hidden; }
  .hero .copy { padding:24px; }
  .hero h2 { color:var(--grn2); font-size:18px; letter-spacing:1px; margin:0 0 10px; }
  .hero p { color:#0c9; font-size:13px; line-height:1.6; margin:0 0 14px; }
  .hero ul { margin:0 0 18px; padding-left:18px; color:#0a8; font-size:12px; line-height:1.8; }
  .cta { display:inline-block; background:var(--grn); color:#000; text-decoration:none; font-weight:bold;
    letter-spacing:1px; padding:11px 22px; border-radius:4px; font-size:13px; transition:.12s; }
  .cta:hover { background:#fff; }
  .hero .art { background:#000308; display:flex; align-items:center; justify-content:center; border-left:1px solid #063; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; }
  .card { display:block; border:1px solid #063; background:var(--panel); border-radius:6px; padding:16px;
    text-decoration:none; transition:.12s; }
  .card:hover { border-color:var(--grn); background:#021810; transform:translateY(-2px); }
  .ct { color:var(--grn2); font-size:14px; letter-spacing:1px; margin-bottom:6px; }
  .cd { color:#0a8; font-size:11px; line-height:1.5; min-height:30px; }
  .go { color:var(--amber); font-size:11px; margin-top:10px; }
  h3.sec { color:#063; font-size:11px; letter-spacing:3px; margin:30px 0 12px; border-bottom:1px solid #052; padding-bottom:6px; }
  footer { text-align:center; color:#063; font-size:10px; margin-top:40px; letter-spacing:1px; }
  /* mini wireframe face mark */
  svg.face { width:200px; height:200px; }
  @media (max-width:720px){ .hero { grid-template-columns:1fr; } .hero .art { display:none; } }
</style></head>
<body><div class="wrap">
  <header>
    <h1>f<b>ai</b>cey</h1>
    <p>THE FACE OF AN AI SERVICE · WIREFRAME PERSONA · IN-HOUSE · NO CDN</p>
    <div class="badges"><span class="badge">MediaPipe · torch-free</span><span class="badge">478-landmark clone</span>
      <span class="badge">18-decimal faceprint</span><span class="badge">9 emotions</span><span class="badge">3D Three.js</span></div>
  </header>

  <section class="hero">
    <div class="copy">
      <h2>⌖ Clone a face</h2>
      <p>Turn a person into a wireframe Persona — from a single photo, front/left/right perspectives, your
      webcam, or a video clip. The same forensic engine that gives voaice its 18-decimal voiceprint gives
      a face its <b>18-decimal faceprint</b>.</p>
      <ul>
        <li>webcam capture — front · left · right</li>
        <li>478-landmark wireframe + live 3D faicey</li>
        <li>emotes across 9 emotions (in lockstep with the voice)</li>
        <li>registerable faceprint → unified persona (face + voice)</li>
      </ul>
      <a class="cta" href="/clone-face">OPEN FACE CLONE ›</a>
    </div>
    <div class="art">
      <svg class="face" viewBox="0 0 200 200" fill="none" stroke="#0a6" stroke-width="1.3">
        <ellipse cx="100" cy="100" rx="56" ry="78"/>
        <path d="M55 78 L78 74" stroke="#0f8" stroke-width="2"/><path d="M122 74 L145 78" stroke="#0f8" stroke-width="2"/>
        <ellipse cx="74" cy="88" rx="12" ry="7" stroke="#0f8"/><ellipse cx="126" cy="88" rx="12" ry="7" stroke="#0f8"/>
        <circle cx="74" cy="88" r="2.5" fill="#0fa"/><circle cx="126" cy="88" r="2.5" fill="#0fa"/>
        <path d="M100 96 L100 120 M90 124 L110 124" stroke="#0a6"/>
        <path d="M76 142 Q100 158 124 142" stroke="#0f8" stroke-width="2"/>
      </svg>
    </div>
  </section>

  <h3 class="sec">MORE SURFACES</h3>
  <div class="grid">
    <a class="card" href="/clone-face"><div class="ct">⌖ Face Clone Studio</div><div class="cd">single · perspective · webcam · video → wireframe + faceprint + live 3D</div><div class="go">/clone-face ›</div></a>
    ${secondary}
  </div>

  <footer>faicey · peer of voaice (the VOICE) · rage.pythai.net · github.com/agenticplace</footer>
</div></body></html>`;
    }

    generateJaimlaDemoHTML() {
        // Return simplified Jaimla demo HTML
        return `
<!DOCTYPE html>
<html>
<head>
    <title>Jaimla Demo - The Machine Learning Agent</title>
    <!--
      three.js is served locally (no CDN) from the in-repo vendored source via the
      canonical Faicey wireframe engine. The import map below resolves any bare
      three specifier to the locally vendored module; the engine bundle itself
      already inlines three. Both are copied into static/vendor by scripts/sync-engine.mjs.
    -->
    <script type="importmap">
    {
      "imports": {
        "three": "/static/vendor/three.module.js",
        "three/examples/jsm/controls/OrbitControls.js": "/static/vendor/jsm/controls/OrbitControls.js"
      }
    }
    </script>
    <style>
        body { margin: 0; font-family: 'Courier New', monospace; background: #000; color: #fff; }
        .container { display: grid; grid-template-columns: 1fr 400px; height: 100vh; }
        .face-area { background: radial-gradient(ellipse at center, #1a1a1a 0%, #000000 100%); }
        .controls { background: rgba(0, 0, 0, 0.9); padding: 20px; border-left: 2px solid #ff0080; }
        .agent-name { font-size: 2.5em; color: #ff0080; text-align: center; }
        .status { background: rgba(255, 0, 128, 0.1); padding: 15px; border: 1px solid #ff0080; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="face-area">
            <canvas id="face-canvas"></canvas>
        </div>
        <div class="controls">
            <h1 class="agent-name">JAIMLA</h1>
            <p style="text-align: center; color: #ff0080;">"I am the machine learning agent"</p>
            <div class="status">
                <div>Status: <span id="status">Initializing...</span></div>
                <div>Expression: <span id="expression">neutral</span></div>
                <div>Voice Active: <span id="voice-active">false</span></div>
            </div>
        </div>
    </div>

    <script type="module">
        // Canonical wireframe rendering service — the same engine FaceRig uses,
        // built from facerig/src/lib/faicey and served locally (no CDN).
        import { Faicey } from '/static/vendor/faicey-engine.js';

        const canvas = document.getElementById('face-canvas');
        const container = canvas.parentElement;

        const faicey = new Faicey();
        await faicey.init(canvas, {
            width: container.clientWidth,
            height: container.clientHeight,
            wireframe: true,
            faceColor: 0xff0080,   // Jaimla pink
            cameraZ: 5,
        });
        document.getElementById('status').textContent = 'Active';

        // Drive the real morph-target expression engine from the live voice WebSocket.
        const ws = new WebSocket('ws://localhost:${this.port}');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            const expr = msg.data && msg.data.expression;
            if (expr) {
                faicey.setExpression(expr, (msg.data && msg.data.intensity) || 1.0);
                document.getElementById('expression').textContent = expr;
            }
            if (msg.type === 'analysis' && msg.data) {
                document.getElementById('voice-active').textContent =
                    String((msg.data.rms || 0) > 0.01);
            }
        };
    </script>
</body>
</html>`;
    }

    generateOscilloscopeDemoHTML() {
        return `
<!DOCTYPE html>
<html>
<head>
    <title>Advanced Oscilloscope Demo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        body { margin: 0; font-family: 'Courier New', monospace; background: #000; color: #00ff00; }
        h1 { text-align: center; color: #00ff80; }
        #oscilloscope { width: 100%; height: 300px; border: 2px solid #00ff00; background: #001100; }
    </style>
</head>
<body>
    <h1>🌊 Advanced Oscilloscope Demo</h1>
    <svg id="oscilloscope"></svg>

    <script>
        const ws = new WebSocket('ws://localhost:${this.port}');
        const svg = d3.select('#oscilloscope');
        const width = svg.node().clientWidth;
        const height = svg.node().clientHeight;

        const xScale = d3.scaleLinear().domain([0, 1024]).range([0, width]);
        const yScale = d3.scaleLinear().domain([-1, 1]).range([height, 0]);

        svg.append('path')
           .attr('class', 'waveform')
           .style('fill', 'none')
           .style('stroke', '#00ff00')
           .style('stroke-width', 2);

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'voiceData' && msg.data.timeData) {
                const line = d3.line()
                    .x((d, i) => xScale(i))
                    .y(d => yScale(d || 0))
                    .curve(d3.curveCardinal);

                svg.select('.waveform')
                   .datum(msg.data.timeData)
                   .attr('d', line);
            }
        };
    </script>
</body>
</html>`;
    }

    generateVoiceAnalysisDemoHTML() {
        return `
<!DOCTYPE html>
<html>
<head>
    <title>Voice Analysis Lab</title>
    <style>
        body { margin: 0; font-family: 'Courier New', monospace; background: #000; color: #fff; padding: 20px; }
        h1 { text-align: center; color: #00ffff; }
        .analysis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .analysis-panel { border: 2px solid #00ffff; padding: 20px; border-radius: 10px; }
        .stat { margin: 10px 0; padding: 10px; background: rgba(0, 255, 255, 0.1); }
    </style>
</head>
<body>
    <h1>📊 Voice Analysis Lab</h1>
    <div class="analysis-grid">
        <div class="analysis-panel">
            <h3>Real-time Metrics</h3>
            <div class="stat">RMS: <span id="rms">0</span></div>
            <div class="stat">Peak: <span id="peak">0</span></div>
            <div class="stat">Pitch: <span id="pitch">0</span> Hz</div>
        </div>
        <div class="analysis-panel">
            <h3>Voice Features</h3>
            <div class="stat">Spectral Centroid: <span id="centroid">0</span></div>
            <div class="stat">Zero Crossing Rate: <span id="zcr">0</span></div>
            <div class="stat">Inflection: <span id="inflection">0</span></div>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:${this.port}');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'analysis') {
                document.getElementById('rms').textContent = msg.data.rms?.toFixed(4) || '0';
                document.getElementById('peak').textContent = msg.data.peak?.toFixed(4) || '0';
                document.getElementById('pitch').textContent = Math.round(msg.data.pitch || 0);
                document.getElementById('centroid').textContent = Math.round(msg.data.spectralCentroid || 0);
                document.getElementById('zcr').textContent = msg.data.zeroCrossingRate?.toFixed(4) || '0';
                document.getElementById('inflection').textContent = msg.data.inflection?.toFixed(4) || '0';
            }
        };
    </script>
</body>
</html>`;
    }

    async shutdown() {
        console.log('🛑 Shutting down Faicey server...');

        // Shutdown all agents
        for (const [id, agent] of this.agents) {
            console.log(`📴 Shutting down agent: ${id}`);
            if (agent.shutdown) {
                await agent.shutdown();
            }
        }

        // Close WebSocket server
        this.wss.close();

        // Close HTTP server
        this.server.close();

        console.log('✅ Faicey server shutdown complete');
    }
}

// CLI handling
const args = process.argv.slice(2);
const options = {};

for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace('--', '');
    const value = args[i + 1];
    if (key && value) {
        options[key] = value;
    }
}

// Graceful shutdown
const server = new FaiceyServer(options);

process.on('SIGINT', async () => {
    await server.shutdown();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    await server.shutdown();
    process.exit(0);
});

// Start server
server.start().catch(console.error);