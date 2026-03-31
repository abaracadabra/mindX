/**
 * Jaimla Demo - Interactive Voice-Reactive Agent
 *
 * © Professor Codephreak - rage.pythai.net
 * Demonstrates Jaimla's advanced voice analysis and 3D face rendering
 *
 * Usage: node examples/jaimla-demo.js
 */

import { JaimlaAgent } from '../src/agents/JaimlaAgent.js';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';

class JaimlaDemo {
    constructor() {
        this.jaimla = null;
        this.server = null;
        this.wss = null;
        this.clients = new Set();
        this.port = process.env.FAICEY_PORT || 8080;
    }

    async start() {
        console.log('🌸 Starting Jaimla Demo - The Machine Learning Agent');
        console.log('💖 "I am the machine learning agent" - Interactive Voice Demo');

        try {
            // Initialize Jaimla agent
            await this.initJaimla();

            // Start web server for browser demo
            await this.startWebServer();

            // Start WebSocket for real-time data
            this.startWebSocket();

            console.log(`🚀 Jaimla demo running at http://localhost:${this.port}`);
            console.log('🎤 Speak into your microphone to see Jaimla react!');

        } catch (error) {
            console.error('❌ Demo startup failed:', error);
            process.exit(1);
        }
    }

    async initJaimla() {
        this.jaimla = new JaimlaAgent({ debug: true });

        // Set up event listeners
        this.jaimla.on('initialized', () => {
            console.log('✅ Jaimla agent initialized');
        });

        this.jaimla.on('triggerActivated', (data) => {
            console.log(`🎯 Voice trigger: ${data.trigger} -> ${data.response}`);
            this.broadcastToClients('trigger', data);
        });

        this.jaimla.on('modeChange', (data) => {
            console.log(`🔄 Mode change: ${data.mode}`);
            this.broadcastToClients('modeChange', data);
        });

        this.jaimla.on('collaboration', (data) => {
            console.log(`🤝 Collaboration: ${data.mode}`);
            this.broadcastToClients('collaboration', data);
        });

        this.jaimla.on('learning', (data) => {
            console.log(`📚 Learning: ${data.mode}`);
            this.broadcastToClients('learning', data);
        });

        this.jaimla.on('discovery', (data) => {
            console.log(`💡 Discovery: ${data.type}`);
            this.broadcastToClients('discovery', data);
        });

        this.jaimla.on('empathy', (data) => {
            console.log(`💖 Empathy: ${data.response}`);
            this.broadcastToClients('empathy', data);
        });

        // Initialize the agent
        await this.jaimla.init();
    }

    async startWebServer() {
        this.server = createServer((req, res) => {
            if (req.url === '/') {
                this.serveHTML(res);
            } else if (req.url === '/status') {
                this.serveStatus(res);
            } else if (req.url === '/nft') {
                this.serveNFTData(res);
            } else {
                res.writeHead(404);
                res.end('Not Found');
            }
        });

        this.server.listen(this.port);
    }

    startWebSocket() {
        this.wss = new WebSocketServer({ server: this.server });

        this.wss.on('connection', (ws) => {
            console.log('🔗 Client connected to Jaimla demo');
            this.clients.add(ws);

            // Send initial status
            ws.send(JSON.stringify({
                type: 'status',
                data: this.jaimla.getStatus()
            }));

            // Send voice data updates every 100ms
            const voiceInterval = setInterval(() => {
                if (ws.readyState === ws.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'voiceData',
                        data: this.jaimla.faiceyCore.getVoiceData()
                    }));
                }
            }, 100);

