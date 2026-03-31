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
import { JaimlaAgent } from './src/agents/JaimlaAgent.js';
import { FaiceyCore } from './src/FaiceyCore.js';

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
                agent: JaimlaAgent,
                endpoint: '/jaimla'
            },
            oscilloscope: {
                name: 'Advanced Oscilloscope',
                description: 'D3.js Voice Analysis Visualization',
                agent: FaiceyCore,
                endpoint: '/oscilloscope'
            },
            voiceanalysis: {
                name: 'Voice Analysis Lab',
                description: 'Comprehensive Voice Pattern Analysis',
                agent: FaiceyCore,
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
    }

    setupRoutes() {
        // Main demo route
        this.app.get('/', (req, res) => {
            this.serveDemoSelector(res);
        });

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

            if (demoConfig.agent === JaimlaAgent) {
                agent = new JaimlaAgent({ debug: true });
            } else {
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

            if (agent instanceof JaimlaAgent) {
                this.setupJaimlaEventListeners(agent);
            } else {
                this.setupFaiceyEventListeners(agent);
            }

            // Initialize agent
            await agent.init();
            this.agents.set(this.demo, agent);

            console.log(`✅ Demo agent ${this.demo} ready`);

        } catch (error) {
            console.error(`❌ Failed to initialize demo agent:`, error);
            throw error;
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

                if (agent instanceof JaimlaAgent) {
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
                        data: agent instanceof JaimlaAgent ? agent.getStatus() : { status: 'active' }
                    }));
                }
                break;

            case 'setExpression':
                const expressionAgent = this.agents.get(this.demo);
                if (expressionAgent) {
                    if (expressionAgent instanceof JaimlaAgent) {
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
                status: agent instanceof JaimlaAgent ? agent.getStatus() : { active: true }
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

        const details = agent instanceof JaimlaAgent ? agent.getStatus() : {
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
        if (agent instanceof JaimlaAgent) {
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
        if (agent instanceof JaimlaAgent) {
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
        return `
<!DOCTYPE html>
<html>
<head>
    <title>Faicey 2.0 Demo Selector</title>
    <style>
        body { font-family: 'Courier New', monospace; background: #000; color: #00ff00; padding: 20px; }
        h1 { color: #ff0080; text-align: center; }
        .demo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .demo-card { border: 2px solid #00ff00; padding: 20px; border-radius: 10px; text-align: center; }
        .demo-card:hover { background: rgba(0, 255, 0, 0.1); }
        .demo-title { color: #00ffff; font-size: 1.5em; margin-bottom: 10px; }
        .demo-desc { margin: 10px 0; }
        .demo-link { display: inline-block; margin-top: 15px; padding: 10px 20px; background: #ff0080; color: #fff; text-decoration: none; border-radius: 5px; }
        .footer { text-align: center; margin-top: 40px; color: #666; }
    </style>
</head>
<body>
    <h1>🎭 Faicey 2.0 - Demo Selector</h1>
    <p style="text-align: center;">© Professor Codephreak - Advanced Voice-Reactive 3D Face System</p>

    <div class="demo-grid">
        ${Object.entries(this.demos).map(([key, demo]) => `
            <div class="demo-card">
                <div class="demo-title">${demo.name}</div>
                <div class="demo-desc">${demo.description}</div>
                <a href="${demo.endpoint}" class="demo-link">Launch Demo</a>
            </div>
        `).join('')}
    </div>

    <div class="footer">
        <p>🌐 rage.pythai.net | github.com/agenticplace | github.com/cryptoagi</p>
    </div>
</body>
</html>`;
    }

    generateJaimlaDemoHTML() {
        // Return simplified Jaimla demo HTML
        return `
<!DOCTYPE html>
<html>
<head>
    <title>Jaimla Demo - The Machine Learning Agent</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
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

    <script>
        const ws = new WebSocket('ws://localhost:${this.port}');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'status') {
                document.getElementById('status').textContent = 'Active';
                if (msg.data.expression) {
                    document.getElementById('expression').textContent = msg.data.expression;
                }
            }
        };

        // Basic 3D setup
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('face-canvas') });

        const canvas = document.getElementById('face-canvas');
        const container = canvas.parentElement;
        renderer.setSize(container.clientWidth, container.clientHeight);

        // Simple face wireframe
        const geometry = new THREE.RingGeometry(0.5, 1.5, 16);
        const material = new THREE.LineBasicMaterial({ color: 0xff0080 });
        const face = new THREE.LineLoop(geometry, material);
        scene.add(face);

        camera.position.z = 3;

        function animate() {
            requestAnimationFrame(animate);
            face.rotation.y += 0.01;
            renderer.render(scene, camera);
        }
        animate();
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