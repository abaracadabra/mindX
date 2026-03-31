/**
 * Oscilloscope Demo - Advanced D3.js Voice Print Visualization
 *
 * © Professor Codephreak - rage.pythai.net
 * Demonstrates advanced oscilloscope visualization with D3.js
 * Real-time voice print analysis with frequency triggers
 *
 * Usage: node examples/oscilloscope-demo.js
 */

import * as d3 from 'd3';
import { FaiceyCore } from '../src/FaiceyCore.js';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';

class OscilloscopeDemo {
    constructor() {
        this.faicey = null;
        this.server = null;
        this.wss = null;
        this.clients = new Set();
        this.port = process.env.OSCILLOSCOPE_PORT || 8081;

        // Advanced analysis buffers
        this.voiceHistory = [];
        this.frequencyHistory = [];
        this.inflectionHistory = [];
        this.triggerHistory = [];

        // Analysis parameters
        this.bufferSize = 2048;
        this.sampleRate = 44100;
        this.analysisWindow = 1000; // ms
    }

    async start() {
        console.log('🌊 Starting Advanced Oscilloscope Demo');
        console.log('📊 D3.js Voice Print Visualization with Frequency Analysis');

        try {
            // Initialize faicey core
            await this.initFaicey();

            // Start web server
            await this.startWebServer();

            // Start WebSocket
            this.startWebSocket();

            // Start advanced analysis
            this.startAdvancedAnalysis();

            console.log(`🚀 Oscilloscope demo running at http://localhost:${this.port}`);

        } catch (error) {
            console.error('❌ Oscilloscope demo startup failed:', error);
            process.exit(1);
        }
    }

    async initFaicey() {
        this.faicey = new FaiceyCore({
            agentId: 'oscilloscope-demo',
            persona: 'jaimla',
            debug: true
        });

        // Enhanced frequency triggers for oscilloscope demo
        this.setupAdvancedTriggers();

        // Event listeners
        this.faicey.on('initialized', () => {
            console.log('✅ Faicey core initialized for oscilloscope demo');
        });

        this.faicey.on('triggerActivated', (data) => {
            this.logTrigger(data);
            this.broadcastTrigger(data);
        });

        await this.faicey.init();
    }

    setupAdvancedTriggers() {
        // Sub-bass analysis
        this.faicey.addFrequencyTrigger('sub-bass', {
            range: [20, 60],
            threshold: 0.8,
            expression: 'concentrated',
            response: 'deep-analysis'
        });

        // Bass frequencies
        this.faicey.addFrequencyTrigger('bass', {
            range: [60, 250],
            threshold: 0.7,
            expression: 'thinking',
            response: 'bass-detected'
        });

        // Midrange (vocal fundamentals)
        this.faicey.addFrequencyTrigger('midrange', {
            range: [250, 4000],
            threshold: 0.6,
            expression: 'speaking',
            response: 'vocal-range'
        });

        // Presence (vocal clarity)
        this.faicey.addFrequencyTrigger('presence', {
            range: [4000, 6000],
            threshold: 0.65,
            expression: 'excited',
            response: 'clarity-boost'
        });

        // Brilliance (harmonics)
        this.faicey.addFrequencyTrigger('brilliance', {
            range: [6000, 20000],
            threshold: 0.75,
            expression: 'surprised',
            response: 'harmonic-content'
        });

        // Complex inflection patterns
        this.faicey.addInflectionTrigger('rapid-rise', {
            pattern: 'rapid-positive',
            threshold: 1.0,
            expression: 'surprised',
            response: 'excitement-detected'
        });

        this.faicey.addInflectionTrigger('gentle-fall', {
            pattern: 'gentle-negative',
            threshold: -0.3,
            expression: 'thinking',
            response: 'contemplation'
        });
    }

    startAdvancedAnalysis() {
        setInterval(() => {
            if (this.faicey && this.faicey.voicePrint) {
                this.performAdvancedAnalysis();
            }
        }, 50); // 20 Hz analysis rate
    }

