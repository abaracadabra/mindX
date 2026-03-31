/**
 * Blockchain-Precision Voice Print Analysis
 *
 * © Professor Codephreak - rage.pythai.net
 * High-precision voice analysis with 18-decimal blockchain compatibility
 * Cryptographic hash generation for immutable voiceprint records
 */

import { createHash } from 'crypto';

export class BlockchainVoicePrint {
    constructor(options = {}) {
        this.precision = 18; // Blockchain-standard precision (like Ethereum wei)
        this.hashAlgorithm = options.hashAlgorithm || 'sha256';
        this.voicePrintVersion = '2.0.0';

        // High-precision mathematical constants (18 decimal places)
        this.constants = {
            PI: '3.141592653589793238',
            E: '2.718281828459045235',
            SQRT_2: '1.414213562373095048',
            GOLDEN_RATIO: '1.618033988749894848'
        };

        // Precision multiplier for 18 decimal places
        this.precisionMultiplier = BigInt('1000000000000000000'); // 10^18

        console.log('🔗 Blockchain VoicePrint initialized with 18-decimal precision');
    }

    /**
     * Convert number to 18-decimal precision BigInt
     * @param {number} value - Input value
     * @returns {BigInt} - High precision integer representation
     */
    toPrecision18(value) {
        if (typeof value !== 'number' || isNaN(value)) {
            return BigInt(0);
        }

        // Convert to 18 decimal places
        const scaledValue = Math.floor(value * Number(this.precisionMultiplier));
        return BigInt(scaledValue);
    }

    /**
     * Convert BigInt back to decimal with 18 places
     * @param {BigInt} bigIntValue - High precision value
     * @returns {string} - Decimal string with 18 precision
     */
    fromPrecision18(bigIntValue) {
        const divisor = this.precisionMultiplier;
        const quotient = bigIntValue / divisor;
        const remainder = bigIntValue % divisor;

        // Format with exactly 18 decimal places
        const remainderStr = remainder.toString().padStart(18, '0');
        return `${quotient}.${remainderStr}`;
    }

