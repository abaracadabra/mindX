/**
 * Enhanced Jaimla Demo - Complete Voice-Reactive Agent with Background Integration
 *
 * © Professor Codephreak - rage.pythai.net
 * Demonstrates enhanced Jaimla with voice creation, background interactions, and modular integration
 *
 * Usage: node examples/enhanced-jaimla-demo.js
 */

import { EnhancedJaimlaAgent } from '../src/agents/EnhancedJaimlaAgent.js';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';

class EnhancedJaimlaDemo {
    constructor() {
        this.jaimla = null;
        this.server = null;
        this.wss = null;
        this.clients = new Set();
        this.port = process.env.ENHANCED_JAIMLA_PORT || 8082;
        this.demoMode = process.argv.includes('--demo');
        this.voiceEnabled = !process.argv.includes('--no-voice');
    }

    async start() {
        console.log('🌸 Starting Enhanced Jaimla Demo');
        console.log('💖 "I am the machine learning agent" - Enhanced Edition');
        console.log('🎭 Features: Voice Creation, Background Interaction, Modular Integration');

        try {
            // Initialize enhanced Jaimla
            await this.initEnhancedJaimla();

            // Start web server for demo interface
            await this.startWebServer();

            // Start WebSocket for real-time updates
            this.startWebSocket();

            // Start demo scenarios
            if (this.demoMode) {
                this.startDemoScenarios();
            }

            console.log(`🚀 Enhanced Jaimla demo running at http://localhost:${this.port}`);
            console.log('🎤 Voice creation enabled, speak to interact!');
            console.log('🌐 Background integration active');
            console.log('🔗 Modular systems connected');

        } catch (error) {
            console.error('❌ Enhanced demo startup failed:', error);
            process.exit(1);
        }
    }

    async initEnhancedJaimla() {
        this.jaimla = new EnhancedJaimlaAgent({
            debug: true,
            autonomousVoice: this.voiceEnabled,
            autonomousMode: true,
            ttsEngine: 'espeak-ng'
        });

        // Enhanced event listeners
        this.jaimla.on('enhanced-initialized', (data) => {
            console.log('✅ Enhanced Jaimla fully initialized');
            this.broadcastToClients('enhanced-initialized', data);
        });

        this.jaimla.on('enhanced-trigger', (data) => {
            console.log(`🎯 Enhanced trigger: ${data.trigger}`);
            this.broadcastToClients('enhanced-trigger', data);
        });

        this.jaimla.on('enhanced-mode-change', (data) => {
            console.log(`🔄 Enhanced mode: ${data.mode}`);
            this.broadcastToClients('enhanced-mode-change', data);
        });

        this.jaimla.on('enhanced-collaboration', (data) => {
            console.log(`🤝 Enhanced collaboration`);
            this.broadcastToClients('enhanced-collaboration', data);
        });

        this.jaimla.on('background-connected', (data) => {
            console.log('🌐 Background systems connected');
            this.broadcastToClients('background-connected', data);
        });

        this.jaimla.on('voice-bridge-ready', (data) => {
            console.log('🗣️ Voice bridge ready');
            this.broadcastToClients('voice-bridge-ready', data);
        });

        this.jaimla.on('background-agent-discovery', (data) => {
            console.log(`🔍 Background agent discovery: ${data.similarAgents?.length || 0} agents`);
            this.broadcastToClients('background-agent-discovery', data);
        });

        this.jaimla.on('speech-error', (data) => {
            console.error('🗣️ Speech error:', data.error);
        });

        // Initialize the enhanced agent
        await this.jaimla.init();
    }