    performAdvancedAnalysis() {
        const voiceData = this.faicey.getVoiceData();

        // Store in history buffers
        this.voiceHistory.push({
            timestamp: Date.now(),
            timeData: Array.from(voiceData.timeData),
            frequencies: Array.from(voiceData.frequencies),
            pitch: voiceData.pitch,
            inflection: voiceData.inflection,
            spectralCentroid: voiceData.spectralCentroid,
            zeroCrossingRate: voiceData.zeroCrossingRate
        });

        // Trim history to analysis window
        const cutoff = Date.now() - this.analysisWindow;
        this.voiceHistory = this.voiceHistory.filter(entry => entry.timestamp > cutoff);

        // Advanced analysis
        const analysis = {
            rms: this.calculateRMS(voiceData.timeData),
            peak: this.calculatePeak(voiceData.timeData),
            spectralRolloff: this.calculateSpectralRolloff(voiceData.frequencies),
            spectralFlux: this.calculateSpectralFlux(voiceData.frequencies),
            dynamicRange: this.calculateDynamicRange(),
            formantAnalysis: this.analyzeFormants(voiceData.frequencies),
            harmonicContent: this.analyzeHarmonics(voiceData.frequencies),
            voicePrint: this.generateVoicePrint()
        };

        // Broadcast to clients
        this.broadcastAnalysis(analysis);
    }

    calculateRMS(timeData) {
        let sum = 0;
        for (let i = 0; i < timeData.length; i++) {
            sum += timeData[i] * timeData[i];
        }
        return Math.sqrt(sum / timeData.length);
    }

    calculatePeak(timeData) {
        let peak = 0;
        for (let i = 0; i < timeData.length; i++) {
            peak = Math.max(peak, Math.abs(timeData[i]));
        }
        return peak;
    }

    calculateSpectralRolloff(frequencies) {
        let totalEnergy = 0;
        let runningSum = 0;

        // Calculate total energy
        for (let i = 0; i < frequencies.length; i++) {
            const magnitude = Math.max(0, frequencies[i] + 100);
            totalEnergy += magnitude;
        }

        // Find 85% rolloff point
        const threshold = totalEnergy * 0.85;
        for (let i = 0; i < frequencies.length; i++) {
            const magnitude = Math.max(0, frequencies[i] + 100);
            runningSum += magnitude;
            if (runningSum >= threshold) {
                return i * (this.sampleRate / 2) / frequencies.length;
            }
        }

        return 0;
    }

    calculateSpectralFlux(frequencies) {
        if (this.previousFrequencies) {
            let flux = 0;
            for (let i = 0; i < frequencies.length; i++) {
                const diff = frequencies[i] - this.previousFrequencies[i];
                if (diff > 0) flux += diff;
            }
            this.previousFrequencies = [...frequencies];
            return flux;
        }

        this.previousFrequencies = [...frequencies];
        return 0;
    }

    calculateDynamicRange() {
        if (this.voiceHistory.length < 10) return 0;

        const recentRMS = this.voiceHistory.slice(-10).map(entry => this.calculateRMS(entry.timeData));
        const min = Math.min(...recentRMS);
        const max = Math.max(...recentRMS);

        return 20 * Math.log10(max / (min + 1e-10)); // dB
    }

    analyzeFormants(frequencies) {
        // Simplified formant detection using spectral peaks
        const peaks = [];
        const smoothed = this.smoothSpectrum(frequencies);

        for (let i = 2; i < smoothed.length - 2; i++) {
            if (smoothed[i] > smoothed[i-1] && smoothed[i] > smoothed[i+1] &&
                smoothed[i] > smoothed[i-2] && smoothed[i] > smoothed[i+2]) {

                const frequency = i * (this.sampleRate / 2) / frequencies.length;
                if (frequency > 100 && frequency < 4000) { // Typical formant range
                    peaks.push({
                        frequency: frequency,
                        magnitude: smoothed[i]
                    });
                }
            }
        }

        return peaks.sort((a, b) => b.magnitude - a.magnitude).slice(0, 4);
    }

    smoothSpectrum(frequencies) {
        const smoothed = new Array(frequencies.length);
        const windowSize = 3;

        for (let i = 0; i < frequencies.length; i++) {
            let sum = 0;
            let count = 0;

            for (let j = Math.max(0, i - windowSize); j <= Math.min(frequencies.length - 1, i + windowSize); j++) {
                sum += Math.max(0, frequencies[j] + 100);
                count++;
            }

            smoothed[i] = sum / count;
        }

        return smoothed;
    }