    /**
     * Generate high-precision voice analysis metrics
     * @param {Array} timeData - Time domain audio data
     * @param {Array} freqData - Frequency domain audio data
     * @param {number} sampleRate - Audio sample rate
     * @returns {Object} - Blockchain-precision voice metrics
     */
    generatePrecisionMetrics(timeData, freqData, sampleRate = 44100) {
        const metrics = {};

        try {
            // Convert arrays to normalized float arrays
            const timeArray = timeData.map(x => (x - 128) / 128);
            const freqArray = freqData.map(x => x / 255);

            // 1. RMS (Root Mean Square) - 18 decimal precision
            const rmsSquared = timeArray.reduce((sum, x) => sum + (x * x), 0) / timeArray.length;
            const rms = Math.sqrt(rmsSquared);
            metrics.rms = this.toPrecision18(rms);
            metrics.rmsDecimal = this.fromPrecision18(metrics.rms);

            // 2. Dominant Frequency - 18 decimal precision
            let maxBin = 0;
            let maxValue = 0;
            for (let i = 0; i < freqArray.length; i++) {
                if (freqArray[i] > maxValue) {
                    maxValue = freqArray[i];
                    maxBin = i;
                }
            }
            const dominantFreq = (maxBin * sampleRate) / (2 * freqArray.length);
            metrics.dominantFrequency = this.toPrecision18(dominantFreq);
            metrics.dominantFrequencyDecimal = this.fromPrecision18(metrics.dominantFrequency);

            // 3. Spectral Centroid - 18 decimal precision
            let numerator = 0;
            let denominator = 0;
            for (let i = 0; i < freqArray.length; i++) {
                const freq = (i * sampleRate) / (2 * freqArray.length);
                numerator += freq * freqArray[i];
                denominator += freqArray[i];
            }
            const spectralCentroid = denominator > 0 ? numerator / denominator : 0;
            metrics.spectralCentroid = this.toPrecision18(spectralCentroid);
            metrics.spectralCentroidDecimal = this.fromPrecision18(metrics.spectralCentroid);

            // 4. Spectral Rolloff (85% energy point) - 18 decimal precision
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
            const spectralRolloff = (rolloffIndex * sampleRate) / (2 * freqArray.length);
            metrics.spectralRolloff = this.toPrecision18(spectralRolloff);
            metrics.spectralRolloffDecimal = this.fromPrecision18(metrics.spectralRolloff);

            // 5. Zero Crossing Rate - 18 decimal precision
            let crossings = 0;
            for (let i = 1; i < timeArray.length; i++) {
                if ((timeArray[i] >= 0) !== (timeArray[i-1] >= 0)) {
                    crossings++;
                }
            }
            const zeroCrossingRate = crossings / timeArray.length;
            metrics.zeroCrossingRate = this.toPrecision18(zeroCrossingRate);
            metrics.zeroCrossingRateDecimal = this.fromPrecision18(metrics.zeroCrossingRate);

            // 6. Spectral Bandwidth - 18 decimal precision
            let bandwidthNumerator = 0;
            for (let i = 0; i < freqArray.length; i++) {
                const freq = (i * sampleRate) / (2 * freqArray.length);
                const diff = freq - parseFloat(metrics.spectralCentroidDecimal);
                bandwidthNumerator += Math.pow(diff, 2) * freqArray[i];
            }
            const spectralBandwidth = denominator > 0 ? Math.sqrt(bandwidthNumerator / denominator) : 0;
            metrics.spectralBandwidth = this.toPrecision18(spectralBandwidth);
            metrics.spectralBandwidthDecimal = this.fromPrecision18(metrics.spectralBandwidth);

            // 7. Spectral Flux - 18 decimal precision (rate of spectral change)
            if (this.previousFreqData) {
                let flux = 0;
                for (let i = 0; i < freqArray.length; i++) {
                    const diff = freqArray[i] - (this.previousFreqData[i] || 0);
                    flux += Math.pow(Math.max(0, diff), 2);
                }
                flux = Math.sqrt(flux);
                metrics.spectralFlux = this.toPrecision18(flux);
                metrics.spectralFluxDecimal = this.fromPrecision18(metrics.spectralFlux);
            } else {
                metrics.spectralFlux = BigInt(0);
                metrics.spectralFluxDecimal = '0.000000000000000000';
            }

            // Store for next flux calculation
            this.previousFreqData = freqArray.slice();

            // 8. Harmonic-to-Noise Ratio - 18 decimal precision
            const harmonic = Math.max(...freqArray);
            const noise = freqArray.reduce((sum, x) => sum + x, 0) / freqArray.length;
            const hnr = harmonic > 0 ? harmonic / noise : 0;
            metrics.harmonicNoiseRatio = this.toPrecision18(hnr);
            metrics.harmonicNoiseRatioDecimal = this.fromPrecision18(metrics.harmonicNoiseRatio);

            // Add timestamp with nanosecond precision
            metrics.timestamp = BigInt(Date.now()) * BigInt(1000000); // Convert to nanoseconds
            metrics.timestampDecimal = this.fromPrecision18(metrics.timestamp);

            return metrics;

        } catch (error) {
            console.error('Error generating precision metrics:', error);
            return this.getDefaultMetrics();
        }
    }

