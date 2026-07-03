/**
 * VoiceCreationEngine.js - Advanced Voice Creation & TTS System
 *
 * © Professor Codephreak - rage.pythai.net
 * Autonomous voice creation engine with frequency modulation and inflection control
 *
 * Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak
 */

import { EventEmitter } from 'events';
import { spawn } from 'child_process';
import { promises as fs } from 'fs';
import { join } from 'path';

export class VoiceCreationEngine extends EventEmitter {
    constructor(options = {}) {
        super();

        // Configuration
        this.agentId = options.agentId || 'faicey-voice';
        this.voiceId = options.voiceId || 'jaimla';
        this.outputPath = options.outputPath || '/tmp/faicey-voice';
        this.sampleRate = options.sampleRate || 44100;

        // TTS Engine options
        this.ttsEngine = options.ttsEngine || 'espeak-ng'; // espeak-ng, festival, flite, pico2wave
        this.voice = options.voice || 'en-us+f3'; // Female voice variant
        this.speed = options.speed || 175; // Words per minute
        this.pitch = options.pitch || 50; // Base pitch (0-99)
        this.gap = options.gap || 10; // Word gap in 10ms units

        // Voice characteristics for Jaimla persona
        this.voiceCharacteristics = {
            jaimla: {
                gender: 'female',
                basePitch: 55,        // Higher pitch for female voice
                pitchRange: 20,       // Pitch variation range
                speed: 180,           // Slightly faster speech
                timbre: 'bright',     // Voice timbre
                energy: 0.8,          // Energy level (0-1)
                warmth: 0.9,          // Warmth factor (0-1)
                breathiness: 0.3,     // Breathiness (0-1)
                resonance: 'head'     // Resonance type
            },
            professor: {
                gender: 'male',
                basePitch: 35,
                pitchRange: 15,
                speed: 160,
                timbre: 'deep',
                energy: 0.7,
                warmth: 0.6,
                breathiness: 0.1,
                resonance: 'chest'
            }
        };

        // Frequency modulation settings
        this.frequencySettings = {
            inflectionMultiplier: 1.2,    // Multiplier for inflection emphasis
            questionRise: 1.5,            // Pitch rise for questions
            exclamationBoost: 1.3,        // Boost for exclamations
            emphasisRange: 0.8,           // Range for emphasis
            pauseDuration: 200,           // Pause duration in ms
            breathPauses: true,           // Add natural breath pauses
            emotionalModulation: true     // Enable emotional pitch changes
        };

        // Available TTS engines and their capabilities
        this.ttsEngines = {
            'espeak-ng': {
                binary: 'espeak-ng',
                voicePrefix: 'en-us',
                supports: ['pitch', 'speed', 'amplitude', 'word-gap'],
                quality: 'medium',
                responsiveness: 'high'
            },
            'festival': {
                binary: 'festival',
                voicePrefix: 'voice_',
                supports: ['pitch', 'speed', 'intonation'],
                quality: 'high',
                responsiveness: 'medium'
            },
            'flite': {
                binary: 'flite',
                voicePrefix: '',
                supports: ['speed', 'pitch-shift'],
                quality: 'medium',
                responsiveness: 'high'
            },
            'pico2wave': {
                binary: 'pico2wave',
                voicePrefix: 'en-US',
                supports: ['language'],
                quality: 'good',
                responsiveness: 'high'
            }
        };

        // Voice state
        this.currentCharacteristics = null;
        this.isGenerating = false;
        this.voiceQueue = [];
        this.generatedFiles = [];

        // Initialize engine
        this.init();
    }