    analyzeHarmonics(frequencies) {
        // Simple harmonic analysis
        const fundamentalBin = this.findFundamental(frequencies);
        if (fundamentalBin === -1) return { harmonics: [], strength: 0 };

        const harmonics = [];
        const fundamental = fundamentalBin * (this.sampleRate / 2) / frequencies.length;

        for (let h = 2; h <= 8; h++) {
            const harmonicFreq = fundamental * h;
            const harmonicBin = Math.round(harmonicFreq * frequencies.length / (this.sampleRate / 2));

            if (harmonicBin < frequencies.length) {
                harmonics.push({
                    harmonic: h,
                    frequency: harmonicFreq,
                    magnitude: Math.max(0, frequencies[harmonicBin] + 100)
                });
            }
        }

        const harmonicStrength = harmonics.reduce((sum, h) => sum + h.magnitude, 0) / harmonics.length;

        return {
            harmonics: harmonics,
            strength: harmonicStrength,
            fundamental: fundamental
        };
    }

    findFundamental(frequencies) {
        let maxBin = -1;
        let maxMagnitude = -Infinity;

        // Look for fundamental in typical voice range (80-400 Hz)
        const startBin = Math.floor(80 * frequencies.length / (this.sampleRate / 2));
        const endBin = Math.floor(400 * frequencies.length / (this.sampleRate / 2));

        for (let i = startBin; i <= endBin; i++) {
            const magnitude = frequencies[i];
            if (magnitude > maxMagnitude) {
                maxMagnitude = magnitude;
                maxBin = i;
            }
        }

        return maxMagnitude > -60 ? maxBin : -1; // Threshold for valid fundamental
    }

    generateVoicePrint() {
        if (this.voiceHistory.length < 20) return null;

        // Generate unique voice print characteristics
        const recentData = this.voiceHistory.slice(-20);

        const avgPitch = recentData.reduce((sum, d) => sum + (d.pitch || 0), 0) / recentData.length;
        const avgSpectralCentroid = recentData.reduce((sum, d) => sum + (d.spectralCentroid || 0), 0) / recentData.length;
        const avgZCR = recentData.reduce((sum, d) => sum + (d.zeroCrossingRate || 0), 0) / recentData.length;

        return {
            averagePitch: avgPitch,
            spectralCentroid: avgSpectralCentroid,
            zeroCrossingRate: avgZCR,
            dynamicRange: this.calculateDynamicRange(),
            voiceStability: this.calculateVoiceStability(recentData),
            uniquenessFactor: this.calculateUniquenessFactor(recentData)
        };
    }

    calculateVoiceStability(data) {
        const pitches = data.map(d => d.pitch || 0).filter(p => p > 0);
        if (pitches.length < 2) return 0;

        const mean = pitches.reduce((sum, p) => sum + p, 0) / pitches.length;
        const variance = pitches.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / pitches.length;

        return 1 / (1 + Math.sqrt(variance) / mean); // Normalized stability
    }

    calculateUniquenessFactor(data) {
        // Simple uniqueness based on spectral characteristics
        const features = data.map(d => [
            d.pitch || 0,
            d.spectralCentroid || 0,
            d.zeroCrossingRate || 0,
            d.inflection || 0
        ]);

        if (features.length < 2) return 0;

        let totalVariation = 0;
        for (let i = 0; i < features[0].length; i++) {
            const values = features.map(f => f[i]);
            const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
            const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
            totalVariation += Math.sqrt(variance);
        }

        return Math.min(1, totalVariation / features[0].length);
    }

    logTrigger(triggerData) {
        this.triggerHistory.unshift({
            ...triggerData,
            timestamp: Date.now()
        });

        if (this.triggerHistory.length > 100) {
            this.triggerHistory = this.triggerHistory.slice(0, 100);
        }
    }

    broadcastAnalysis(analysis) {
        const message = JSON.stringify({
            type: 'analysis',
            data: analysis,
            timestamp: Date.now()
        });

        this.clients.forEach(client => {
            if (client.readyState === client.OPEN) {
                client.send(message);
            }
        });
    }

    broadcastTrigger(triggerData) {
        const message = JSON.stringify({
            type: 'trigger',
            data: triggerData,
            timestamp: Date.now()
        });

        this.clients.forEach(client => {
            if (client.readyState === client.OPEN) {
                client.send(message);
            }
        });
    }

