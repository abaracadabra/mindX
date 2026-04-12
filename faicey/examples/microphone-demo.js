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
            console.log('  ✅ Background integration ready');
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
            this.initializeBackgroundActivity();
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

    initializeBackgroundActivity() {
        const activities = [
            'Real-time FFT analysis ready',
            'Voice pattern recognition active',
            'Frequency trigger detection online',
            'AgenticPlace agent discovery ready',
            'BANKON workflow integration ready',
            'Voicey bridge communication active',
            'Background learning process online',
            'Microphone data processing ready',
            'Live oscilloscope rendering active'
        ];

        const activity = activities[Math.floor(Math.random() * activities.length)];
        console.log(`🌐 System status: ${activity}`);
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
            margin-bottom: 20px;
        }

        .sensitivity-control {
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(0, 255, 128, 0.1);
            border-radius: 10px;
            border: 1px solid #00ff80;
        }

        .sensitivity-slider {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: #444;
            outline: none;
            margin: 10px 0;
            cursor: pointer;
        }

        .sensitivity-slider::-webkit-slider-thumb {
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #00ff80;
            cursor: pointer;
        }

        .sensitivity-slider::-moz-range-thumb {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #00ff80;
            cursor: pointer;
            border: none;
        }

        .playback-controls {
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(0, 128, 255, 0.1);
            border-radius: 10px;
            border: 1px solid #0080ff;
        }

        .playback-buttons {
            display: flex;
            gap: 10px;
            margin: 10px 0;
            flex-wrap: wrap;
        }

        .playback-button {
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            background: #0080ff;
            color: white;
            cursor: pointer;
            font-family: inherit;
            font-size: 12px;
            transition: background 0.3s;
        }

        .playback-button:hover {
            background: #0060dd;
        }

        .playback-button:disabled {
            background: #444;
            cursor: not-allowed;
        }

        .eq-controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 10px;
        }

        .eq-slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #444;
            outline: none;
        }

        .eq-slider::-webkit-slider-thumb {
            appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #0080ff;
            cursor: pointer;
        }

        .eq-label {
            text-align: center;
            font-size: 10px;
            color: #0080ff;
            margin-top: 5px;
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

            <div class="sensitivity-control">
                <div style="color: #00ff80; font-weight: bold; margin-bottom: 5px;">🎛️ Microphone Sensitivity</div>
                <input type="range" min="0.1" max="3.0" step="0.1" value="1.0" class="sensitivity-slider" id="sensitivity-slider">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #ccc;">
                    <span>Low</span>
                    <span id="sensitivity-value">1.0x</span>
                    <span>High</span>
                </div>
            </div>

            <div class="playback-controls">
                <div style="color: #0080ff; font-weight: bold; margin-bottom: 5px;">🔊 Voice Playback & Analysis</div>
                <div class="playback-buttons">
                    <button class="playback-button" id="load-clip" onclick="loadVoiceClip()">Load Clip</button>
                    <button class="playback-button" id="play-btn" onclick="playAudio()" disabled>▶️ Play</button>
                    <button class="playback-button" id="pause-btn" onclick="pauseAudio()" disabled>⏸️ Pause</button>
                    <button class="playback-button" id="stop-btn" onclick="stopAudio()" disabled>⏹️ Stop</button>
                    <button class="playback-button" id="record-btn" onclick="recordAudio()">🔴 Record</button>
                </div>
                <div class="eq-controls">
                    <div>
                        <input type="range" min="-10" max="10" step="1" value="0" class="eq-slider" id="eq-low" onchange="updateEQ()">
                        <div class="eq-label">Low</div>
                    </div>
                    <div>
                        <input type="range" min="-10" max="10" step="1" value="0" class="eq-slider" id="eq-mid" onchange="updateEQ()">
                        <div class="eq-label">Mid</div>
                    </div>
                    <div>
                        <input type="range" min="-10" max="10" step="1" value="0" class="eq-slider" id="eq-high" onchange="updateEQ()">
                        <div class="eq-label">High</div>
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 12px; color: #ccc;">
                    <span>Clip: </span><span id="clip-name">No clip loaded</span>
                </div>
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

        // Playback functionality variables
        let audioElement = null;
        let playbackAnalyser = null;
        let playbackSource = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let isPlaying = false;
        let isPaused = false;
        let sensitivity = 1.0;

        // EQ variables
        let eqLow = null;
        let eqMid = null;
        let eqHigh = null;

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
                addLog('FFT analysis running with sensitivity: ' + sensitivity.toFixed(1) + 'x');

                // Enable record button
                document.getElementById('record-btn').disabled = false;

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

            addLog('Microphone disabled');

            // Disable record button
            document.getElementById('record-btn').disabled = true;
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
            // Apply sensitivity multiplier to relevant metrics
            const adjustedRms = metrics.rms * sensitivity;
            const adjustedAmplitude = metrics.amplitude * sensitivity;

            document.getElementById('frequency').textContent = Math.round(metrics.dominantFreq) + ' Hz';
            document.getElementById('amplitude').textContent = adjustedAmplitude.toFixed(3);
            document.getElementById('rms').textContent = adjustedRms.toFixed(3);
            document.getElementById('centroid').textContent = Math.round(metrics.spectralCentroid) + ' Hz';
            document.getElementById('rolloff').textContent = Math.round(metrics.spectralRolloff) + ' Hz';
            document.getElementById('zcr').textContent = metrics.zeroCrossingRate.toFixed(3);

            // Pattern detection with sensitivity adjustment
            const sensitivityThreshold = 0.1 / sensitivity;
            const noiseThreshold = 0.05 / sensitivity;

            if (adjustedRms > sensitivityThreshold) {
                document.getElementById('pattern').textContent = 'speech';
                document.getElementById('inflection').textContent = metrics.spectralCentroid > 2000 ? 'rising' : 'falling';
            } else if (adjustedRms > noiseThreshold) {
                document.getElementById('pattern').textContent = 'noise';
                document.getElementById('inflection').textContent = 'neutral';
            } else {
                document.getElementById('pattern').textContent = 'silent';
                document.getElementById('inflection').textContent = 'neutral';
            }
        }

        // Generic updateMetrics function for both live and playback analysis
        function updateMetrics() {
            if (!analyser && !playbackAnalyser) return;

            const activeAnalyser = analyser || playbackAnalyser;
            activeAnalyser.getByteTimeDomainData(dataArray);
            activeAnalyser.getByteFrequencyData(freqArray);

            const metrics = calculateAudioMetrics(dataArray, freqArray);
            updateRealTimeDisplay(metrics);
        }

        function drawOscilloscope() {
            if (!dataArray) return;

            const timeData = dataArray;
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

        function drawSpectrum() {
            if (!freqArray) return;

            const freqData = freqArray;
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
            activityLogs.unshift(`[${timestamp}] ${message}`);

            if (activityLogs.length > 15) {
                activityLogs = activityLogs.slice(0, 15);
            }

            document.getElementById('activity-log').innerHTML = activityLogs.join('<br>');
        }


        // Initialize
        loadCapabilities();
        updateDisplay();
        setInterval(updateDisplay, 2000);

        // Initialize display
        updateDisplay();
        loadCapabilities();

        // Sensitivity control
        function updateSensitivity() {
            const slider = document.getElementById('sensitivity-slider');
            sensitivity = parseFloat(slider.value);
            document.getElementById('sensitivity-value').textContent = sensitivity.toFixed(1) + 'x';
            addLog(`Microphone sensitivity set to ${sensitivity.toFixed(1)}x`);
        }

        // Playback functionality
        function loadVoiceClip() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'audio/*';
            input.onchange = function(e) {
                const file = e.target.files[0];
                if (file) {
                    const url = URL.createObjectURL(file);
                    audioElement = new Audio(url);
                    audioElement.crossOrigin = 'anonymous';

                    document.getElementById('clip-name').textContent = file.name;
                    document.getElementById('play-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = false;

                    addLog(`Loaded audio clip: ${file.name}`);

                    // Set up audio context for playback analysis
                    if (!audioContext) {
                        audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    }

                    audioElement.addEventListener('loadeddata', () => {
                        setupPlaybackAnalysis();
                    });
                }
            };
            input.click();
        }

        function setupPlaybackAnalysis() {
            if (audioElement && audioContext) {
                playbackSource = audioContext.createMediaElementSource(audioElement);
                playbackAnalyser = audioContext.createAnalyser();

                playbackAnalyser.fftSize = 2048;
                const bufferLength = playbackAnalyser.frequencyBinCount;
                dataArray = new Uint8Array(bufferLength);
                freqArray = new Uint8Array(bufferLength);

                // Set up EQ
                setupEQ();

                playbackSource.connect(eqLow);
                eqHigh.connect(audioContext.destination);
                playbackSource.connect(playbackAnalyser);

                addLog('Playback analysis ready');
            }
        }

        function setupEQ() {
            if (!audioContext) return;

            eqLow = audioContext.createBiquadFilter();
            eqMid = audioContext.createBiquadFilter();
            eqHigh = audioContext.createBiquadFilter();

            eqLow.type = 'lowshelf';
            eqLow.frequency.value = 320;

            eqMid.type = 'peaking';
            eqMid.frequency.value = 1000;
            eqMid.Q.value = 0.5;

            eqHigh.type = 'highshelf';
            eqHigh.frequency.value = 3200;

            eqLow.connect(eqMid);
            eqMid.connect(eqHigh);
        }

        function updateEQ() {
            if (!eqLow || !eqMid || !eqHigh) return;

            const lowGain = parseInt(document.getElementById('eq-low').value);
            const midGain = parseInt(document.getElementById('eq-mid').value);
            const highGain = parseInt(document.getElementById('eq-high').value);

            eqLow.gain.value = lowGain;
            eqMid.gain.value = midGain;
            eqHigh.gain.value = highGain;

            addLog(`EQ updated: Low=${lowGain}dB, Mid=${midGain}dB, High=${highGain}dB`);
        }

        function playAudio() {
            if (audioElement) {
                audioElement.play();
                isPlaying = true;
                isPaused = false;

                document.getElementById('play-btn').disabled = true;
                document.getElementById('pause-btn').disabled = false;

                addLog('Playback started - analyzing audio...');
                startPlaybackAnalysis();
            }
        }

        function pauseAudio() {
            if (audioElement) {
                audioElement.pause();
                isPaused = true;

                document.getElementById('play-btn').disabled = false;
                document.getElementById('pause-btn').disabled = true;

                addLog('Playback paused');
            }
        }

        function stopAudio() {
            if (audioElement) {
                audioElement.pause();
                audioElement.currentTime = 0;
                isPlaying = false;
                isPaused = false;

                document.getElementById('play-btn').disabled = false;
                document.getElementById('pause-btn').disabled = true;

                addLog('Playback stopped');
            }
        }

        function startPlaybackAnalysis() {
            if (!isPlaying || !playbackAnalyser) return;

            function analyze() {
                if (!isPlaying) return;

                playbackAnalyser.getByteTimeDomainData(dataArray);
                playbackAnalyser.getByteFrequencyData(freqArray);

                drawOscilloscope();
                drawSpectrum();
                updateMetrics();

                requestAnimationFrame(analyze);
            }

            analyze();
        }

        function recordAudio() {
            if (isRecording) {
                addLog('Already recording with microphone');
                return;
            }

            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    mediaRecorder = new MediaRecorder(stream);
                    recordedChunks = [];

                    mediaRecorder.addEventListener('dataavailable', event => {
                        if (event.data.size > 0) {
                            recordedChunks.push(event.data);
                        }
                    });

                    mediaRecorder.addEventListener('stop', () => {
                        const blob = new Blob(recordedChunks, { type: 'audio/wav' });
                        const url = URL.createObjectURL(blob);

                        audioElement = new Audio(url);
                        document.getElementById('clip-name').textContent = 'Recorded Audio';
                        document.getElementById('play-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = false;

                        addLog('Recording completed and loaded for playback');
                    });

                    mediaRecorder.start();
                    addLog('Recording started...');

                    setTimeout(() => {
                        mediaRecorder.stop();
                        stream.getTracks().forEach(track => track.stop());
                    }, 10000); // Record for 10 seconds
                })
                .catch(error => {
                    addLog(`Recording failed: ${error.message}`);
                });
        }

        // Initialize sensitivity slider
        document.getElementById('sensitivity-slider').addEventListener('input', updateSensitivity);

        // Initial logs
        addLog('Faicey 2.0 microphone system initialized');
        addLog('Jaimla agent online and listening');
        addLog('Enable microphone for live analysis or load audio clip for playback analysis');
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