            ws.on('close', () => {
                console.log('🔗 Client disconnected from Jaimla demo');
                this.clients.delete(ws);
                clearInterval(voiceInterval);
            });
        });
    }

    broadcastToClients(type, data) {
        const message = JSON.stringify({ type, data });
        this.clients.forEach(client => {
            if (client.readyState === client.OPEN) {
                client.send(message);
            }
        });
    }

    serveHTML(res) {
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jaimla Demo - The Machine Learning Agent</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        body {
            margin: 0;
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a0a1a 100%);
            color: #fff;
            overflow: hidden;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 400px;
            height: 100vh;
        }

        .face-area {
            position: relative;
            background: radial-gradient(ellipse at center, #1a1a1a 0%, #000000 100%);
        }

        .controls-area {
            background: rgba(0, 0, 0, 0.9);
            padding: 20px;
            border-left: 2px solid #ff0080;
            overflow-y: auto;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .agent-name {
            font-size: 2.5em;
            color: #ff0080;
            text-shadow: 0 0 20px #ff0080;
            margin: 0;
        }

        .agent-tagline {
            font-size: 1.2em;
            color: #fff;
            margin: 10px 0;
            opacity: 0.8;
        }

        .status-panel {
            background: rgba(255, 0, 128, 0.1);
            border: 1px solid #ff0080;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }

        .status-title {
            color: #ff0080;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .voice-analysis {
            margin-top: 20px;
        }

        #oscilloscope {
            background: #000;
            border: 1px solid #ff0080;
            border-radius: 5px;
        }

        #frequency-chart {
            background: #000;
            border: 1px solid #00ff80;
            border-radius: 5px;
            margin-top: 10px;
        }

        #inflection-graph {
            background: #000;
            border: 1px solid #00ffff;
            border-radius: 5px;
            margin-top: 10px;
        }

        .trigger-log {
            height: 200px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid #333;
            border-radius: 5px;
            padding: 10px;
            margin-top: 20px;
        }

        .trigger-item {
            padding: 5px;
            border-left: 3px solid #ff0080;
            margin: 5px 0;
            background: rgba(255, 0, 128, 0.1);
        }

        .nft-info {
            text-align: center;
            padding: 20px;
            background: linear-gradient(45deg, #ff0080, #ff4080);
            border-radius: 10px;
            margin-top: 20px;
        }

        .nft-info a {
            color: #fff;
            text-decoration: none;
            font-weight: bold;
        }

        .footer {
            position: fixed;
            bottom: 10px;
            right: 10px;
            font-size: 0.9em;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="face-area">
            <canvas id="face-canvas"></canvas>
        </div>

        <div class="controls-area">
            <div class="header">
                <h1 class="agent-name">JAIMLA</h1>
                <p class="agent-tagline">"I am the machine learning agent"</p>
            </div>

            <div class="status-panel">
                <div class="status-title">Agent Status</div>
                <div id="status-content">Initializing...</div>
            </div>

            <div class="voice-analysis">
                <h3 style="color: #ff0080; margin-bottom: 15px;">Voice Analysis</h3>
                <div>
                    <h4 style="color: #ff0080; margin: 10px 0;">🌊 Oscilloscope</h4>
                    <canvas id="oscilloscope" width="360" height="120"></canvas>
                </div>
                <div>
                    <h4 style="color: #00ff80; margin: 10px 0;">🎵 Frequency</h4>
                    <canvas id="frequency-chart" width="360" height="100"></canvas>
                </div>
                <div>
                    <h4 style="color: #00ffff; margin: 10px 0;">📈 Inflection</h4>
                    <canvas id="inflection-graph" width="360" height="80"></canvas>
                </div>
            </div>

            <div class="trigger-log">
                <div style="color: #ff0080; font-weight: bold; margin-bottom: 10px;">Voice Triggers</div>
                <div id="trigger-list"></div>
            </div>

            <div class="nft-info">
                <div style="font-weight: bold; margin-bottom: 10px;">NFT Available</div>
                <div style="font-size: 0.9em;">
                    <a href="https://github.com/jaimla" target="_blank">GitHub Repository</a><br>
                    <span style="opacity: 0.8;">Available on OpenSea</span>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        © Professor Codephreak - rage.pythai.net
    </div>

    <script>
        class JaimlaDemoClient {
            constructor() {
                this.ws = null;
                this.scene = null;
                this.camera = null;
                this.renderer = null;
                this.faceMesh = null;
                this.triggers = [];

                this.initWebSocket();
                this.init3D();
                this.initCanvases();
            }

            initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                this.ws = new WebSocket(protocol + '//' + window.location.host);

                this.ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                };

                this.ws.onopen = () => {
                    console.log('Connected to Jaimla demo');
                };

                this.ws.onclose = () => {
                    console.log('Disconnected from Jaimla demo');
                    setTimeout(() => this.initWebSocket(), 3000);
                };
            }

            init3D() {
                const canvas = document.getElementById('face-canvas');
                const container = canvas.parentElement;

                this.scene = new THREE.Scene();
                this.camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
                this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

                this.renderer.setSize(container.clientWidth, container.clientHeight);
                this.renderer.setClearColor(0x000000, 0);

                // Create simple Jaimla face representation
                this.createJaimlaFace();

                // Lighting
                const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
                const directionalLight = new THREE.DirectionalLight(0xff0080, 0.8);
                directionalLight.position.set(0, 10, 5);

                this.scene.add(ambientLight);
                this.scene.add(directionalLight);

                this.camera.position.set(0, 0, 5);
                this.camera.lookAt(0, 0, 0);

                // Start render loop
                this.animate();
            }

            createJaimlaFace() {
                // Wireframe face for Jaimla
                const geometry = new THREE.BufferGeometry();

                const vertices = new Float32Array([
                    // Face outline
                    -1.0, 1.2, 0.0,   1.0, 1.2, 0.0,   1.2, 0.8, 0.0,   1.2, -0.8, 0.0,
                     1.0, -1.2, 0.0,  -1.0, -1.2, 0.0,  -1.2, -0.8, 0.0,  -1.2, 0.8, 0.0,
                    // Eyes
                    -0.6, 0.4, 0.1,  -0.3, 0.4, 0.1,  -0.3, 0.2, 0.1,  -0.6, 0.2, 0.1,
                     0.3, 0.4, 0.1,   0.6, 0.4, 0.1,   0.6, 0.2, 0.1,   0.3, 0.2, 0.1,
                    // Nose
                     0.0, 0.1, 0.2,  -0.1, -0.1, 0.15,   0.1, -0.1, 0.15,
                    // Mouth (happy curve)
                    -0.4, -0.4, 0.1,  -0.2, -0.5, 0.1,   0.0, -0.5, 0.1,   0.2, -0.5, 0.1,   0.4, -0.4, 0.1
                ]);

                const indices = new Uint16Array([
                    0,1, 1,2, 2,3, 3,4, 4,5, 5,6, 6,7, 7,0,
                    8,9, 9,10, 10,11, 11,8,
                    12,13, 13,14, 14,15, 15,12,
                    16,17, 16,18, 17,18,
                    19,20, 20,21, 21,22, 22,23
                ]);

                geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
                geometry.setIndex(new THREE.BufferAttribute(indices, 1));

                const material = new THREE.LineBasicMaterial({
                    color: 0xff0080,
                    linewidth: 2
                });

                this.faceMesh = new THREE.LineSegments(geometry, material);
                this.scene.add(this.faceMesh);
            }

            animate() {
                requestAnimationFrame(() => this.animate());

                // Gentle rotation
                if (this.faceMesh) {
                    this.faceMesh.rotation.y += 0.002;
                }

                this.renderer.render(this.scene, this.camera);
            }

            initCanvases() {
                this.oscCanvas = document.getElementById('oscilloscope');
                this.freqCanvas = document.getElementById('frequency-chart');
                this.inflCanvas = document.getElementById('inflection-graph');

                this.oscCtx = this.oscCanvas.getContext('2d');
                this.freqCtx = this.freqCanvas.getContext('2d');
                this.inflCtx = this.inflCanvas.getContext('2d');
            }

            handleMessage(message) {
                switch (message.type) {
                    case 'status':
                        this.updateStatus(message.data);
                        break;
                    case 'voiceData':
                        this.updateVoiceVisuals(message.data);
                        break;
                    case 'trigger':
                        this.addTrigger(message.data);
                        break;
                    default:
                        console.log('Received:', message);
                }
            }

            updateStatus(status) {
                const content = document.getElementById('status-content');
                content.innerHTML = \`
                    <div>Expression: \${status.expression}</div>
                    <div>Target: \${status.targetExpression}</div>
                    <div>Interactions: \${status.interactionCount}</div>
                    <div>Processing: \${status.processingState?.fusionMode ? 'Multimodal' : 'Standard'}</div>
                \`;
            }

            updateVoiceVisuals(voiceData) {
                this.drawOscilloscope(voiceData.timeData);
                this.drawFrequencyChart(voiceData.frequencies);
                this.drawInflectionGraph(voiceData.inflection);
            }

            drawOscilloscope(timeData) {
                if (!timeData || !this.oscCtx) return;

                const ctx = this.oscCtx;
                const canvas = this.oscCanvas;

                ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.strokeStyle = '#ff0080';
                ctx.lineWidth = 2;
                ctx.beginPath();

                const sliceWidth = canvas.width / timeData.length;
                let x = 0;

                for (let i = 0; i < timeData.length; i++) {
                    const v = (timeData[i] + 1) / 2; // Normalize to 0-1
                    const y = v * canvas.height;

                    if (i === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }

                    x += sliceWidth;
                }

                ctx.stroke();
            }

            drawFrequencyChart(frequencies) {
                if (!frequencies || !this.freqCtx) return;

                const ctx = this.freqCtx;
                const canvas = this.freqCanvas;

                ctx.fillStyle = '#000';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.fillStyle = '#00ff80';

                const barWidth = canvas.width / frequencies.length;

                for (let i = 0; i < frequencies.length; i++) {
                    const magnitude = Math.max(0, (frequencies[i] + 100) / 100); // Normalize
                    const barHeight = magnitude * canvas.height;

                    ctx.fillRect(i * barWidth, canvas.height - barHeight, barWidth - 1, barHeight);
                }
            }

            drawInflectionGraph(inflection) {
                // Simple inflection visualization
                if (!this.inflCtx) return;

                const ctx = this.inflCtx;
                const canvas = this.inflCanvas;

                // Shift existing data left
                const imageData = ctx.getImageData(1, 0, canvas.width - 1, canvas.height);
                ctx.putImageData(imageData, 0, 0);

                // Clear rightmost column
                ctx.fillStyle = '#000';
                ctx.fillRect(canvas.width - 1, 0, 1, canvas.height);

                // Draw new inflection point
                ctx.fillStyle = '#00ffff';
                const y = canvas.height / 2 - (inflection || 0) * (canvas.height / 4);
                ctx.fillRect(canvas.width - 1, y - 1, 1, 2);
            }

            addTrigger(trigger) {
                this.triggers.unshift(trigger);
                if (this.triggers.length > 10) {
                    this.triggers = this.triggers.slice(0, 10);
                }

                const triggerList = document.getElementById('trigger-list');
                triggerList.innerHTML = this.triggers.map(t => \`
                    <div class="trigger-item">
                        <strong>\${t.trigger}</strong> → \${t.response}<br>
                        <small>Expression: \${t.expression}</small>
                    </div>
                \`).join('');
            }
        }

        // Start demo when page loads
        window.addEventListener('load', () => {
            new JaimlaDemoClient();
        });
    </script>
</body>
</html>
        `;

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveStatus(res) {
        const status = this.jaimla ? this.jaimla.getStatus() : { error: 'Agent not initialized' };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(status, null, 2));
    }

    serveNFTData(res) {
        const nftData = this.jaimla ? this.jaimla.exportAgentData() : { error: 'Agent not initialized' };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(nftData, null, 2));
    }

    async shutdown() {
        console.log('🛑 Shutting down Jaimla demo...');

        if (this.jaimla) {
            await this.jaimla.shutdown();
        }

        if (this.wss) {
            this.wss.close();
        }

        if (this.server) {
            this.server.close();
        }

        console.log('✅ Jaimla demo shutdown complete');
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    if (global.demo) {
        await global.demo.shutdown();
    }
    process.exit(0);
});

// Start demo
const demo = new JaimlaDemo();
global.demo = demo;
demo.start().catch(console.error);