    async startWebServer() {
        this.server = createServer((req, res) => {
            if (req.url === '/') {
                this.serveOscilloscopeHTML(res);
            } else if (req.url === '/analysis') {
                this.serveAnalysisData(res);
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
            console.log('🔗 Client connected to oscilloscope demo');
            this.clients.add(ws);

            ws.on('close', () => {
                console.log('🔗 Client disconnected from oscilloscope demo');
                this.clients.delete(ws);
            });
        });
    }

    serveOscilloscopeHTML(res) {
        const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Oscilloscope Demo - D3.js Voice Analysis</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        body {
            margin: 0;
            font-family: 'Courier New', monospace;
            background: #000;
            color: #00ff00;
            overflow: hidden;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            height: 100vh;
            gap: 5px;
            padding: 5px;
        }

        .panel {
            border: 2px solid #00ff00;
            border-radius: 5px;
            padding: 10px;
            background: rgba(0, 255, 0, 0.05);
        }

        .panel h3 {
            margin: 0 0 10px 0;
            color: #00ff80;
            text-align: center;
        }

        #oscilloscope-panel {
            grid-column: 1 / 3;
        }

        .oscilloscope {
            width: 100%;
            height: 300px;
            background: #001100;
            border: 1px solid #00ff00;
        }

        .frequency-panel {
            background: rgba(255, 128, 0, 0.05);
            border-color: #ff8000;
        }

        .frequency-panel h3 {
            color: #ff8000;
        }

        .analysis-panel {
            background: rgba(0, 255, 255, 0.05);
            border-color: #00ffff;
        }

        .analysis-panel h3 {
            color: #00ffff;
        }

        .chart {
            background: #000;
            border: 1px solid;
        }

        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            font-size: 0.9em;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 8px;
            border-radius: 3px;
            border-left: 3px solid;
        }

        .trigger-log {
            height: 150px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid #00ff00;
            padding: 10px;
            margin-top: 10px;
        }

        .trigger-item {
            padding: 5px;
            margin: 3px 0;
            background: rgba(0, 255, 0, 0.1);
            border-left: 3px solid #00ff00;
            font-size: 0.8em;
        }

        .footer {
            position: fixed;
            bottom: 5px;
            right: 10px;
            font-size: 0.8em;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="panel" id="oscilloscope-panel">
            <h3>🌊 Advanced Voice Print Oscilloscope</h3>
            <svg class="oscilloscope" id="oscilloscope"></svg>
        </div>

        <div class="panel frequency-panel">
            <h3>🎵 Frequency Analysis & Triggers</h3>
            <svg class="chart" id="frequency-chart" width="100%" height="200"></svg>
            <div class="stats">
                <div class="stat-item" style="border-color: #ff8000;">
                    <div>RMS: <span id="rms-value">0</span></div>
                </div>
                <div class="stat-item" style="border-color: #ff8000;">
                    <div>Peak: <span id="peak-value">0</span></div>
                </div>
                <div class="stat-item" style="border-color: #ff8000;">
                    <div>Rolloff: <span id="rolloff-value">0</span> Hz</div>
                </div>
                <div class="stat-item" style="border-color: #ff8000;">
                    <div>Flux: <span id="flux-value">0</span></div>
                </div>
            </div>
        </div>

        <div class="panel analysis-panel">
            <h3>📊 Advanced Voice Analysis</h3>
            <div class="stats">
                <div class="stat-item" style="border-color: #00ffff;">
                    <div>Fundamental: <span id="fundamental-value">0</span> Hz</div>
                </div>
                <div class="stat-item" style="border-color: #00ffff;">
                    <div>Harmonics: <span id="harmonics-value">0</span></div>
                </div>
                <div class="stat-item" style="border-color: #00ffff;">
                    <div>Dynamic Range: <span id="range-value">0</span> dB</div>
                </div>
                <div class="stat-item" style="border-color: #00ffff;">
                    <div>Voice Stability: <span id="stability-value">0</span></div>
                </div>
            </div>
            <div class="trigger-log">
                <div style="color: #00ffff; font-weight: bold; margin-bottom: 10px;">Live Triggers</div>
                <div id="trigger-list"></div>
            </div>
        </div>
    </div>

    <div class="footer">
        © Professor Codephreak - Advanced Oscilloscope Demo
    </div>

    <script>
        class AdvancedOscilloscope {
            constructor() {
                this.ws = null;
                this.oscilloscope = null;
                this.frequencyChart = null;
                this.triggers = [];

                this.initWebSocket();
                this.initVisualizations();
            }

            initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                this.ws = new WebSocket(protocol + '//' + window.location.host);

                this.ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                };

                this.ws.onopen = () => console.log('Connected to oscilloscope demo');
                this.ws.onclose = () => {
                    console.log('Disconnected from oscilloscope demo');
                    setTimeout(() => this.initWebSocket(), 3000);
                };
            }