    /**
     * Initialize voice creation engine
     */
    async init() {
        console.log('🗣️ Initializing Voice Creation Engine...');
        console.log(`🎭 Agent: ${this.agentId}, Voice: ${this.voiceId}`);

        try {
            // Create output directory
            await this.ensureOutputDirectory();

            // Check TTS engine availability
            await this.checkTTSEngines();

            // Set voice characteristics for current voice ID
            this.setVoiceCharacteristics(this.voiceId);

            // Initialize audio processing
            await this.initializeAudioProcessing();

            this.emit('initialized', {
                agentId: this.agentId,
                voiceId: this.voiceId,
                engine: this.ttsEngine,
                characteristics: this.currentCharacteristics
            });

            console.log('✅ Voice Creation Engine initialized');

        } catch (error) {
            console.error('❌ Voice Creation Engine initialization failed:', error);
            this.emit('error', error);
        }
    }

    /**
     * Ensure output directory exists
     */
    async ensureOutputDirectory() {
        try {
            await fs.mkdir(this.outputPath, { recursive: true });
            console.log(`📁 Output directory ready: ${this.outputPath}`);
        } catch (error) {
            throw new Error(`Failed to create output directory: ${error.message}`);
        }
    }

    /**
     * Check available TTS engines
     */
    async checkTTSEngines() {
        console.log('🔍 Checking TTS engines...');

        for (const [engine, config] of Object.entries(this.ttsEngines)) {
            try {
                await this.testTTSEngine(engine);
                console.log(`✅ ${engine} available`);
            } catch (error) {
                console.log(`❌ ${engine} not available: ${error.message}`);
            }
        }

        // Verify selected engine is available
        try {
            await this.testTTSEngine(this.ttsEngine);
            console.log(`✅ Selected TTS engine ${this.ttsEngine} verified`);
        } catch (error) {
            console.warn(`⚠️ Selected engine ${this.ttsEngine} not available, falling back to espeak-ng`);
            this.ttsEngine = 'espeak-ng';
            await this.testTTSEngine(this.ttsEngine);
        }
    }

    /**
     * Test specific TTS engine availability
     */
    async testTTSEngine(engine) {
        const config = this.ttsEngines[engine];
        if (!config) {
            throw new Error(`Unknown TTS engine: ${engine}`);
        }

        return new Promise((resolve, reject) => {
            const process = spawn(config.binary, ['--version'], { stdio: 'pipe' });

            process.on('error', (error) => {
                reject(new Error(`${config.binary} not found: ${error.message}`));
            });

            process.on('close', (code) => {
                if (code === 0 || code === 1) { // Some TTS engines exit with 1 on --version
                    resolve();
                } else {
                    reject(new Error(`${config.binary} test failed with code ${code}`));
                }
            });
        });
    }

    /**
     * Set voice characteristics for specific persona
     */
    setVoiceCharacteristics(voiceId) {
        if (this.voiceCharacteristics[voiceId]) {
            this.currentCharacteristics = { ...this.voiceCharacteristics[voiceId] };
            this.voiceId = voiceId;

            // Update engine settings based on characteristics
            this.pitch = this.currentCharacteristics.basePitch;
            this.speed = this.currentCharacteristics.speed;

            console.log(`🎭 Voice characteristics set for ${voiceId}:`, this.currentCharacteristics);

            this.emit('voiceCharacteristicsChanged', {
                voiceId: voiceId,
                characteristics: this.currentCharacteristics
            });
        } else {
            console.warn(`⚠️ Unknown voice ID: ${voiceId}, using default characteristics`);
        }
    }

    /**
     * Initialize audio processing capabilities
     */
    async initializeAudioProcessing() {
        // Check for additional audio processing tools
        const audioTools = ['sox', 'ffmpeg', 'paplay', 'aplay'];

        for (const tool of audioTools) {
            try {
                await this.testCommand(tool, ['--version']);
                console.log(`✅ Audio tool available: ${tool}`);
            } catch (error) {
                console.log(`❌ Audio tool not available: ${tool}`);
            }
        }
    }