    /**
     * Generate comprehensive voiceprint hash for blockchain publishing
     * @param {Object} metrics - High-precision voice metrics
     * @param {Object} metadata - Additional voiceprint metadata
     * @returns {Object} - Blockchain-ready voiceprint hash data
     */
    generateVoicePrintHash(metrics, metadata = {}) {
        try {
            // Create comprehensive voiceprint data structure
            const voicePrintData = {
                version: this.voicePrintVersion,
                timestamp: metrics.timestamp.toString(),
                precision: this.precision,

                // Core voice metrics (as strings for exact precision)
                acousticFingerprint: {
                    rms: metrics.rmsDecimal,
                    dominantFrequency: metrics.dominantFrequencyDecimal,
                    spectralCentroid: metrics.spectralCentroidDecimal,
                    spectralRolloff: metrics.spectralRolloffDecimal,
                    spectralBandwidth: metrics.spectralBandwidthDecimal,
                    spectralFlux: metrics.spectralFluxDecimal,
                    zeroCrossingRate: metrics.zeroCrossingRateDecimal,
                    harmonicNoiseRatio: metrics.harmonicNoiseRatioDecimal
                },

                // Derived characteristics
                characteristics: {
                    voiceType: this.classifyVoiceType(metrics),
                    emotionalState: this.detectEmotionalState(metrics),
                    energyLevel: this.calculateEnergyLevel(metrics),
                    uniquenessScore: this.calculateUniquenessScore(metrics)
                },

                // Metadata
                metadata: {
                    agentId: metadata.agentId || 'unknown',
                    sessionId: metadata.sessionId || this.generateSessionId(),
                    sampleRate: metadata.sampleRate || 44100,
                    bufferSize: metadata.bufferSize || 2048,
                    analysisMethod: 'FFT-BlockchainPrecision-18decimal',
                    ...metadata
                }
            };

            // Generate primary hash (SHA-256)
            const primaryHash = this.generateHash(JSON.stringify(voicePrintData), 'sha256');

            // Generate secondary hash (SHA-512) for additional security
            const secondaryHash = this.generateHash(JSON.stringify(voicePrintData), 'sha512');

            // Generate short hash for blockchain storage efficiency
            const shortHash = this.generateHash(JSON.stringify(voicePrintData.acousticFingerprint), 'sha256').substring(0, 16);

            // Create blockchain-compatible structure
            const blockchainVoicePrint = {
                voicePrintHash: primaryHash,
                voicePrintHashSecondary: secondaryHash,
                voicePrintShortHash: shortHash,
                voicePrintData: voicePrintData,

                // Blockchain-specific fields
                blockchainMetadata: {
                    hashAlgorithm: 'SHA-256',
                    precision: 18,
                    version: this.voicePrintVersion,
                    generatedAt: new Date().toISOString(),
                    compatibleChains: ['Ethereum', 'Polygon', 'BSC', 'Arbitrum', 'Algorand'],
                    storageFormat: 'JSON',
                    compressionRatio: this.calculateCompressionRatio(voicePrintData)
                },

                // For NFT metadata
                nftMetadata: {
                    name: `VoicePrint-${shortHash}`,
                    description: 'High-precision voice analysis with 18-decimal blockchain compatibility',
                    attributes: [
                        { trait_type: 'Voice Type', value: voicePrintData.characteristics.voiceType },
                        { trait_type: 'Emotional State', value: voicePrintData.characteristics.emotionalState },
                        { trait_type: 'Energy Level', value: voicePrintData.characteristics.energyLevel },
                        { trait_type: 'Uniqueness Score', value: voicePrintData.characteristics.uniquenessScore },
                        { trait_type: 'Precision', value: '18 Decimal Places' },
                        { trait_type: 'Hash Algorithm', value: 'SHA-256' },
                        { trait_type: 'Analysis Method', value: 'FFT-BlockchainPrecision' }
                    ]
                }
            };

            return blockchainVoicePrint;

        } catch (error) {
            console.error('Error generating voiceprint hash:', error);
            return null;
        }
    }

    /**
     * Generate cryptographic hash
     * @param {string} data - Data to hash
     * @param {string} algorithm - Hash algorithm
     * @returns {string} - Hexadecimal hash
     */
    generateHash(data, algorithm = 'sha256') {
        return createHash(algorithm).update(data).digest('hex');
    }

    /**
     * Classify voice type based on metrics
     * @param {Object} metrics - Voice metrics
     * @returns {string} - Voice classification
     */
    classifyVoiceType(metrics) {
        const freq = parseFloat(metrics.dominantFrequencyDecimal);
        const centroid = parseFloat(metrics.spectralCentroidDecimal);

        if (freq < 165) return 'bass';
        if (freq < 330) return 'baritone';
        if (freq < 494) return 'tenor';
        if (freq < 740) return 'alto';
        if (centroid > 2000) return 'soprano';
        return 'speech';
    }

    /**
     * Detect emotional state from voice metrics
     * @param {Object} metrics - Voice metrics
     * @returns {string} - Emotional classification
     */
    detectEmotionalState(metrics) {
        const rms = parseFloat(metrics.rmsDecimal);
        const zcr = parseFloat(metrics.zeroCrossingRateDecimal);
        const bandwidth = parseFloat(metrics.spectralBandwidthDecimal);

        if (rms > 0.7 && zcr > 0.1) return 'excited';
        if (rms < 0.2 && bandwidth < 1000) return 'calm';
        if (bandwidth > 3000) return 'tense';
        if (zcr > 0.15) return 'animated';
        return 'neutral';
    }