            initVisualizations() {
                this.initOscilloscope();
                this.initFrequencyChart();
            }

            initOscilloscope() {
                const svg = d3.select('#oscilloscope');
                const container = svg.node().getBoundingClientRect();

                this.oscilloscope = {
                    svg: svg,
                    width: container.width,
                    height: container.height,
                    xScale: d3.scaleLinear().domain([0, 2048]).range([0, container.width]),
                    yScale: d3.scaleLinear().domain([-1, 1]).range([container.height, 0])
                };

                // Add grid lines
                const xAxis = d3.axisBottom(this.oscilloscope.xScale).ticks(10);
                const yAxis = d3.axisLeft(this.oscilloscope.yScale).ticks(5);

                svg.append('g')
                    .attr('class', 'x-axis')
                    .attr('transform', \`translate(0, \${this.oscilloscope.height / 2})\`)
                    .call(xAxis)
                    .selectAll('text, line').style('stroke', '#003300').style('fill', '#003300');

                svg.append('g')
                    .attr('class', 'y-axis')
                    .call(yAxis)
                    .selectAll('text, line').style('stroke', '#003300').style('fill', '#003300');

                // Add waveform path
                svg.append('path')
                    .attr('class', 'waveform')
                    .style('fill', 'none')
                    .style('stroke', '#00ff00')
                    .style('stroke-width', 2);
            }

            initFrequencyChart() {
                const svg = d3.select('#frequency-chart');
                const container = svg.node().getBoundingClientRect();

                this.frequencyChart = {
                    svg: svg,
                    width: container.width,
                    height: container.height,
                    xScale: d3.scaleLinear().domain([0, 512]).range([0, container.width]),
                    yScale: d3.scaleLinear().domain([0, 100]).range([container.height, 0])
                };
            }

            handleMessage(message) {
                switch (message.type) {
                    case 'analysis':
                        this.updateAnalysis(message.data);
                        break;
                    case 'trigger':
                        this.addTrigger(message.data);
                        break;
                }
            }

            updateAnalysis(analysis) {
                // Update statistics
                document.getElementById('rms-value').textContent = analysis.rms?.toFixed(4) || '0';
                document.getElementById('peak-value').textContent = analysis.peak?.toFixed(4) || '0';
                document.getElementById('rolloff-value').textContent = Math.round(analysis.spectralRolloff || 0);
                document.getElementById('flux-value').textContent = analysis.spectralFlux?.toFixed(2) || '0';

                if (analysis.harmonicContent) {
                    document.getElementById('fundamental-value').textContent = Math.round(analysis.harmonicContent.fundamental || 0);
                    document.getElementById('harmonics-value').textContent = analysis.harmonicContent.harmonics?.length || 0;
                }

                document.getElementById('range-value').textContent = analysis.dynamicRange?.toFixed(1) || '0';

                if (analysis.voicePrint) {
                    document.getElementById('stability-value').textContent = analysis.voicePrint.voiceStability?.toFixed(3) || '0';
                }
            }

            addTrigger(trigger) {
                this.triggers.unshift(trigger);
                if (this.triggers.length > 15) {
                    this.triggers = this.triggers.slice(0, 15);
                }

                const triggerList = document.getElementById('trigger-list');
                triggerList.innerHTML = this.triggers.map(t => \`
                    <div class="trigger-item">
                        <strong>\${t.trigger}</strong> → \${t.response}<br>
                        <small>\${new Date().toLocaleTimeString()}</small>
                    </div>
                \`).join('');
            }
        }

        // Start oscilloscope demo
        window.addEventListener('load', () => {
            new AdvancedOscilloscope();
        });
    </script>
</body>
</html>
        `;

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(html);
    }

    serveAnalysisData(res) {
        const data = {
            voiceHistory: this.voiceHistory.slice(-50),
            triggerHistory: this.triggerHistory.slice(-20),
            analysisWindow: this.analysisWindow,
            bufferSize: this.bufferSize,
            sampleRate: this.sampleRate
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data, null, 2));
    }
}

// Start oscilloscope demo
const demo = new OscilloscopeDemo();
demo.start().catch(console.error);