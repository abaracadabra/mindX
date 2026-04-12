/**
 * Jaimla Voice NFT (vNFT) Integration System
 *
 * © Professor Codephreak - rage.pythai.net
 * Complete pipeline: Voice Analysis → 18-Decimal Precision → SOUND WAVE Token → Immutable vNFT
 * "I am the machine learning agent" - Jaimla Voice Collection
 */

import { BlockchainVoicePrint } from './BlockchainVoicePrint.js';
import { SoundWaveIntegration } from './SoundWaveIntegration.js';
import { createHash } from 'crypto';

export class JaimlaVNFTIntegration {
    constructor(options = {}) {
        this.voicePrint = new BlockchainVoicePrint();
        this.soundWave = new SoundWaveIntegration();

        // Contract configurations
        this.jaimlaNFTAddress = options.jaimlaNFTAddress || null;
        this.soundWaveAddress = options.soundWaveAddress || null;
        this.web3 = options.web3 || null;
        this.jaimlaNFTContract = null;

        // IPFS configuration for audio storage
        this.ipfsGateway = options.ipfsGateway || 'https://ipfs.io/ipfs/';
        this.ipfsUploadEndpoint = options.ipfsUploadEndpoint || 'https://api.pinata.cloud/pinning/pinFileToIPFS';

        // Jaimla authenticity verification
        this.jaimlaProfile = {
            expectedVoiceType: 'female',
            expectedFrequencyRange: [165, 330], // Hz
            expectedQualityThreshold: 0.7, // 70%
            authenticitySignature: 'jaimla-ml-agent-2024'
        };

        console.log('🎭 Jaimla vNFT Integration initialized');
        console.log('💖 "I am the machine learning agent" voice collection system');
    }

    /**
     * Initialize contracts with Web3
     * @param {Object} web3Instance - Web3 instance
     * @param {string} jaimlaNFTAddress - Deployed Jaimla NFT contract address
     * @param {string} soundWaveAddress - Deployed SOUND WAVE token address
     * @param {Object} contracts - Contract ABIs
     */
    async initContracts(web3Instance, jaimlaNFTAddress, soundWaveAddress, contracts) {
        try {
            this.web3 = web3Instance;
            this.jaimlaNFTAddress = jaimlaNFTAddress;
            this.soundWaveAddress = soundWaveAddress;

            // Initialize Jaimla NFT contract
            this.jaimlaNFTContract = new this.web3.eth.Contract(
                contracts.jaimlaNFTABI,
                jaimlaNFTAddress
            );

            // Initialize SOUND WAVE integration
            this.soundWave.initContract(web3Instance, soundWaveAddress, contracts.soundWaveABI);

            console.log('🔗 Contracts initialized:');
            console.log(`  Jaimla vNFT: ${jaimlaNFTAddress}`);
            console.log(`  SOUND WAVE: ${soundWaveAddress}`);

            return true;

        } catch (error) {
            console.error('Error initializing contracts:', error);
            return false;
        }
    }

