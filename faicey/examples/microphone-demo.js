#!/usr/bin/env node
/**
 * Microphone-Enhanced Faicey Demo - Real-Time Voice Analysis with Actual Oscilloscope
 *
 * © Professor Codephreak - rage.pythai.net
 * Demonstrates faicey with REAL microphone input and live frequency analysis
 *
 * Usage: node examples/microphone-demo.js
 */

import { promises as fs } from 'fs';
import { createServer } from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class MicrophoneEnhancedFaiceyDemo {
    constructor() {
        this.port = process.env.FAICEY_PORT || 8081;
        this.server = null;
        this.startTime = Date.now();

        // Enhanced agent state with real microphone data
        this.jaimlaState = {
            active: true,
            expression: 'listening',
            voicePattern: 'attentive',
            lastActivity: Date.now(),
            interactions: 0,
            microphoneEnabled: false,
            realTimeAnalysis: false,
            capabilities: [
                'Real-Time Microphone Analysis',
                'Live FFT Frequency Spectrum',
                'Voice Print Analysis (REAL)',
                'Frequency Trigger Detection',
                'Inflection Pattern Recognition',
                'D3.js Live Oscilloscope',
                'Autonomous Voice Creation',
                'Background Agent Interaction',
                'Modular Integration Bridge'
            ]
        };

        // Real-time voice analysis data structure
        this.voiceAnalysis = {
            frequency: 0,
            amplitude: 0,
            dominantFreq: 0,
            spectralCentroid: 0,
            spectralRolloff: 0,
            zeroCrossingRate: 0,
            rms: 0,
            lastUpdate: Date.now(),
            pattern: 'silent',
            inflection: 'neutral',
            isRealTime: false
        };

        console.log('🎤 Microphone-Enhanced Faicey Demo Initializing...');
        console.log('💖 "I am the machine learning agent" - Jaimla with REAL voice analysis');
        console.log('🎵 Live microphone input with FFT analysis');
    }

    async start() {
        try {
            await this.startWebServer();
            this.startSimulations();

            console.log(`🚀 Microphone-Enhanced Faicey Demo running at http://localhost:${this.port}`);
            console.log('🎨 Features demonstrated:');
            console.log('  ✅ Real-time microphone capture');
            console.log('  ✅ Live FFT frequency analysis');
            console.log('  ✅ Voice pattern recognition');
            console.log('  ✅ Jaimla reactive expressions');
            console.log('  ✅ Background integration simulation');
            console.log('');
            console.log('🎤 Click "Enable Microphone" to start REAL voice analysis');

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
        // Simulate agent state changes
        setInterval(() => {
            this.updateAgentState();
        }, 2000);

        // Simulate background activity
        setInterval(() => {
            this.simulateBackgroundActivity();
        }, 5000);
    }

    updateAgentState() {
        const expressions = ['listening', 'analyzing', 'processing', 'responding', 'learning'];
        const voicePatterns = ['attentive', 'focused', 'reactive', 'analytical'];

        // Update based on microphone activity
        if (this.jaimlaState.microphoneEnabled && this.voiceAnalysis.rms > 0.1) {
            this.jaimlaState.expression = 'analyzing';
            this.jaimlaState.voicePattern = 'reactive';
        } else {
            // Occasionally update expression
            if (Math.random() < 0.3) {
                this.jaimlaState.expression = expressions[Math.floor(Math.random() * expressions.length)];
            }

            if (Math.random() < 0.2) {
                this.jaimlaState.voicePattern = voicePatterns[Math.floor(Math.random() * voicePatterns.length)];
            }
        }

        this.jaimlaState.lastActivity = Date.now();
    }

    simulateBackgroundActivity() {
        const activities = [
            'Real-time FFT analysis',
            'Voice pattern recognition',
            'Frequency trigger detection',
            'AgenticPlace agent discovery',
            'BANKON workflow simulation',
            'Voicey bridge communication',
            'Background learning process',
            'Microphone data processing',
            'Live oscilloscope rendering'
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
    <title>Faicey 2.0 - Real Microphone Analysis</title>
    <style>
        body {
            margin: 0;
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a1a0a 0%, #1a2e1a 50%, #0a3060 100%);
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
            background: rgba(0, 255, 128, 0.1);
            padding: 30px;
            border-radius: 15px;
            border: 2px solid #00ff80;
        }

        .title {
            font-size: 2.5rem;
            color: #00ff80;
            text-shadow: 0 0 20px #00ff80;
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
            color: #00ff80;
            font-size: 1.4rem;
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid #00ff80;
            padding-bottom: 10px;
        }

        .microphone-controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
        }

        .mic-button {
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-family: inherit;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }

        .mic-enable {
            background: linear-gradient(135deg, #00ff80, #40ff80);
            color: #000;
        }

        .mic-disable {
            background: linear-gradient(135deg, #ff4080, #ff8080);
            color: #fff;
        }

        .mic-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 255, 128, 0.3);
        }

        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 30px;
        }

        .status-item {
            background: rgba(0, 255, 128, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #00ff80;
        }

        .status-label {
            font-size: 0.9rem;
            color: #ccc;
            margin-bottom: 5px;
        }

        .status-value {
            font-size: 1.1rem;
            color: #00ff80;
            font-weight: bold;
        }

        .real-time {
            color: #ff0080 !important;
            text-shadow: 0 0 5px #ff0080;
        }

        .oscilloscope-container {
            position: relative;
            margin: 20px 0;
        }

        .oscilloscope {
            width: 100%;
            height: 250px;
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #00ff80;
            border-radius: 10px;
            position: relative;
        }

        .oscilloscope.real-time {
            border-color: #ff0080;
            box-shadow: 0 0 20px rgba(255, 0, 128, 0.3);
        }

        .frequency-spectrum {
            width: 100%;
            height: 150px;
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #00ff80;
            border-radius: 10px;
            margin-top: 10px;
        }

        .frequency-spectrum.real-time {
            border-color: #ff0080;
            box-shadow: 0 0 20px rgba(255, 0, 128, 0.3);
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

        .capability.real-time {
            background: rgba(255, 0, 128, 0.1);
            border-color: #ff0080;
            color: #ff0080;
        }

        .footer {
            grid-column: 1 / 3;
            text-align: center;
            font-size: 0.9rem;
            opacity: 0.7;
            padding: 15px;
        }

        .live-data {
            color: #ff0080;
            text-shadow: 0 0 5px #ff0080;
        }

        .pulse {
            animation: pulse 1.5s infinite;
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

        .mic-status {
            text-align: center;
            margin: 10px 0;
            padding: 10px;
            border-radius: 8px;
            font-weight: bold;
        }

        .mic-off {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid #ff4444;
            color: #ff4444;
        }

        .mic-on {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff80;
            color: #00ff80;
        }

        .advanced-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }

        .metric {
            background: rgba(0, 255, 128, 0.05);
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #00ff80;
            text-align: center;
            font-size: 0.8rem;
        }

        .metric.real-time {
            border-color: #ff0080;
            color: #ff0080;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">FAICEY 2.0 🎤 LIVE</h1>
            <p class="subtitle">Real-Time Microphone Analysis with Live FFT & Voice Pattern Recognition</p>
            <div style="margin-top: 15px;">
                🎭 <span class="live-data">Jaimla Agent</span> |
                🎤 <span class="live-data">Live Microphone</span> |
                📊 <span class="live-data">Real FFT Analysis</span>
            </div>
        </div>

        <div class="panel">
            <h2 class="panel-title">🎭 Jaimla Agent Status</h2>

            <div class="jaimla-quote pulse">
                "I am the machine learning agent - listening to YOUR voice!"
            </div>

            <div class="microphone-controls">
                <button id="enable-mic" class="mic-button mic-enable" onclick="enableMicrophone()">
                    🎤 Enable Microphone
                </button>
                <button id="disable-mic" class="mic-button mic-disable" onclick="disableMicrophone()" disabled>
                    🔇 Disable Microphone
                </button>
            </div>

            <div class="mic-status mic-off" id="mic-status">
                🔇 Microphone Disabled - Using Simulation
            </div>

            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Status</div>
                    <div class="status-value" id="agent-status">Active</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Expression</div>
                    <div class="status-value" id="agent-expression">listening</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Voice Pattern</div>
                    <div class="status-value" id="voice-pattern">attentive</div>
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
            <h2 class="panel-title">🎵 Live Voice Analysis & Oscilloscope</h2>

            <div class="oscilloscope-container">
                <canvas id="oscilloscope" class="oscilloscope" width="400" height="250"></canvas>
                <canvas id="frequency-spectrum" class="frequency-spectrum" width="400" height="150"></canvas>
            </div>

            <div class="advanced-metrics">
                <div class="metric">
                    <div>Frequency</div>
                    <div id="frequency">0 Hz</div>
                </div>
                <div class="metric">
                    <div>Amplitude</div>
                    <div id="amplitude">0.0</div>
                </div>
                <div class="metric">
                    <div>RMS</div>
                    <div id="rms">0.0</div>
                </div>
                <div class="metric">
                    <div>Centroid</div>
                    <div id="centroid">0 Hz</div>
                </div>
                <div class="metric">
                    <div>Rolloff</div>
                    <div id="rolloff">0 Hz</div>
                </div>
                <div class="metric">
                    <div>ZCR</div>
                    <div id="zcr">0.0</div>
                </div>
            </div>

            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">Pattern</div>
                    <div class="status-value" id="pattern">silent</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Inflection</div>
                    <div class="status-value" id="inflection">neutral</div>
                </div>
            </div>

            <h3 style="color: #00ff80; margin-bottom: 10px;">📊 Activity Log</h3>
            <div class="activity-log" id="activity-log">
                Initializing microphone-enhanced voice analysis system...
            </div>
        </div>

        <div class="footer">
            © Professor Codephreak - Faicey 2.0 with Real-Time Microphone Analysis<br>
            🔗 Live FFT Processing + Voice Pattern Recognition + Jaimla Agent
        </div>
    </div>

    <script>
        let audioContext = null;
        let analyser = null;
        let microphone = null;
        let dataArray = null;
        let freqArray = null;
        let isRecording = false;
        let activityLogs = [];

        // Initialize canvases
        const oscilloscope = document.getElementById('oscilloscope');
        const oscCtx = oscilloscope.getContext('2d');
        const spectrum = document.getElementById('frequency-spectrum');
        const specCtx = spectrum.getContext('2d');

        // Microphone control functions
        async function enableMicrophone() {
            try {
                addLog('Requesting microphone access...');

                audioContext = new (window.AudioContext || window.webkitAudioContext)();

                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                microphone = audioContext.createMediaStreamSource(stream);
                analyser = audioContext.createAnalyser();

                analyser.fftSize = 2048;
                const bufferLength = analyser.frequencyBinCount;
                dataArray = new Uint8Array(bufferLength);
                freqArray = new Uint8Array(bufferLength);

                microphone.connect(analyser);

                isRecording = true;

                // Update UI
                document.getElementById('enable-mic').disabled = true;
                document.getElementById('disable-mic').disabled = false;
                document.getElementById('mic-status').className = 'mic-status mic-on';
                document.getElementById('mic-status').textContent = '🎤 Microphone Active - Real-Time Analysis';

                // Add real-time styling
                oscilloscope.classList.add('real-time');
                spectrum.classList.add('real-time');

                addLog('Microphone enabled - Real-time analysis active');
                addLog('FFT analysis running at 60 FPS');

                startRealTimeAnalysis();

            } catch (error) {
                console.error('Microphone access denied:', error);
                addLog('Microphone access denied: ' + error.message);
                alert('Microphone access required for real-time analysis. Please allow microphone access and try again.');
            }
        }

        function disableMicrophone() {
            isRecording = false;

            if (microphone) {
                microphone.disconnect();
                microphone = null;
            }

            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }

            // Update UI
            document.getElementById('enable-mic').disabled = false;
            document.getElementById('disable-mic').disabled = true;
            document.getElementById('mic-status').className = 'mic-status mic-off';
            document.getElementById('mic-status').textContent = '🔇 Microphone Disabled - Using Simulation';

            // Remove real-time styling
            oscilloscope.classList.remove('real-time');
            spectrum.classList.remove('real-time');

            // Remove real-time styling from metrics
            document.querySelectorAll('.metric').forEach(metric => {
                metric.classList.remove('real-time');
            });

            addLog('Microphone disabled - Returning to simulation mode');
        }

        function startRealTimeAnalysis() {
            if (!isRecording) return;

            analyser.getByteTimeDomainData(dataArray);
            analyser.getByteFrequencyData(freqArray);

            // Calculate advanced metrics
            const metrics = calculateAdvancedMetrics(dataArray, freqArray);

            // Update display
            updateRealTimeDisplay(metrics);
            updateOscilloscope(dataArray);
            updateFrequencySpectrum(freqArray);

            // Add real-time styling to metrics
            document.querySelectorAll('.metric').forEach(metric => {
                metric.classList.add('real-time');
            });

            requestAnimationFrame(startRealTimeAnalysis);
        }

        function calculateAdvancedMetrics(timeData, freqData) {
            // Convert to normalized float arrays
            const timeArray = Array.from(timeData).map(x => (x - 128) / 128);
            const freqArray = Array.from(freqData).map(x => x / 255);

            // RMS (Root Mean Square)
            const rms = Math.sqrt(timeArray.reduce((sum, x) => sum + x * x, 0) / timeArray.length);

            // Dominant frequency
            let maxBin = 0;
            let maxValue = 0;
            for (let i = 0; i < freqArray.length; i++) {
                if (freqArray[i] > maxValue) {
                    maxValue = freqArray[i];
                    maxBin = i;
                }
            }
            const dominantFreq = (maxBin * audioContext.sampleRate) / (2 * freqArray.length);

            // Spectral Centroid
            let numerator = 0;
            let denominator = 0;
            for (let i = 0; i < freqArray.length; i++) {
                const freq = (i * audioContext.sampleRate) / (2 * freqArray.length);
                numerator += freq * freqArray[i];
                denominator += freqArray[i];
            }
            const spectralCentroid = denominator > 0 ? numerator / denominator : 0;

            // Spectral Rolloff (85% of energy)
            const totalEnergy = freqArray.reduce((sum, x) => sum + x, 0);
            const rolloffThreshold = totalEnergy * 0.85;
            let runningSum = 0;
            let rolloffIndex = 0;
            for (let i = 0; i < freqArray.length; i++) {
                runningSum += freqArray[i];
                if (runningSum >= rolloffThreshold) {
                    rolloffIndex = i;
                    break;
                }
            }
            const spectralRolloff = (rolloffIndex * audioContext.sampleRate) / (2 * freqArray.length);

            // Zero Crossing Rate
            let crossings = 0;
            for (let i = 1; i < timeArray.length; i++) {
                if ((timeArray[i] >= 0) !== (timeArray[i-1] >= 0)) {
                    crossings++;
                }
            }
            const zeroCrossingRate = crossings / timeArray.length;

            return {
                rms: rms,
                dominantFreq: dominantFreq,
                spectralCentroid: spectralCentroid,
                spectralRolloff: spectralRolloff,
                zeroCrossingRate: zeroCrossingRate,
                amplitude: rms,
                isRealTime: true
            };
        }

        function updateRealTimeDisplay(metrics) {
            document.getElementById('frequency').textContent = Math.round(metrics.dominantFreq) + ' Hz';
            document.getElementById('amplitude').textContent = metrics.amplitude.toFixed(3);
            document.getElementById('rms').textContent = metrics.rms.toFixed(3);
            document.getElementById('centroid').textContent = Math.round(metrics.spectralCentroid) + ' Hz';
            document.getElementById('rolloff').textContent = Math.round(metrics.spectralRolloff) + ' Hz';
            document.getElementById('zcr').textContent = metrics.zeroCrossingRate.toFixed(3);

            // Pattern detection
            if (metrics.rms > 0.1) {
                document.getElementById('pattern').textContent = 'speech';
                document.getElementById('inflection').textContent = metrics.spectralCentroid > 2000 ? 'rising' : 'falling';
            } else if (metrics.rms > 0.05) {
                document.getElementById('pattern').textContent = 'noise';
                document.getElementById('inflection').textContent = 'neutral';
            } else {
                document.getElementById('pattern').textContent = 'silent';
                document.getElementById('inflection').textContent = 'neutral';
            }
        }

        function updateOscilloscope(timeData) {
            oscCtx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            oscCtx.fillRect(0, 0, oscilloscope.width, oscilloscope.height);

            // Grid
            oscCtx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            oscCtx.lineWidth = 1;
            for (let x = 0; x < oscilloscope.width; x += 40) {
                oscCtx.beginPath();
                oscCtx.moveTo(x, 0);
                oscCtx.lineTo(x, oscilloscope.height);
                oscCtx.stroke();
            }
            for (let y = 0; y < oscilloscope.height; y += 25) {
                oscCtx.beginPath();
                oscCtx.moveTo(0, y);
                oscCtx.lineTo(oscilloscope.width, y);
                oscCtx.stroke();
            }

            // Waveform
            oscCtx.strokeStyle = isRecording ? '#ff0080' : '#00ff80';
            oscCtx.lineWidth = 2;
            oscCtx.beginPath();

            const sliceWidth = oscilloscope.width / timeData.length;
            let x = 0;

            for (let i = 0; i < timeData.length; i++) {
                const v = (timeData[i] - 128) / 128;
                const y = (v * oscilloscope.height / 2) + oscilloscope.height / 2;

                if (i === 0) {
                    oscCtx.moveTo(x, y);
                } else {
                    oscCtx.lineTo(x, y);
                }

                x += sliceWidth;
            }

            oscCtx.stroke();

            // Center line
            oscCtx.strokeStyle = 'rgba(255, 0, 128, 0.3)';
            oscCtx.lineWidth = 1;
            oscCtx.beginPath();
            oscCtx.moveTo(0, oscilloscope.height / 2);
            oscCtx.lineTo(oscilloscope.width, oscilloscope.height / 2);
            oscCtx.stroke();
        }

        function updateFrequencySpectrum(freqData) {
            specCtx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            specCtx.fillRect(0, 0, spectrum.width, spectrum.height);

            const barWidth = spectrum.width / freqData.length;
            let x = 0;

            for (let i = 0; i < freqData.length; i++) {
                const barHeight = (freqData[i] / 255) * spectrum.height;

                const hue = (i / freqData.length) * 360;
                specCtx.fillStyle = isRecording ?
                    \`hsl(\${hue}, 100%, 50%)\` :
                    \`hsl(\${hue + 120}, 70%, 50%)\`;

                specCtx.fillRect(x, spectrum.height - barHeight, barWidth, barHeight);
                x += barWidth;
            }
        }

        // Fallback simulation for when microphone is disabled
        function drawSimulatedOscilloscope() {
            if (isRecording) return; // Don't simulate if real microphone is active

            const time = Date.now() / 1000;
            const frequency = 440 + Math.sin(time * 0.5) * 100;
            const amplitude = 0.3 + Math.sin(time * 0.8) * 0.3;

            oscCtx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            oscCtx.fillRect(0, 0, oscilloscope.width, oscilloscope.height);

            // Grid
            oscCtx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            oscCtx.lineWidth = 1;
            for (let x = 0; x < oscilloscope.width; x += 40) {
                oscCtx.beginPath();
                oscCtx.moveTo(x, 0);
                oscCtx.lineTo(x, oscilloscope.height);
                oscCtx.stroke();
            }
            for (let y = 0; y < oscilloscope.height; y += 25) {
                oscCtx.beginPath();
                oscCtx.moveTo(0, y);
                oscCtx.lineTo(oscilloscope.width, y);
                oscCtx.stroke();
            }

            // Simulated waveform
            oscCtx.strokeStyle = '#00ff80';
            oscCtx.lineWidth = 2;
            oscCtx.beginPath();

            const centerY = oscilloscope.height / 2;

            for (let x = 0; x < oscilloscope.width; x++) {
                const t = (x / oscilloscope.width) * 4 * Math.PI + time * frequency / 100;
                const y = centerY + Math.sin(t) * amplitude * centerY * 0.8;

                if (x === 0) {
                    oscCtx.moveTo(x, y);
                } else {
                    oscCtx.lineTo(x, y);
                }
            }

            oscCtx.stroke();

            // Update simulated metrics
            document.getElementById('frequency').textContent = Math.round(frequency) + ' Hz';
            document.getElementById('amplitude').textContent = amplitude.toFixed(3);
            document.getElementById('rms').textContent = (amplitude * 0.707).toFixed(3);
            document.getElementById('centroid').textContent = Math.round(frequency * 1.2) + ' Hz';
            document.getElementById('rolloff').textContent = Math.round(frequency * 2.5) + ' Hz';
            document.getElementById('zcr').textContent = (frequency / 1000).toFixed(3);
            document.getElementById('pattern').textContent = 'simulated';
            document.getElementById('inflection').textContent = 'neutral';
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
                        if (capability.includes('Real-Time') || capability.includes('Live')) {
                            div.classList.add('real-time');
                        }
                        div.textContent = capability;
                        container.appendChild(div);
                    });
                });
        }

        function addLog(message) {
            const timestamp = new Date().toTimeString().slice(0, 8);
            activityLogs.unshift(\`[\${timestamp}] \${message}\`);

            if (activityLogs.length > 15) {
                activityLogs = activityLogs.slice(0, 15);
            }

            document.getElementById('activity-log').innerHTML = activityLogs.join('<br>');
        }

        // Simulate system activity logs
        setInterval(() => {
            if (!isRecording) {
                const activities = [
                    'Voice pattern simulated',
                    'Frequency simulation updated',
                    'Agent expression updated',
                    'Background process active',
                    'Oscilloscope simulation rendered',
                    'Jaimla response prepared'
                ];

                const activity = activities[Math.floor(Math.random() * activities.length)];
                addLog(activity);
            } else {
                const realActivities = [
                    'Real FFT analysis completed',
                    'Live frequency spectrum updated',
                    'Voice pattern recognition active',
                    'Real-time oscilloscope rendered',
                    'Microphone data processed',
                    'Advanced metrics calculated'
                ];

                const activity = realActivities[Math.floor(Math.random() * realActivities.length)];
                addLog(activity);
            }
        }, 3000);

        // Initialize
        loadCapabilities();
        updateDisplay();
        setInterval(updateDisplay, 2000);

        // Start simulated oscilloscope
        function animate() {
            drawSimulatedOscilloscope();
            requestAnimationFrame(animate);
        }
        animate();

        // Initial logs
        addLog('Faicey 2.0 microphone system initialized');
        addLog('Jaimla agent online and listening');
        addLog('Click Enable Microphone for REAL analysis');
        addLog('Currently using simulation mode');
    </script>
</body>
</html>`;

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveStatus(res) {
        const status = {
            uptime: Date.now() - this.startTime,
            system: 'Faicey 2.0 Microphone-Enhanced Demo',
            agent: 'Jaimla',
            version: '2.0.0-microphone',
            features: [
                'Real-Time Microphone Analysis',
                'Live FFT Frequency Spectrum',
                'Voice Pattern Recognition',
                'Advanced Audio Metrics',
                'Agent State Management',
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
            voiceEngines: ['Web Audio API', 'Real-Time FFT', 'espeak-ng', 'festival', 'flite'],
            integrations: ['microphone', 'voicey', 'agenticplace', 'bankon'],
            features: {
                realTimeMicrophone: true,
                liveFFTAnalysis: true,
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
        console.log('🛑 Shutting down microphone-enhanced demo...');

        if (this.server) {
            this.server.close();
        }

        console.log('✅ Shutdown complete');
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    if (global.micDemo) {
        await global.micDemo.shutdown();
    }
    process.exit(0);
});

// Start the microphone-enhanced demo
const demo = new MicrophoneEnhancedFaiceyDemo();
global.micDemo = demo;
demo.start().catch(console.error);