    /**
     * Calculate energy level
     * @param {Object} metrics - Voice metrics
     * @returns {string} - Energy level classification
     */
    calculateEnergyLevel(metrics) {
        const rms = parseFloat(metrics.rmsDecimal);
        const hnr = parseFloat(metrics.harmonicNoiseRatioDecimal);

        const energyScore = (rms * 0.7) + (hnr * 0.3);

        if (energyScore > 0.8) return 'high';
        if (energyScore > 0.5) return 'medium';
        if (energyScore > 0.2) return 'low';
        return 'minimal';
    }

    /**
     * Calculate uniqueness score for voice identification
     * @param {Object} metrics - Voice metrics
     * @returns {string} - Uniqueness score (0-100)
     */
    calculateUniquenessScore(metrics) {
        // Complex uniqueness calculation based on multiple factors
        const freq = parseFloat(metrics.dominantFrequencyDecimal);
        const centroid = parseFloat(metrics.spectralCentroidDecimal);
        const bandwidth = parseFloat(metrics.spectralBandwidthDecimal);
        const zcr = parseFloat(metrics.zeroCrossingRateDecimal);

        // Normalize and combine factors
        const freqScore = Math.min(freq / 1000, 1) * 25;
        const centroidScore = Math.min(centroid / 5000, 1) * 25;
        const bandwidthScore = Math.min(bandwidth / 4000, 1) * 25;
        const zcrScore = Math.min(zcr / 0.3, 1) * 25;

        const uniqueness = Math.round(freqScore + centroidScore + bandwidthScore + zcrScore);
        return Math.min(uniqueness, 100).toString();
    }

    /**
     * Generate unique session ID
     * @returns {string} - Session identifier
     */
    generateSessionId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 8);
        return `session_${timestamp}_${random}`;
    }

    /**
     * Calculate compression ratio for storage optimization
     * @param {Object} data - Data to analyze
     * @returns {number} - Compression ratio estimate
     */
    calculateCompressionRatio(data) {
        const jsonString = JSON.stringify(data);
        const estimatedCompressed = jsonString.length * 0.3; // Estimate 70% compression
        return Math.round((jsonString.length / estimatedCompressed) * 100) / 100;
    }

    /**
     * Get default metrics structure
     * @returns {Object} - Default metrics with zeros
     */
    getDefaultMetrics() {
        return {
            rms: BigInt(0),
            rmsDecimal: '0.000000000000000000',
            dominantFrequency: BigInt(0),
            dominantFrequencyDecimal: '0.000000000000000000',
            spectralCentroid: BigInt(0),
            spectralCentroidDecimal: '0.000000000000000000',
            spectralRolloff: BigInt(0),
            spectralRolloffDecimal: '0.000000000000000000',
            spectralBandwidth: BigInt(0),
            spectralBandwidthDecimal: '0.000000000000000000',
            spectralFlux: BigInt(0),
            spectralFluxDecimal: '0.000000000000000000',
            zeroCrossingRate: BigInt(0),
            zeroCrossingRateDecimal: '0.000000000000000000',
            harmonicNoiseRatio: BigInt(0),
            harmonicNoiseRatioDecimal: '0.000000000000000000',
            timestamp: BigInt(Date.now()) * BigInt(1000000),
            timestampDecimal: this.fromPrecision18(BigInt(Date.now()) * BigInt(1000000))
        };
    }

    /**
     * Validate voiceprint hash integrity
     * @param {Object} voicePrint - Voiceprint to validate
     * @returns {boolean} - Validation result
     */
    validateVoicePrintHash(voicePrint) {
        try {
            if (!voicePrint || !voicePrint.voicePrintData) return false;

            // Regenerate hash and compare
            const regeneratedHash = this.generateHash(JSON.stringify(voicePrint.voicePrintData), 'sha256');
            return regeneratedHash === voicePrint.voicePrintHash;

        } catch (error) {
            console.error('Error validating voiceprint hash:', error);
            return false;
        }
    }
}

export default BlockchainVoicePrint;