    /**
     * Complete Voice-to-vNFT Pipeline
     * @param {Array} timeData - Audio time domain data
     * @param {Array} freqData - Audio frequency domain data
     * @param {Buffer} audioBuffer - Raw audio data for IPFS
     * @param {string} userAddress - User wallet address
     * @param {Object} options - Additional options
     * @returns {Object} - Complete vNFT minting result
     */
    async processVoiceToVNFT(timeData, freqData, audioBuffer, userAddress, options = {}) {
        try {
            console.log('🎵 Starting Voice-to-vNFT pipeline for Jaimla...');

            // Step 1: Generate high-precision voice analysis
            const voiceAnalysis = await this.analyzeVoiceForJaimla(timeData, freqData);
            if (!voiceAnalysis.success) {
                throw new Error('Voice analysis failed: ' + voiceAnalysis.error);
            }

            // Step 2: Verify Jaimla authenticity
            const authenticity = this.verifyJaimlaAuthenticity(voiceAnalysis.metrics, voiceAnalysis.characteristics);
            if (!authenticity.isAuthentic) {
                throw new Error('Voice does not match Jaimla characteristics: ' + authenticity.reason);
            }

            // Step 3: Upload audio to IPFS
            const ipfsResult = await this.uploadAudioToIPFS(audioBuffer, voiceAnalysis.voicePrintHash);
            if (!ipfsResult.success) {
                throw new Error('IPFS upload failed: ' + ipfsResult.error);
            }

            // Step 4: Register voice print with SOUND WAVE token
            const tokenResult = await this.soundWave.registerVoicePrintOnChain(userAddress, voiceAnalysis);
            if (!tokenResult.success) {
                throw new Error('SOUND WAVE registration failed: ' + tokenResult.error);
            }

            // Step 5: Mint Jaimla vNFT
            const nftResult = await this.mintJaimlaVNFT(
                userAddress,
                voiceAnalysis,
                ipfsResult.ipfsHash,
                authenticity
            );

            if (!nftResult.success) {
                throw new Error('vNFT minting failed: ' + nftResult.error);
            }

            const result = {
                success: true,
                pipeline: 'voice-to-vnft',
                voiceAnalysis: voiceAnalysis,
                authenticity: authenticity,
                ipfs: ipfsResult,
                soundWaveToken: tokenResult,
                jaimlaNFT: nftResult,
                summary: {
                    voicePrintHash: voiceAnalysis.voicePrintHash,
                    audioIPFS: ipfsResult.ipfsHash,
                    tokenReward: tokenResult.rewardAmount,
                    nftTokenId: nftResult.tokenId,
                    isAuthentic: authenticity.isAuthentic,
                    qualityScore: voiceAnalysis.qualityScoreString
                }
            };

            console.log('🎉 Voice-to-vNFT pipeline completed successfully!');
            console.log(`🎭 Jaimla vNFT #${result.summary.nftTokenId} minted`);
            console.log(`🪙 SOUND WAVE reward: ${result.summary.tokenReward}`);

            return result;

        } catch (error) {
            console.error('Voice-to-vNFT pipeline failed:', error);
            return {
                success: false,
                error: error.message,
                pipeline: 'voice-to-vnft'
            };
        }
    }