    async startWebServer() {
        this.server = createServer((req, res) => {
            if (req.url === '/') {
                this.serveEnhancedDemo(res);
            } else if (req.url === '/status') {
                this.serveEnhancedStatus(res);
            } else if (req.url === '/capabilities') {
                this.serveCapabilities(res);
            } else if (req.url === '/voice-test') {
                this.handleVoiceTest(res);
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
            console.log('🔗 Client connected to enhanced demo');
            this.clients.add(ws);

            // Send initial status
            ws.send(JSON.stringify({
                type: 'enhanced-status',
                data: this.jaimla ? this.jaimla.getEnhancedStatus() : { status: 'initializing' }
            }));

            // Handle client messages
            ws.on('message', async (message) => {
                try {
                    const data = JSON.parse(message);
                    await this.handleWebSocketMessage(ws, data);
                } catch (error) {
                    console.error('WebSocket message error:', error);
                }
            });

            ws.on('close', () => {
                console.log('🔗 Client disconnected from enhanced demo');
                this.clients.delete(ws);
            });
        });

        // Send periodic updates
        setInterval(() => {
            if (this.jaimla && this.clients.size > 0) {
                this.broadcastToClients('status-update', this.jaimla.getEnhancedStatus());
            }
        }, 5000); // Every 5 seconds
    }

    async handleWebSocketMessage(ws, data) {
        switch (data.type) {
            case 'speak-request':
                if (this.jaimla && data.text) {
                    try {
                        await this.jaimla.speak(data.text, data.options || {});
                        ws.send(JSON.stringify({
                            type: 'speak-response',
                            success: true,
                            text: data.text
                        }));
                    } catch (error) {
                        ws.send(JSON.stringify({
                            type: 'speak-response',
                            success: false,
                            error: error.message
                        }));
                    }
                }
                break;

            case 'trigger-background':
                if (this.jaimla && data.action) {
                    try {
                        const result = await this.jaimla.backgroundManager.triggerResponse(data.action, data.context || {});
                        ws.send(JSON.stringify({
                            type: 'background-response',
                            success: result.success,
                            action: data.action,
                            result: result
                        }));
                    } catch (error) {
                        ws.send(JSON.stringify({
                            type: 'background-response',
                            success: false,
                            error: error.message
                        }));
                    }
                }
                break;

            case 'get-capabilities':
                ws.send(JSON.stringify({
                    type: 'capabilities',
                    data: this.jaimla ? this.jaimla.getCapabilities() : {}
                }));
                break;

            default:
                console.log(`Unknown WebSocket message type: ${data.type}`);
        }
    }

    startDemoScenarios() {
        console.log('🎭 Starting demo scenarios...');

        // Scenario 1: Voice greeting and introduction (5 seconds)
        setTimeout(async () => {
            if (this.jaimla && this.voiceEnabled) {
                await this.jaimla.speak("Welcome to my enhanced demonstration! I'm Jaimla, your machine learning agent with advanced voice and background capabilities.");
            }
        }, 5000);

        // Scenario 2: Background agent discovery (15 seconds)
        setTimeout(async () => {
            console.log('🔍 Demo: Triggering agent discovery...');
            await this.jaimla.backgroundManager.triggerResponse('agent-discovery', {
                category: 'analytical',
                minScore: 80
            });
        }, 15000);

        // Scenario 3: Collaboration demonstration (30 seconds)
        setTimeout(async () => {
            console.log('🤝 Demo: Triggering collaboration mode...');
            await this.jaimla.backgroundManager.triggerResponse('collaboration', {
                partners: ['research-agent', 'analysis-agent']
            });
        }, 30000);

        // Scenario 4: Voice characteristics demonstration (45 seconds)
        setTimeout(async () => {
            if (this.jaimla && this.voiceEnabled) {
                await this.jaimla.speak("Let me demonstrate different vocal expressions and inflections!", {
                    pitch: 10,
                    speed: 20,
                    energy: 1.0
                });
            }
        }, 45000);

        // Scenario 5: Learning demonstration (60 seconds)
        setTimeout(async () => {
            console.log('📚 Demo: Triggering learning mode...');
            this.jaimla.baseAgent.emit('learning', {
                mode: 'active',
                source: 'demo-interaction',
                data: { pattern: 'user-engagement', confidence: 0.95 }
            });
        }, 60000);

        // Scenario 6: Background status check (75 seconds)
        setTimeout(async () => {
            console.log('📊 Demo: Background status check...');
            await this.jaimla.backgroundManager.triggerResponse('status-check');
        }, 75000);

        console.log('✅ Demo scenarios scheduled');
    }

    broadcastToClients(type, data) {
        const message = JSON.stringify({ type, data, timestamp: Date.now() });
        this.clients.forEach(client => {
            if (client.readyState === client.OPEN) {
                client.send(message);
            }
        });
    }

    // Serve enhanced demo HTML
    serveEnhancedDemo(res) {
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Jaimla Demo - Voice & Background Integration</title>
    <style>
        body {
            margin: 0;
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #1a0a1a 0%, #2d1b2d 100%);
            color: #fff;
            overflow-x: hidden;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr;
            height: 100vh;
            gap: 20px;
            padding: 20px;
        }

        .header {
            grid-column: 1 / 3;
            text-align: center;
            background: rgba(255, 0, 128, 0.1);
            padding: 30px;
            border-radius: 15px;
            border: 2px solid #ff0080;
        }

        .agent-name {
            font-size: 3rem;
            color: #ff0080;
            text-shadow: 0 0 20px #ff0080;
            margin: 0;
        }

        .agent-tagline {
            font-size: 1.3rem;
            color: #fff;
            margin: 10px 0 0 0;
            opacity: 0.9;
        }

        .left-panel, .right-panel {
            background: rgba(0, 0, 0, 0.7);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid #444;
            overflow-y: auto;
        }

        .panel-title {
            color: #ff0080;
            font-size: 1.5rem;
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid #ff0080;
            padding-bottom: 10px;
        }

        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
        }

        .status-card {
            background: rgba(255, 0, 128, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #ff0080;
        }

        .status-label {
            font-size: 0.9rem;
            color: #ccc;
            margin-bottom: 5px;
        }

        .status-value {
            font-size: 1.1rem;
            color: #ff0080;
            font-weight: bold;
        }

        .controls {
            margin: 20px 0;
        }

        .control-group {
            margin-bottom: 20px;
        }

        .control-label {
            color: #00ff80;
            font-weight: bold;
            margin-bottom: 10px;
            display: block;
        }

        input, textarea, button {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #444;
            background: rgba(0, 0, 0, 0.5);
            color: #fff;
            border-radius: 5px;
            font-family: inherit;
        }

        button {
            background: linear-gradient(135deg, #ff0080, #ff4080);
            border: none;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }

        button:hover {
            background: linear-gradient(135deg, #ff4080, #ff8080);
            transform: translateY(-2px);
        }

        .log {
            height: 300px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.8);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #00ff80;
            font-size: 0.9rem;
        }

        .log-entry {
            margin: 5px 0;
            padding: 8px;
            border-left: 3px solid;
            background: rgba(255, 255, 255, 0.05);
        }

        .log-enhanced { border-color: #ff0080; }
        .log-voice { border-color: #00ff80; }
        .log-background { border-color: #00ffff; }
        .log-error { border-color: #ff4444; }

        .capabilities {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }

        .capability {
            background: rgba(0, 255, 0, 0.1);
            padding: 8px 12px;
            border-radius: 20px;
            text-align: center;
            border: 1px solid #00ff80;
            font-size: 0.8rem;
        }

        .footer {
            position: fixed;
            bottom: 10px;
            right: 10px;
            font-size: 0.9rem;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="agent-name">ENHANCED JAIMLA</h1>
            <p class="agent-tagline">"I am the machine learning agent" - Enhanced Edition</p>
            <div style="margin-top: 15px; color: #00ff80;">
                🗣️ Voice Creation | 🌐 Background Integration | 🔗 Modular Systems
            </div>
        </div>

        <div class="left-panel">
            <h2 class="panel-title">🎭 Agent Status</h2>

            <div class="status-grid">
                <div class="status-card">
                    <div class="status-label">Voice Status</div>
                    <div class="status-value" id="voice-status">Initializing...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Background</div>
                    <div class="status-value" id="background-status">Connecting...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Expression</div>
                    <div class="status-value" id="expression-status">neutral</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Mode</div>
                    <div class="status-value" id="mode-status">initializing</div>
                </div>
            </div>

            <div class="capabilities" id="capabilities-list">
                <div class="capability">Voice Creation</div>
                <div class="capability">Background Interaction</div>
                <div class="capability">Modular Integration</div>
                <div class="capability">Autonomous Response</div>
                <div class="capability">Marketplace Integration</div>
                <div class="capability">BANKON Workflow</div>
            </div>

            <div class="controls">
                <div class="control-group">
                    <label class="control-label">🗣️ Voice Input</label>
                    <textarea id="speech-input" placeholder="Enter text for Jaimla to speak..." rows="3"></textarea>
                    <button onclick="requestSpeech()">Make Jaimla Speak</button>
                </div>

                <div class="control-group">
                    <label class="control-label">🌐 Background Actions</label>
                    <select id="background-action">
                        <option value="agent-discovery">Agent Discovery</option>
                        <option value="collaboration">Start Collaboration</option>
                        <option value="status-check">Status Check</option>
                    </select>
                    <button onclick="triggerBackground()">Trigger Action</button>
                </div>
            </div>
        </div>

        <div class="right-panel">
            <h2 class="panel-title">📊 Live Activity Log</h2>
            <div class="log" id="activity-log"></div>

            <div style="margin-top: 20px;">
                <button onclick="getCapabilities()">Refresh Capabilities</button>
                <button onclick="getStatus()">Get Full Status</button>
                <button onclick="clearLog()">Clear Log</button>
            </div>
        </div>
    </div>

    <div class="footer">
        © Professor Codephreak - Enhanced Jaimla Demo
    </div>

    <script>
        let ws = null;
        let logEntries = [];

        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host);

            ws.onopen = () => {
                addLog('enhanced', 'Connected to Enhanced Jaimla');
                ws.send(JSON.stringify({ type: 'get-capabilities' }));
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };

            ws.onclose = () => {
                addLog('error', 'Connection lost, attempting to reconnect...');
                setTimeout(initWebSocket, 3000);
            };

            ws.onerror = (error) => {
                addLog('error', 'WebSocket error: ' + error.message);
            };
        }

        function handleWebSocketMessage(message) {
            switch (message.type) {
                case 'enhanced-status':
                    updateStatus(message.data);
                    break;
                case 'enhanced-initialized':
                    addLog('enhanced', 'Enhanced Jaimla fully initialized');
                    document.getElementById('voice-status').textContent = 'Ready';
                    document.getElementById('background-status').textContent = 'Connected';
                    break;
                case 'enhanced-trigger':
                    addLog('enhanced', \`Trigger: \${message.data.trigger} → \${message.data.response}\`);
                    break;
                case 'voice-bridge-ready':
                    addLog('voice', 'Voice bridge initialized and ready');
                    document.getElementById('voice-status').textContent = 'Active';
                    break;
                case 'background-connected':
                    addLog('background', 'Background systems connected');
                    document.getElementById('background-status').textContent = 'Active';
                    break;
                case 'background-agent-discovery':
                    addLog('background', \`Agent discovery: \${message.data.similarAgents?.length || 0} agents found\`);
                    break;
                case 'speak-response':
                    if (message.success) {
                        addLog('voice', \`Speech generated: "\${message.text}"\`);
                    } else {
                        addLog('error', \`Speech failed: \${message.error}\`);
                    }
                    break;
                case 'background-response':
                    if (message.success) {
                        addLog('background', \`Action \${message.action} completed successfully\`);
                    } else {
                        addLog('error', \`Background action failed: \${message.error}\`);
                    }
                    break;
                case 'capabilities':
                    updateCapabilities(message.data);
                    break;
                default:
                    addLog('enhanced', \`\${message.type}: \${JSON.stringify(message.data).substring(0, 100)}\`);
            }
        }

        function updateStatus(status) {
            if (status.base?.expression) {
                document.getElementById('expression-status').textContent = status.base.expression;
            }
            if (status.enhanced) {
                document.getElementById('voice-status').textContent = status.enhanced.voiceEnabled ? 'Active' : 'Disabled';
                document.getElementById('background-status').textContent = status.enhanced.backgroundCapable ? 'Active' : 'Disabled';
            }
        }

        function updateCapabilities(capabilities) {
            const capList = document.getElementById('capabilities-list');
            capList.innerHTML = '';

            // Base capabilities
            if (capabilities.base) {
                Object.keys(capabilities.base).forEach(cap => {
                    if (capabilities.base[cap]) {
                        const div = document.createElement('div');
                        div.className = 'capability';
                        div.textContent = cap.replace(/([A-Z])/g, ' $1').trim();
                        capList.appendChild(div);
                    }
                });
            }

            // Enhanced capabilities
            if (capabilities.enhanced) {
                Object.keys(capabilities.enhanced).forEach(cap => {
                    if (capabilities.enhanced[cap]) {
                        const div = document.createElement('div');
                        div.className = 'capability';
                        div.style.borderColor = '#ff0080';
                        div.textContent = cap.replace(/([A-Z])/g, ' $1').trim() + ' ✨';
                        capList.appendChild(div);
                    }
                });
            }
        }

        function addLog(type, message) {
            const timestamp = new Date().toTimeString().slice(0, 8);
            logEntries.unshift({ type, message, timestamp });

            if (logEntries.length > 100) {
                logEntries = logEntries.slice(0, 100);
            }

            updateLog();
        }

        function updateLog() {
            const log = document.getElementById('activity-log');
            log.innerHTML = logEntries.map(entry => \`
                <div class="log-entry log-\${entry.type}">
                    <strong>\${entry.timestamp}</strong> [\${entry.type.toUpperCase()}] \${entry.message}
                </div>
            \`).join('');
        }

        function requestSpeech() {
            const text = document.getElementById('speech-input').value.trim();
            if (text && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'speak-request',
                    text: text,
                    options: { voiceId: 'jaimla' }
                }));
                document.getElementById('speech-input').value = '';
                addLog('voice', \`Requesting speech: "\${text}"\`);
            }
        }

        function triggerBackground() {
            const action = document.getElementById('background-action').value;
            if (action && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'trigger-background',
                    action: action,
                    context: { source: 'demo-interface' }
                }));
                addLog('background', \`Triggering: \${action}\`);
            }
        }

        function getCapabilities() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'get-capabilities' }));
                addLog('enhanced', 'Requesting capabilities update');
            }
        }

        function getStatus() {
            addLog('enhanced', 'Status: Enhanced Jaimla running with full capabilities');
        }

        function clearLog() {
            logEntries = [];
            updateLog();
        }

        // Initialize on page load
        window.addEventListener('load', () => {
            initWebSocket();
        });

        // Handle enter key in text area
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && event.target.id === 'speech-input' && event.ctrlKey) {
                requestSpeech();
            }
        });
    </script>
</body>
</html>`;

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveEnhancedStatus(res) {
        const status = this.jaimla ? this.jaimla.getEnhancedStatus() : { error: 'Agent not initialized' };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(status, null, 2));
    }

    serveCapabilities(res) {
        const capabilities = this.jaimla ? this.jaimla.getCapabilities() : { error: 'Agent not initialized' };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(capabilities, null, 2));
    }

    async handleVoiceTest(res) {
        if (!this.jaimla) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Agent not initialized' }));
            return;
        }

        try {
            const testText = "Hello! This is a test of my enhanced voice capabilities. I am Jaimla, your machine learning agent!";
            const result = await this.jaimla.speak(testText, { autoPlay: false });

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                success: true,
                text: testText,
                result: result
            }));

        } catch (error) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                success: false,
                error: error.message
            }));
        }
    }

    async shutdown() {
        console.log('🛑 Shutting down Enhanced Jaimla demo...');

        if (this.jaimla) {
            await this.jaimla.shutdown();
        }

        if (this.wss) {
            this.wss.close();
        }

        if (this.server) {
            this.server.close();
        }

        console.log('✅ Enhanced Jaimla demo shutdown complete');
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    if (global.enhancedDemo) {
        await global.enhancedDemo.shutdown();
    }
    process.exit(0);
});

// Start enhanced demo
const demo = new EnhancedJaimlaDemo();
global.enhancedDemo = demo;
demo.start().catch(console.error);