    /**
     * Test command availability
     */
    async testCommand(command, args = []) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, { stdio: 'pipe' });
            process.on('error', reject);
            process.on('close', (code) => {
                if (code === 0 || code === 1) {
                    resolve();
                } else {
                    reject(new Error(`Command failed with code ${code}`));
                }
            });
        });
    }

    /**
     * Generate speech from text with advanced options
     */
    async generateSpeech(text, options = {}) {
        console.log(`🗣️ Generating speech: "${text.substring(0, 50)}..."`);

        if (this.isGenerating) {
            // Queue the request
            this.voiceQueue.push({ text, options });
            console.log('📋 Speech request queued');
            return;
        }

        this.isGenerating = true;

        try {
            // Analyze text for inflection and emotional content
            const analysis = this.analyzeText(text);

            // Generate modified characteristics based on analysis
            const modifiedCharacteristics = this.applyTextAnalysis(analysis, options);

            // Generate speech file
            const outputFile = await this.generateTTSSpeech(text, modifiedCharacteristics);

            // Apply frequency modulation if needed
            const processedFile = await this.applyFrequencyModulation(outputFile, analysis);

            // Store generated file info
            this.generatedFiles.push({
                text: text,
                file: processedFile,
                analysis: analysis,
                characteristics: modifiedCharacteristics,
                timestamp: Date.now()
            });

            this.emit('speechGenerated', {
                text: text,
                file: processedFile,
                analysis: analysis,
                duration: await this.getAudioDuration(processedFile)
            });

            console.log(`✅ Speech generated: ${processedFile}`);

            // Process queue
            this.isGenerating = false;
            if (this.voiceQueue.length > 0) {
                const next = this.voiceQueue.shift();
                setTimeout(() => this.generateSpeech(next.text, next.options), 100);
            }

            return processedFile;

        } catch (error) {
            this.isGenerating = false;
            console.error('❌ Speech generation failed:', error);
            this.emit('speechError', { text, error: error.message });
            throw error;
        }
    }

    /**
     * Analyze text for emotional content and inflection patterns
     */
    analyzeText(text) {
        const analysis = {
            length: text.length,
            wordCount: text.split(' ').length,
            sentiment: 'neutral',
            inflections: [],
            emphasis: [],
            punctuation: [],
            emotionalMarkers: []
        };

        // Detect questions
        if (text.includes('?')) {
            analysis.inflections.push({ type: 'question', intensity: 0.8 });
            analysis.punctuation.push('question');
        }

        // Detect exclamations
        if (text.includes('!')) {
            analysis.inflections.push({ type: 'exclamation', intensity: 0.9 });
            analysis.punctuation.push('exclamation');
        }

        // Detect emotional words
        const positiveWords = ['happy', 'excited', 'great', 'wonderful', 'amazing', 'fantastic'];
        const negativeWords = ['sad', 'angry', 'terrible', 'awful', 'frustrated', 'disappointed'];

        positiveWords.forEach(word => {
            if (text.toLowerCase().includes(word)) {
                analysis.emotionalMarkers.push({ word, sentiment: 'positive', intensity: 0.7 });
                analysis.sentiment = 'positive';
            }
        });

        negativeWords.forEach(word => {
            if (text.toLowerCase().includes(word)) {
                analysis.emotionalMarkers.push({ word, sentiment: 'negative', intensity: 0.7 });
                analysis.sentiment = 'negative';
            }
        });

        // Detect emphasis (ALL CAPS words)
        const emphasisMatches = text.match(/\b[A-Z]{2,}\b/g);
        if (emphasisMatches) {
            emphasisMatches.forEach(word => {
                analysis.emphasis.push({ word, intensity: 0.8 });
            });
        }

        // Detect collaborative language (for Jaimla)
        const collaborativeWords = ['together', 'collaborate', 'work', 'team', 'help'];
        collaborativeWords.forEach(word => {
            if (text.toLowerCase().includes(word)) {
                analysis.emotionalMarkers.push({ word, sentiment: 'collaborative', intensity: 0.6 });
            }
        });

        console.log('📊 Text analysis:', analysis);

        return analysis;
    }

    /**
     * Apply text analysis to voice characteristics
     */
    applyTextAnalysis(analysis, options = {}) {
        const modified = { ...this.currentCharacteristics };

        // Apply sentiment modifications
        if (analysis.sentiment === 'positive') {
            modified.basePitch += 5;
            modified.speed += 10;
            modified.energy += 0.1;
        } else if (analysis.sentiment === 'negative') {
            modified.basePitch -= 3;
            modified.speed -= 5;
            modified.energy -= 0.1;
        }

        // Apply inflection modifications
        analysis.inflections.forEach(inflection => {
            if (inflection.type === 'question') {
                modified.basePitch += Math.floor(inflection.intensity * this.frequencySettings.questionRise * 10);
            } else if (inflection.type === 'exclamation') {
                modified.basePitch += Math.floor(inflection.intensity * this.frequencySettings.exclamationBoost * 10);
            }
        });

        // Apply emphasis modifications
        if (analysis.emphasis.length > 0) {
            modified.energy += 0.2;
            modified.basePitch += 3;
        }

        // Apply user options
        if (options.pitch !== undefined) {
            modified.basePitch = Math.max(0, Math.min(99, modified.basePitch + options.pitch));
        }

        if (options.speed !== undefined) {
            modified.speed = Math.max(80, Math.min(300, modified.speed + options.speed));
        }

        if (options.energy !== undefined) {
            modified.energy = Math.max(0, Math.min(1, options.energy));
        }

        console.log('🎛️ Modified characteristics:', modified);

        return modified;
    }

    /**
     * Generate TTS speech using selected engine
     */
    async generateTTSSpeech(text, characteristics) {
        const timestamp = Date.now();
        const filename = `speech_${this.voiceId}_${timestamp}.wav`;
        const outputFile = join(this.outputPath, filename);

        console.log(`🔧 Generating TTS with ${this.ttsEngine}...`);

        switch (this.ttsEngine) {
            case 'espeak-ng':
                return await this.generateEspeakSpeech(text, outputFile, characteristics);

            case 'festival':
                return await this.generateFestivalSpeech(text, outputFile, characteristics);

            case 'flite':
                return await this.generateFliteSpeech(text, outputFile, characteristics);

            case 'pico2wave':
                return await this.generatePicoSpeech(text, outputFile, characteristics);

            default:
                throw new Error(`Unsupported TTS engine: ${this.ttsEngine}`);
        }
    }

    /**
     * Generate speech using espeak-ng
     */
    async generateEspeakSpeech(text, outputFile, characteristics) {
        const args = [
            '-v', `${this.voice}`,
            '-p', characteristics.basePitch.toString(),
            '-s', characteristics.speed.toString(),
            '-g', this.gap.toString(),
            '-a', Math.floor(characteristics.energy * 100).toString(),
            '-w', outputFile,
            text
        ];

        return new Promise((resolve, reject) => {
            const process = spawn('espeak-ng', args);

            process.on('error', (error) => {
                reject(new Error(`espeak-ng failed: ${error.message}`));
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve(outputFile);
                } else {
                    reject(new Error(`espeak-ng exited with code ${code}`));
                }
            });
        });
    }

    /**
     * Generate speech using festival
     */
    async generateFestivalSpeech(text, outputFile, characteristics) {
        // Create festival script
        const script = `
(voice_${characteristics.gender === 'female' ? 'kal_diphone' : 'ked_diphone'})
(Parameter.set 'Duration_Stretch ${1.0 / (characteristics.speed / 170)})
(SayText "${text.replace(/"/g, '\\"')}")
(utt.save.wave (SayText "${text.replace(/"/g, '\\"')}") "${outputFile}")
`;

        const scriptFile = join(this.outputPath, `script_${Date.now()}.scm`);
        await fs.writeFile(scriptFile, script);

        return new Promise((resolve, reject) => {
            const process = spawn('festival', ['--batch', scriptFile]);

            process.on('error', (error) => {
                reject(new Error(`Festival failed: ${error.message}`));
            });

            process.on('close', (code) => {
                // Clean up script file
                fs.unlink(scriptFile).catch(() => {});

                if (code === 0) {
                    resolve(outputFile);
                } else {
                    reject(new Error(`Festival exited with code ${code}`));
                }
            });
        });
    }

    /**
     * Generate speech using flite
     */
    async generateFliteSpeech(text, outputFile, characteristics) {
        const voice = characteristics.gender === 'female' ? 'slt' : 'awb';

        return new Promise((resolve, reject) => {
            const process = spawn('flite', [
                '-voice', voice,
                '-t', text,
                '-o', outputFile
            ]);

            process.on('error', (error) => {
                reject(new Error(`Flite failed: ${error.message}`));
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve(outputFile);
                } else {
                    reject(new Error(`Flite exited with code ${code}`));
                }
            });
        });
    }

    /**
     * Generate speech using pico2wave
     */
    async generatePicoSpeech(text, outputFile, characteristics) {
        const lang = 'en-US';

        return new Promise((resolve, reject) => {
            const process = spawn('pico2wave', [
                '-l', lang,
                '-w', outputFile,
                text
            ]);

            process.on('error', (error) => {
                reject(new Error(`Pico2wave failed: ${error.message}`));
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve(outputFile);
                } else {
                    reject(new Error(`Pico2wave exited with code ${code}`));
                }
            });
        });
    }

    /**
     * Apply frequency modulation to generated speech
     */
    async applyFrequencyModulation(inputFile, analysis) {
        // Check if sox is available for audio processing
        try {
            await this.testCommand('sox', ['--version']);
        } catch (error) {
            console.log('⚠️ Sox not available, skipping frequency modulation');
            return inputFile;
        }

        const timestamp = Date.now();
        const modifiedFile = join(this.outputPath, `modified_${timestamp}.wav`);

        try {
            // Build sox effects chain
            const effects = [];

            // Apply pitch variations based on inflections
            if (analysis.inflections.length > 0) {
                analysis.inflections.forEach(inflection => {
                    if (inflection.type === 'question') {
                        effects.push('pitch', '+200'); // Raise pitch for questions
                    } else if (inflection.type === 'exclamation') {
                        effects.push('overdrive', '10'); // Add energy for exclamations
                    }
                });
            }

            // Add tremolo for emotional content
            if (analysis.sentiment === 'positive') {
                effects.push('tremolo', '6', '0.5'); // Light tremolo for happiness
            }

            // Apply emphasis effects
            if (analysis.emphasis.length > 0) {
                effects.push('gain', '3'); // Increase volume for emphasis
            }

            // Always normalize and apply gentle compression
            effects.push('compand', '0.02,0.05', '-60,-60,-30,-15,-20,-10,-5,-8,-2,-8', '-8', '-7', '0.05');
            effects.push('norm', '-1');

            if (effects.length > 0) {
                const args = [inputFile, modifiedFile, ...effects];

                await new Promise((resolve, reject) => {
                    const process = spawn('sox', args);

                    process.on('error', (error) => {
                        reject(new Error(`Sox processing failed: ${error.message}`));
                    });

                    process.on('close', (code) => {
                        if (code === 0) {
                            resolve();
                        } else {
                            reject(new Error(`Sox exited with code ${code}`));
                        }
                    });
                });

                console.log('🎛️ Frequency modulation applied');
                return modifiedFile;
            }

        } catch (error) {
            console.warn('⚠️ Frequency modulation failed:', error.message);
        }

        return inputFile;
    }

    /**
     * Get audio file duration
     */
    async getAudioDuration(audioFile) {
        try {
            await this.testCommand('sox', ['--version']);

            return new Promise((resolve, reject) => {
                const process = spawn('sox', [audioFile, '-n', 'stat'], { stdio: ['pipe', 'pipe', 'pipe'] });

                let stderr = '';
                process.stderr.on('data', (data) => {
                    stderr += data.toString();
                });

                process.on('close', (code) => {
                    if (code === 0) {
                        const match = stderr.match(/Length \(seconds\):\s*([0-9.]+)/);
                        if (match) {
                            resolve(parseFloat(match[1]));
                        } else {
                            resolve(0);
                        }
                    } else {
                        resolve(0);
                    }
                });
            });

        } catch (error) {
            return 0;
        }
    }

    /**
     * Play generated speech
     */
    async playSpeech(audioFile) {
        try {
            // Try different audio players
            const players = ['paplay', 'aplay', 'play'];

            for (const player of players) {
                try {
                    await this.testCommand(player, ['--version']);
                    console.log(`🔊 Playing audio with ${player}...`);

                    return new Promise((resolve, reject) => {
                        const args = player === 'play' ? [audioFile] : [audioFile];
                        const process = spawn(player, args);

                        process.on('error', (error) => {
                            reject(new Error(`${player} failed: ${error.message}`));
                        });

                        process.on('close', (code) => {
                            if (code === 0) {
                                resolve();
                            } else {
                                reject(new Error(`${player} exited with code ${code}`));
                            }
                        });
                    });

                } catch (error) {
                    continue;
                }
            }

            throw new Error('No audio player available');

        } catch (error) {
            console.error('❌ Failed to play audio:', error);
            this.emit('playError', { file: audioFile, error: error.message });
        }
    }

    /**
     * Generate and play speech in one call
     */
    async speak(text, options = {}) {
        try {
            const audioFile = await this.generateSpeech(text, options);

            if (options.autoPlay !== false) {
                await this.playSpeech(audioFile);
            }

            return audioFile;

        } catch (error) {
            console.error('❌ Speak failed:', error);
            throw error;
        }
    }

    /**
     * Get voice engine status
     */
    getStatus() {
        return {
            agentId: this.agentId,
            voiceId: this.voiceId,
            ttsEngine: this.ttsEngine,
            characteristics: this.currentCharacteristics,
            isGenerating: this.isGenerating,
            queueLength: this.voiceQueue.length,
            generatedFiles: this.generatedFiles.length,
            outputPath: this.outputPath,
            lastGeneration: this.generatedFiles[this.generatedFiles.length - 1]?.timestamp || null
        };
    }

    /**
     * Clean up generated files
     */
    async cleanup() {
        console.log('🧹 Cleaning up voice files...');

        try {
            // Remove old generated files
            const cutoffTime = Date.now() - (24 * 60 * 60 * 1000); // 24 hours

            for (const fileInfo of this.generatedFiles) {
                if (fileInfo.timestamp < cutoffTime) {
                    try {
                        await fs.unlink(fileInfo.file);
                        console.log(`🗑️ Removed old file: ${fileInfo.file}`);
                    } catch (error) {
                        console.warn(`Failed to remove ${fileInfo.file}:`, error.message);
                    }
                }
            }

            // Update file list
            this.generatedFiles = this.generatedFiles.filter(f => f.timestamp >= cutoffTime);

            console.log('✅ Voice file cleanup complete');

        } catch (error) {
            console.error('❌ Cleanup failed:', error);
        }
    }

    /**
     * Shutdown voice engine
     */
    async shutdown() {
        console.log('🛑 Shutting down Voice Creation Engine...');

        // Clear queue
        this.voiceQueue = [];
        this.isGenerating = false;

        // Optional cleanup
        if (process.env.FAICEY_CLEANUP_ON_SHUTDOWN === 'true') {
            await this.cleanup();
        }

        this.emit('shutdown', { timestamp: Date.now() });

        console.log('✅ Voice Creation Engine shutdown complete');
    }
}

export default VoiceCreationEngine;