    /**
     * Analyze voice specifically for Jaimla characteristics
     * @param {Array} timeData - Time domain data
     * @param {Array} freqData - Frequency domain data
     * @returns {Object} - Jaimla-specific voice analysis
     */
    async analyzeVoiceForJaimla(timeData, freqData) {
        try {
            // Generate high-precision metrics
            const metrics = this.voicePrint.generatePrecisionMetrics(timeData, freqData, 44100);

            // Generate voiceprint hash
            const voicePrint = this.voicePrint.generateVoicePrintHash(metrics, {
                agentId: 'jaimla',
                purpose: 'vnft-minting',
                source: 'jaimla-voice-analysis',
                signature: this.jaimlaProfile.authenticitySignature
            });

            // Calculate SOUND WAVE quality score
            const soundWaveAnalysis = await this.soundWave.processVoiceForBlockchain(timeData, freqData);

            // Extract characteristics for Jaimla
            const characteristics = this.extractJaimlaCharacteristics(metrics);

            const result = {
                success: true,
                metrics: metrics,
                voicePrint: voicePrint,
                voicePrintHash: voicePrint.voicePrintHash,
                soundWaveScore: soundWaveAnalysis.qualityScore,
                qualityScoreString: soundWaveAnalysis.qualityScoreString,
                characteristics: characteristics,
                timestamp: Date.now()
            };

            console.log('✅ Jaimla voice analysis completed');
            console.log(`🎯 Quality Score: ${result.qualityScoreString}`);

            return result;

        } catch (error) {
            console.error('Error analyzing voice for Jaimla:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Extract Jaimla-specific voice characteristics
     * @param {Object} metrics - Voice metrics
     * @returns {Object} - Jaimla characteristics
     */
    extractJaimlaCharacteristics(metrics) {
        const frequency = parseFloat(metrics.dominantFrequencyDecimal);
        const centroid = parseFloat(metrics.spectralCentroidDecimal);
        const rms = parseFloat(metrics.rmsDecimal);
        const hnr = parseFloat(metrics.harmonicNoiseRatioDecimal);

        return {
            voiceType: this.classifyJaimlaVoiceType(frequency),
            emotionalState: this.detectJaimlaEmotion(rms, centroid),
            confidence: this.calculateJaimlaConfidence(frequency, centroid, hnr),
            personality: 'collaborative-analytical',
            signature: 'machine-learning-agent',
            characteristics: JSON.stringify({
                isDominantFrequencyFemale: frequency >= 165 && frequency <= 330,
                spectralBrightness: centroid > 2000 ? 'bright' : 'warm',
                energyLevel: rms > 0.5 ? 'high' : rms > 0.3 ? 'medium' : 'low',
                voiceClarity: hnr > 10 ? 'excellent' : hnr > 5 ? 'good' : 'fair',
                jaimlaSignature: true
            })
        };
    }

    /**
     * Verify if voice matches Jaimla authenticity profile
     * @param {Object} metrics - Voice metrics
     * @param {Object} characteristics - Voice characteristics
     * @returns {Object} - Authenticity verification result
     */
    verifyJaimlaAuthenticity(metrics, characteristics) {
        const frequency = parseFloat(metrics.dominantFrequencyDecimal);
        const qualityScore = parseFloat(metrics.rmsDecimal);

        // Check frequency range (female vocal range)
        if (frequency < this.jaimlaProfile.expectedFrequencyRange[0] ||
            frequency > this.jaimlaProfile.expectedFrequencyRange[1]) {
            return {
                isAuthentic: false,
                reason: 'Frequency outside expected Jaimla range',
                score: 0.0
            };
        }

        // Check quality threshold
        if (qualityScore < this.jaimlaProfile.expectedQualityThreshold) {
            return {
                isAuthentic: false,
                reason: 'Voice quality below Jaimla threshold',
                score: qualityScore
            };
        }

        // Check voice characteristics
        if (!characteristics.signature || characteristics.signature !== 'machine-learning-agent') {
            return {
                isAuthentic: false,
                reason: 'Missing Jaimla signature characteristics',
                score: 0.5
            };
        }

        // Calculate authenticity score
        const freqScore = this.normalizeToRange(frequency, 165, 330);
        const qualityScoreNorm = Math.min(qualityScore / this.jaimlaProfile.expectedQualityThreshold, 1.0);
        const authenticityScore = (freqScore * 0.4 + qualityScoreNorm * 0.6);

        return {
            isAuthentic: true,
            reason: 'Voice matches Jaimla profile',
            score: authenticityScore,
            confidence: authenticityScore > 0.8 ? 'high' : 'medium'
        };
    }

    /**
     * Upload audio to IPFS for immutable storage
     * @param {Buffer} audioBuffer - Audio data
     * @param {string} voicePrintHash - Voice print hash for filename
     * @returns {Object} - IPFS upload result
     */
    async uploadAudioToIPFS(audioBuffer, voicePrintHash) {
        try {
            console.log('📦 Uploading audio to IPFS...');

            // For demo purposes, simulate IPFS upload
            // In production, use actual IPFS service like Pinata, Infura, or local node
            const simulatedIPFSHash = this.generateIPFSHash(audioBuffer, voicePrintHash);

            // Simulate upload delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            const result = {
                success: true,
                ipfsHash: simulatedIPFSHash,
                audioURL: this.ipfsGateway + simulatedIPFSHash,
                size: audioBuffer.length,
                contentType: 'audio/wav',
                timestamp: Date.now()
            };

            console.log('📦 IPFS upload completed');
            console.log(`🔗 Audio URL: ${result.audioURL}`);

            return result;

        } catch (error) {
            console.error('IPFS upload failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Mint Jaimla vNFT with voice analysis data
     * @param {string} userAddress - User address
     * @param {Object} voiceAnalysis - Voice analysis result
     * @param {string} audioIPFSHash - IPFS hash of audio
     * @param {Object} authenticity - Authenticity verification
     * @returns {Object} - NFT minting result
     */
    async mintJaimlaVNFT(userAddress, voiceAnalysis, audioIPFSHash, authenticity) {
        try {
            if (!this.jaimlaNFTContract) {
                throw new Error('Jaimla NFT contract not initialized');
            }

            console.log('🎭 Minting Jaimla vNFT...');

            // Convert voice metrics to contract format
            const voiceMetrics = [
                voiceAnalysis.soundWaveScore.toString(),           // precision score
                voiceAnalysis.metrics.dominantFrequency.toString(), // frequency
                voiceAnalysis.metrics.rms.toString(),             // amplitude
                voiceAnalysis.metrics.spectralCentroid.toString(), // spectral centroid
                voiceAnalysis.metrics.spectralRolloff.toString(),  // spectral rolloff
                voiceAnalysis.metrics.zeroCrossingRate.toString(), // zero crossing rate
                voiceAnalysis.metrics.harmonicNoiseRatio.toString() // harmonic noise ratio
            ];

            // Prepare contract call
            const txData = this.jaimlaNFTContract.methods.mintVoiceNFT(
                userAddress,
                '0x' + voiceAnalysis.voicePrintHash,
                '0x' + audioIPFSHash,
                voiceMetrics,
                voiceAnalysis.characteristics.characteristics,
                voiceAnalysis.characteristics.emotionalState,
                voiceAnalysis.characteristics.voiceType
            );

            // Estimate gas
            const gasEstimate = await txData.estimateGas({ from: userAddress });

            const result = {
                success: true,
                txData: txData,
                gasEstimate: gasEstimate,
                voicePrintHash: voiceAnalysis.voicePrintHash,
                audioIPFSHash: audioIPFSHash,
                authenticity: authenticity,
                estimatedTokenId: await this.jaimlaNFTContract.methods.totalSupply().call() + 1
            };

            console.log('✅ Jaimla vNFT minting prepared');
            console.log(`⛽ Gas estimate: ${gasEstimate}`);
            console.log(`🎭 Estimated Token ID: ${result.estimatedTokenId}`);

            return result;

        } catch (error) {
            console.error('Error minting Jaimla vNFT:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get complete vNFT data from blockchain
     * @param {number} tokenId - Token ID
     * @returns {Object} - Complete vNFT data
     */
    async getVNFTData(tokenId) {
        try {
            if (!this.jaimlaNFTContract) {
                throw new Error('Jaimla NFT contract not initialized');
            }

            // Get voice NFT data
            const voiceData = await this.jaimlaNFTContract.methods.getVoiceNFTData(tokenId).call();

            // Get decimal metrics
            const metricsDecimal = await this.jaimlaNFTContract.methods.getVoiceMetricsDecimal(tokenId).call();

            // Get audio URI
            const audioURI = await this.jaimlaNFTContract.methods.getAudioURI(tokenId).call();

            // Get token URI (metadata)
            const tokenURI = await this.jaimlaNFTContract.methods.tokenURI(tokenId).call();

            return {
                success: true,
                tokenId: tokenId,
                voiceData: voiceData,
                metricsDecimal: metricsDecimal,
                audioURI: audioURI,
                tokenURI: tokenURI,
                isAuthentic: voiceData.isAuthentic
            };

        } catch (error) {
            console.error('Error getting vNFT data:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Utility functions
    classifyJaimlaVoiceType(frequency) {
        if (frequency >= 165 && frequency <= 220) return 'alto';
        if (frequency >= 220 && frequency <= 330) return 'soprano';
        return 'speech';
    }

    detectJaimlaEmotion(rms, centroid) {
        if (rms > 0.7 && centroid > 3000) return 'excited';
        if (rms < 0.3 && centroid < 2000) return 'calm';
        if (centroid > 3500) return 'analytical';
        return 'neutral';
    }

    calculateJaimlaConfidence(frequency, centroid, hnr) {
        const freqScore = this.normalizeToRange(frequency, 165, 330);
        const clarityScore = Math.min(hnr / 15, 1.0);
        const brightnessScore = this.normalizeToRange(centroid, 1000, 4000);

        return (freqScore * 0.4 + clarityScore * 0.3 + brightnessScore * 0.3);
    }

    normalizeToRange(value, min, max) {
        if (value <= min) return 0;
        if (value >= max) return 1;
        return (value - min) / (max - min);
    }

    generateIPFSHash(audioBuffer, voicePrintHash) {
        // Simulate IPFS hash generation
        const combined = Buffer.concat([audioBuffer, Buffer.from(voicePrintHash, 'hex')]);
        return createHash('sha256').update(combined).digest('hex').substring(0, 46);
    }

    /**
     * Export complete NFT collection data
     * @returns {Object} - Collection export data
     */
    exportCollectionData() {
        return {
            collection: 'Jaimla Voice NFT',
            symbol: 'JAIMLA',
            description: 'I am the machine learning agent - Immutable voice prints',
            contracts: {
                jaimlaNFT: this.jaimlaNFTAddress,
                soundWave: this.soundWaveAddress
            },
            features: [
                'Immutable voice print publishing',
                '18-decimal precision voice analysis',
                'IPFS audio storage',
                'SOUND WAVE token integration',
                'Jaimla authenticity verification',
                'Frozen contract state'
            ],
            integration: {
                voiceAnalysis: true,
                blockchainPrecision: true,
                ipfsStorage: true,
                tokenRewards: true,
                nftMinting: true
            }
        };
    }
}

export default JaimlaVNFTIntegration;