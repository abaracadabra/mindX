#!/usr/bin/env node
/**
 * Lightweight Faicey Demo - Core Functionality Without Heavy Dependencies
 *
 * © Professor Codephreak - rage.pythai.net
 * Demonstrates faicey core concepts, voice analysis simulation, and agent interaction
 * without requiring full dependency installation
 *
 * Usage: node examples/lightweight-demo.js
 */

import { promises as fs } from 'fs';
import { createServer } from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class LightweightFaiceyDemo {
    constructor() {
        this.port = process.env.FAICEY_PORT || 8080;
        this.server = null;
        this.startTime = Date.now();

        // Simulated agent state
        this.jaimlaState = {
            active: true,
            expression: 'neutral',
            voicePattern: 'calm',
            lastActivity: Date.now(),
            interactions: 0,
            capabilities: [
                'Voice Print Analysis (simulated)',
                'Frequency Trigger Detection',
                'Inflection Pattern Recognition',
                'D3.js Oscilloscope Integration',
                'Autonomous Voice Creation',
                'Background Agent Interaction',
                'Modular Integration Bridge',
                'AgenticPlace Marketplace',
                'BANKON Workflow Support'
            ]
        };

        // Simulated voice analysis data
        this.voiceAnalysis = {
            frequency: 440, // A4 note
            amplitude: 0.5,
            lastUpdate: Date.now(),
            pattern: 'speech',
            inflection: 'rising'
        };

        console.log('🎭 Lightweight Faicey Demo Initializing...');
        console.log('💖 "I am the machine learning agent" - Jaimla');
        console.log('🔧 Running without heavy dependencies for compatibility');
    }

    async start() {
        try {
            await this.startWebServer();
            this.startSimulations();

            console.log(`🚀 Lightweight Faicey Demo running at http://localhost:${this.port}`);
            console.log('🎨 Features demonstrated:');
            console.log('  ✅ Agent state management');
            console.log('  ✅ Voice analysis simulation');
            console.log('  ✅ Frequency trigger patterns');
            console.log('  ✅ Jaimla agent personality');
            console.log('  ✅ Modular architecture concepts');
            console.log('  ✅ Background integration patterns');
            console.log('');
            console.log('📱 Open browser to see interactive demo');

        } catch (error) {
            console.error('❌ Demo startup failed:', error);
            process.exit(1);
        }
    }

    async startWebServer() {
        this.server = createServer(async (req, res) => {
            try {
                if (req.url === '/') {
                    await this.serveDemoPage(res);
                } else if (req.url === '/api/status') {
                    this.serveStatus(res);
                } else if (req.url === '/api/jaimla') {
                    this.serveJaimlaState(res);
                } else if (req.url === '/api/voice-analysis') {
                    this.serveVoiceAnalysis(res);
                } else if (req.url === '/api/capabilities') {
                    this.serveCapabilities(res);
                } else {
                    res.writeHead(404);
                    res.end('Not Found');
                }
            } catch (error) {
                console.error('Server error:', error);
                res.writeHead(500);
                res.end('Internal Server Error');
            }
        });

        this.server.listen(this.port);
    }

    startSimulations() {
        // Simulate voice analysis updates
        setInterval(() => {
            this.updateVoiceAnalysis();
        }, 100); // 10 Hz updates

        // Simulate agent state changes
        setInterval(() => {
            this.updateAgentState();
        }, 2000);

        // Simulate background activity
        setInterval(() => {
            this.simulateBackgroundActivity();
        }, 5000);
    }

    updateVoiceAnalysis() {
        // Simulate dynamic frequency analysis
        const time = Date.now() / 1000;
        this.voiceAnalysis.frequency = 440 + Math.sin(time * 0.5) * 100; // Frequency oscillation
        this.voiceAnalysis.amplitude = 0.3 + Math.sin(time * 0.8) * 0.3; // Amplitude variation
        this.voiceAnalysis.lastUpdate = Date.now();

        // Simulate inflection changes
        const inflections = ['rising', 'falling', 'neutral', 'questioning'];
        if (Math.random() < 0.1) { // 10% chance to change inflection
            this.voiceAnalysis.inflection = inflections[Math.floor(Math.random() * inflections.length)];
        }
    }

    updateAgentState() {
        const expressions = ['neutral', 'curious', 'analytical', 'collaborative', 'learning'];
        const voicePatterns = ['calm', 'excited', 'focused', 'conversational'];

        // Occasionally update expression and voice pattern
        if (Math.random() < 0.3) {
            this.jaimlaState.expression = expressions[Math.floor(Math.random() * expressions.length)];
        }

        if (Math.random() < 0.2) {
            this.jaimlaState.voicePattern = voicePatterns[Math.floor(Math.random() * voicePatterns.length)];
        }

        this.jaimlaState.lastActivity = Date.now();
    }

    simulateBackgroundActivity() {
        const activities = [
            'AgenticPlace agent discovery',
            'BANKON workflow simulation',
            'Voicey bridge communication',
            'Background learning process',
            'Marketplace interaction',
            'Collaborative analysis',
            'Frequency pattern analysis',
            'Voice print generation'
        ];

        const activity = activities[Math.floor(Math.random() * activities.length)];
        console.log(`🌐 Background activity: ${activity}`);
        this.jaimlaState.interactions++;
    }

    async serveDemoPage(res) {
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faicey 2.0 - Lightweight Demo</title>
    <style>
        body {
            margin: 0;
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #1a0a2e 0%, #16213e 50%, #0f3460 100%);
            color: #fff;
            min-height: 100vh;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr auto;
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

        .title {
            font-size: 2.5rem;
            color: #ff0080;
            text-shadow: 0 0 20px #ff0080;
            margin: 0;
        }

        .subtitle {
            font-size: 1.1rem;
            color: #fff;
            margin: 10px 0 0 0;
            opacity: 0.9;
        }

        .panel {
            background: rgba(0, 0, 0, 0.7);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid #444;
            overflow-y: auto;
        }

        .panel-title {
            color: #ff0080;
            font-size: 1.4rem;
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

        .status-item {
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

        .oscilloscope {
            width: 100%;
            height: 200px;
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #00ff80;
            border-radius: 10px;
            position: relative;
            margin: 20px 0;
        }

        .wave {
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 2px;
            background: #00ff80;
            box-shadow: 0 0 10px #00ff80;
            transform-origin: left center;
        }

        .capabilities {
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
        }

        .capability {
            background: rgba(0, 255, 128, 0.1);
            padding: 8px 12px;
            border-radius: 20px;
            border: 1px solid #00ff80;
            font-size: 0.9rem;
            text-align: center;
        }

        .footer {
            grid-column: 1 / 3;
            text-align: center;
            font-size: 0.9rem;
            opacity: 0.7;
            padding: 15px;
        }

        .live-data {
            color: #00ff80;
            text-shadow: 0 0 5px #00ff80;
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .jaimla-quote {
            font-style: italic;
            color: #ff8080;
            text-align: center;
            margin: 15px 0;
            padding: 10px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 10px;
        }

        .activity-log {
            max-height: 200px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.5);
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #444;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">FAICEY 2.0 DEMO</h1>
            <p class="subtitle">Advanced Voice-Reactive Agent System with D3.js Oscilloscope & Frequency Analysis</p>
            <div style="margin-top: 15px;">
                🎭 <span class="live-data">Jaimla Agent</span> |
                🎵 <span class="live-data">Voice Analysis</span> |
                🌐 <span class="live-data">Background Integration</span>
            </div>
        </div>

        <div class="panel">
            <h2 class="panel-title">🎭 Jaimla Agent Status</h2>

            <div class="jaimla-quote pulse">
                "I am the machine learning agent"
            </div>

            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Status</div>
                    <div class="status-value" id="agent-status">Active</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Expression</div>
                    <div class="status-value" id="agent-expression">neutral</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Voice Pattern</div>
                    <div class="status-value" id="voice-pattern">calm</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Interactions</div>
                    <div class="status-value" id="interactions">0</div>
                </div>
            </div>

            <h3 style="color: #00ff80; margin-bottom: 15px;">🚀 Capabilities</h3>
            <div class="capabilities" id="capabilities-list">
                <!-- Capabilities loaded dynamically -->
            </div>
        </div>

        <div class="panel">
            <h2 class="panel-title">🎵 Voice Analysis & Oscilloscope</h2>

            <div class="oscilloscope">
                <canvas id="oscilloscope" width="400" height="200"></canvas>
            </div>

            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Frequency (Hz)</div>
                    <div class="status-value" id="frequency">440</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Amplitude</div>
                    <div class="status-value" id="amplitude">0.5</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Pattern</div>
                    <div class="status-value" id="pattern">speech</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Inflection</div>
                    <div class="status-value" id="inflection">neutral</div>
                </div>
            </div>

            <h3 style="color: #00ff80; margin-bottom: 10px;">📊 Activity Log</h3>
            <div class="activity-log" id="activity-log">
                Initializing voice analysis system...
            </div>
        </div>

        <div class="footer">
            © Professor Codephreak - Faicey 2.0 Advanced Voice-Reactive Agent System<br>
            🔗 Modular Integration: Faicey + Voicey + AgenticPlace + BANKON
        </div>
    </div>

    <script>
        let activityLogs = [];

        // Initialize oscilloscope canvas
        const canvas = document.getElementById('oscilloscope');
        const ctx = canvas.getContext('2d');

        function drawOscilloscope(frequency, amplitude) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Grid
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 1;
            for (let x = 0; x < canvas.width; x += 40) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }
            for (let y = 0; y < canvas.height; y += 40) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }

            // Waveform
            ctx.strokeStyle = '#00ff80';
            ctx.lineWidth = 2;
            ctx.beginPath();

            const centerY = canvas.height / 2;
            const time = Date.now() / 1000;

            for (let x = 0; x < canvas.width; x++) {
                const t = (x / canvas.width) * 4 * Math.PI + time * frequency / 100;
                const y = centerY + Math.sin(t) * amplitude * centerY * 0.8;

                if (x === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }

            ctx.stroke();

            // Center line
            ctx.strokeStyle = 'rgba(255, 0, 128, 0.3)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, centerY);
            ctx.lineTo(canvas.width, centerY);
            ctx.stroke();
        }

        function updateDisplay() {
            fetch('/api/jaimla')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('agent-status').textContent = data.active ? 'Active' : 'Inactive';
                    document.getElementById('agent-expression').textContent = data.expression;
                    document.getElementById('voice-pattern').textContent = data.voicePattern;
                    document.getElementById('interactions').textContent = data.interactions;
                });

            fetch('/api/voice-analysis')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('frequency').textContent = Math.round(data.frequency * 100) / 100;
                    document.getElementById('amplitude').textContent = Math.round(data.amplitude * 100) / 100;
                    document.getElementById('pattern').textContent = data.pattern;
                    document.getElementById('inflection').textContent = data.inflection;

                    // Update oscilloscope
                    drawOscilloscope(data.frequency, data.amplitude);
                });
        }

        function loadCapabilities() {
            fetch('/api/capabilities')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('capabilities-list');
                    container.innerHTML = '';

                    data.capabilities.forEach(capability => {
                        const div = document.createElement('div');
                        div.className = 'capability';
                        div.textContent = capability;
                        container.appendChild(div);
                    });
                });
        }

        function addLog(message) {
            const timestamp = new Date().toTimeString().slice(0, 8);
            activityLogs.unshift(\`[\${timestamp}] \${message}\`);

            if (activityLogs.length > 10) {
                activityLogs = activityLogs.slice(0, 10);
            }

            document.getElementById('activity-log').innerHTML = activityLogs.join('<br>');
        }

        // Simulate system activity logs
        setInterval(() => {
            const activities = [
                'Voice pattern analyzed',
                'Frequency trigger detected',
                'Agent expression updated',
                'Background process active',
                'Voice print generated',
                'Inflection change detected',
                'Oscilloscope data updated',
                'Jaimla response prepared'
            ];

            const activity = activities[Math.floor(Math.random() * activities.length)];
            addLog(activity);
        }, 3000);

        // Initialize
        loadCapabilities();
        updateDisplay();
        setInterval(updateDisplay, 100); // Update at 10 FPS

        // Initial logs
        addLog('Faicey 2.0 system initialized');
        addLog('Jaimla agent online');
        addLog('Voice analysis system active');
    </script>
</body>
</html>`;

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveStatus(res) {
        const status = {
            uptime: Date.now() - this.startTime,
            system: 'Faicey 2.0 Lightweight Demo',
            agent: 'Jaimla',
            version: '2.0.0-demo',
            features: [
                'Voice Analysis Simulation',
                'Agent State Management',
                'Frequency Analysis',
                'Oscilloscope Visualization',
                'Background Activity Simulation'
            ]
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(status, null, 2));
    }

    serveJaimlaState(res) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(this.jaimlaState, null, 2));
    }

    serveVoiceAnalysis(res) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(this.voiceAnalysis, null, 2));
    }

    serveCapabilities(res) {
        const capabilities = {
            capabilities: this.jaimlaState.capabilities,
            voiceEngines: ['espeak-ng', 'festival', 'flite', 'pico2wave'],
            integrations: ['voicey', 'agenticplace', 'bankon'],
            features: {
                voiceAnalysis: true,
                frequencyTriggers: true,
                inflectionDetection: true,
                oscilloscope: true,
                backgroundIntegration: true,
                modularArchitecture: true
            }
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(capabilities, null, 2));
    }

    async shutdown() {
        console.log('🛑 Shutting down lightweight demo...');

        if (this.server) {
            this.server.close();
        }

        console.log('✅ Shutdown complete');
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    if (global.demo) {
        await global.demo.shutdown();
    }
    process.exit(0);
});

// Start the demo
const demo = new LightweightFaiceyDemo();
global.demo = demo;
demo.start().catch(console.error);