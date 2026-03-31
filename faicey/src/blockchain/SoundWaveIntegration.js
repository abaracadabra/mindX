/**
 * SOUND WAVE Token Integration with Faicey Voice Analysis
 *
 * © Professor Codephreak - rage.pythai.net
 * Connects 18-decimal precision voice analysis with maximum supply token contract
 */

import { BlockchainVoicePrint } from './BlockchainVoicePrint.js';
import { createHash } from 'crypto';

export class SoundWaveIntegration {
    constructor(options = {}) {
        this.voicePrint = new BlockchainVoicePrint();
        this.contractAddress = options.contractAddress || null;
        this.web3 = options.web3 || null;
        this.contract = null;

        // Maximum token economics
        this.MAX_SUPPLY = BigInt('115792089237316195423570985008687907853269984665640564039457584007913129639935'); // 2^256 - 1
        this.PRECISION_MULTIPLIER = BigInt('1000000000000000000'); // 10^18
        this.VOICE_REWARD_POOL = this.MAX_SUPPLY / BigInt('1000000'); // 0.0001% of max supply for voice rewards

        console.log('🌊 SOUND WAVE Integration initialized with maximum tokenomics');
        console.log(`📊 Max Supply: ${this.MAX_SUPPLY.toString()}`);
        console.log(`⚡ Precision: 18 decimals (${this.PRECISION_MULTIPLIER.toString()})`);
    }

    /**
     * Initialize Web3 contract connection
     * @param {Object} web3Instance - Web3 instance
     * @param {string} contractAddress - Deployed contract address
     * @param {Object} contractABI - Contract ABI
     */
    initContract(web3Instance, contractAddress, contractABI) {
        this.web3 = web3Instance;
        this.contractAddress = contractAddress;
        this.contract = new this.web3.eth.Contract(contractABI, contractAddress);

        console.log(`🔗 Connected to SOUND WAVE contract: ${contractAddress}`);
    }

    /**
     * Process voice analysis and calculate precision score for blockchain
     * @param {Array} timeData - Audio time domain data
     * @param {Array} freqData - Audio frequency domain data
     * @param {number} sampleRate - Sample rate
     * @returns {Object} - Blockchain-ready voice analysis
     */
    async processVoiceForBlockchain(timeData, freqData, sampleRate = 44100) {
        try {
            console.log('🎵 Processing voice for SOUND WAVE blockchain integration...');

            // Generate high-precision voice metrics
            const metrics = this.voicePrint.generatePrecisionMetrics(timeData, freqData, sampleRate);

            // Calculate overall voice quality score (0-10^18 scale)
            const qualityScore = this.calculateVoiceQualityScore(metrics);

            // Generate voiceprint hash for blockchain registration
            const voicePrint = this.voicePrint.generateVoicePrintHash(metrics, {
                agentId: 'sound-wave-jaimla',
                purpose: 'token-integration',
                precision: 18
            });

            // Calculate token reward based on voice quality
            const rewardAmount = this.calculateTokenReward(qualityScore);

            const result = {
                voicePrintHash: voicePrint.voicePrintHash,
                voicePrintShortHash: voicePrint.voicePrintShortHash,
                qualityScore: qualityScore,
                qualityScoreString: this.bigIntToDecimal18(qualityScore),
                rewardAmount: rewardAmount,
                rewardAmountString: this.bigIntToDecimal18(rewardAmount),
                metrics: metrics,
                voicePrint: voicePrint,
                blockchainReady: true
            };

            console.log(`🎯 Voice quality score: ${result.qualityScoreString}`);
            console.log(`🪙 Calculated reward: ${result.rewardAmountString} WAVE`);

            return result;

        } catch (error) {
            console.error('Error processing voice for blockchain:', error);
            return null;
        }
    }

    /**
     * Calculate voice quality score with 18-decimal precision
     * @param {Object} metrics - Voice analysis metrics
     * @returns {BigInt} - Quality score (0 to 10^18)
     */
    calculateVoiceQualityScore(metrics) {
        try {
            // Extract key metrics
            const rms = parseFloat(metrics.rmsDecimal);
            const frequency = parseFloat(metrics.dominantFrequencyDecimal);
            const centroid = parseFloat(metrics.spectralCentroidDecimal);
            const rolloff = parseFloat(metrics.spectralRolloffDecimal);
            const bandwidth = parseFloat(metrics.spectralBandwidthDecimal);
            const hnr = parseFloat(metrics.harmonicNoiseRatioDecimal);

            // Weighted quality calculation
            let qualityScore = 0;

            // RMS contribution (20%) - optimal range 0.3-0.8
            const rmsScore = this.normalizeToRange(rms, 0.1, 1.0) * 0.2;

            // Frequency contribution (15%) - optimal vocal range 85-1000 Hz
            const freqScore = this.normalizeToRange(frequency, 50, 2000) * 0.15;

            // Spectral centroid contribution (20%) - brightness measure
            const centroidScore = this.normalizeToRange(centroid, 500, 8000) * 0.2;

            // Spectral rolloff contribution (15%) - energy distribution
            const rolloffScore = this.normalizeToRange(rolloff, 1000, 15000) * 0.15;

            // Bandwidth contribution (15%) - spectral width
            const bandwidthScore = this.normalizeToRange(bandwidth, 1000, 6000) * 0.15;

            // Harmonic-to-noise ratio contribution (15%) - voice clarity
            const hnrScore = this.normalizeToRange(hnr, 1, 20) * 0.15;

            qualityScore = rmsScore + freqScore + centroidScore + rolloffScore + bandwidthScore + hnrScore;

            // Ensure score is between 0 and 1, then scale to 18-decimal precision
            qualityScore = Math.max(0, Math.min(1, qualityScore));

            // Convert to 18-decimal BigInt
            const precision18 = BigInt(Math.floor(qualityScore * Number(this.PRECISION_MULTIPLIER)));

            return precision18;

        } catch (error) {
            console.error('Error calculating voice quality score:', error);
            return BigInt(0);
        }
    }

    /**
     * Normalize value to 0-1 range based on optimal range
     * @param {number} value - Input value
     * @param {number} min - Minimum optimal value
     * @param {number} max - Maximum optimal value
     * @returns {number} - Normalized score (0-1)
     */
    normalizeToRange(value, min, max) {
        if (value <= min) return 0;
        if (value >= max) return 1;
        return (value - min) / (max - min);
    }

    /**
     * Calculate token reward based on voice quality score
     * @param {BigInt} qualityScore - Voice quality score (0 to 10^18)
     * @returns {BigInt} - Token reward amount with 18-decimal precision
     */
    calculateTokenReward(qualityScore) {
        // Base reward: 1 WAVE token for perfect quality (10^18)
        const baseReward = this.PRECISION_MULTIPLIER; // 1 token with 18 decimals

        // Calculate proportional reward
        const reward = (qualityScore * baseReward) / this.PRECISION_MULTIPLIER;

        // Add bonus for high quality (>90%)
        if (qualityScore > (this.PRECISION_MULTIPLIER * BigInt(90)) / BigInt(100)) {
            const bonus = reward / BigInt(10); // 10% bonus
            return reward + bonus;
        }

        return reward;
    }

    /**
     * Register voice print on blockchain
     * @param {string} userAddress - User wallet address
     * @param {Object} voiceAnalysis - Voice analysis result
     * @returns {Object} - Transaction result
     */
    async registerVoicePrintOnChain(userAddress, voiceAnalysis) {
        try {
            if (!this.contract) {
                throw new Error('Contract not initialized');
            }

            console.log(`🔗 Registering voice print on blockchain for ${userAddress}...`);

            // Convert hash to bytes32 format
            const voicePrintBytes32 = '0x' + voiceAnalysis.voicePrintHash;

            // Prepare transaction
            const txData = this.contract.methods.registerVoicePrint(
                voicePrintBytes32,
                voiceAnalysis.qualityScore.toString()
            );

            // Estimate gas
            const gasEstimate = await txData.estimateGas({ from: userAddress });

            console.log(`⛽ Estimated gas: ${gasEstimate}`);
            console.log(`🎯 Quality score: ${voiceAnalysis.qualityScoreString}`);
            console.log(`🪙 Expected reward: ${voiceAnalysis.rewardAmountString} WAVE`);

            return {
                success: true,
                txData: txData,
                gasEstimate: gasEstimate,
                voicePrintHash: voiceAnalysis.voicePrintHash,
                qualityScore: voiceAnalysis.qualityScoreString,
                rewardAmount: voiceAnalysis.rewardAmountString
            };

        } catch (error) {
            console.error('Error registering voice print on chain:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Bulk register multiple voice prints
     * @param {string} userAddress - User wallet address
     * @param {Array} voiceAnalyses - Array of voice analysis results
     * @returns {Object} - Transaction result
     */
    async bulkRegisterVoicePrints(userAddress, voiceAnalyses) {
        try {
            if (!this.contract || voiceAnalyses.length === 0) {
                throw new Error('Contract not initialized or no voice analyses provided');
            }

            console.log(`🔗 Bulk registering ${voiceAnalyses.length} voice prints...`);

            // Convert to contract format
            const hashes = voiceAnalyses.map(va => '0x' + va.voicePrintHash);
            const scores = voiceAnalyses.map(va => va.qualityScore.toString());

            // Prepare transaction
            const txData = this.contract.methods.bulkRegisterVoicePrints(hashes, scores);

            // Calculate total expected rewards
            const totalReward = voiceAnalyses.reduce(
                (sum, va) => sum + va.rewardAmount,
                BigInt(0)
            );

            const result = {
                success: true,
                txData: txData,
                voicePrintCount: voiceAnalyses.length,
                totalReward: this.bigIntToDecimal18(totalReward),
                voicePrints: voiceAnalyses.map(va => ({
                    hash: va.voicePrintShortHash,
                    quality: va.qualityScoreString,
                    reward: va.rewardAmountString
                }))
            };

            console.log(`📊 Total expected reward: ${result.totalReward} WAVE`);

            return result;

        } catch (error) {
            console.error('Error bulk registering voice prints:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get user's voice analysis data from blockchain
     * @param {string} userAddress - User wallet address
     * @returns {Object} - Voice analysis data
     */
    async getUserVoiceData(userAddress) {
        try {
            if (!this.contract) {
                throw new Error('Contract not initialized');
            }

            const result = await this.contract.methods.getVoiceAnalysisData(userAddress).call();

            return {
                voicePrintHash: result.voicePrintHash,
                analysisTimestamp: result.analysisTimestamp,
                precisionScore: result.precisionScore,
                precisionDecimal: result.precisionDecimal,
                hasVoicePrint: result.voicePrintHash !== '0x0000000000000000000000000000000000000000000000000000000000000000'
            };

        } catch (error) {
            console.error('Error getting user voice data:', error);
            return null;
        }
    }

    /**
     * Calculate market metrics for SOUND WAVE token
     * @param {BigInt} pricePerToken - Price per token (18-decimal precision)
     * @returns {Object} - Market metrics
     */
    calculateMarketMetrics(pricePerToken) {
        try {
            // Market cap = Total Supply × Price
            const marketCap = (this.MAX_SUPPLY * pricePerToken) / this.PRECISION_MULTIPLIER;

            // Theoretical values at different price points
            const metrics = {
                maxSupply: this.bigIntToDecimal18(this.MAX_SUPPLY),
                pricePerToken: this.bigIntToDecimal18(pricePerToken),
                marketCap: this.bigIntToDecimal18(marketCap),

                // Theoretical scenarios
                scenarios: {
                    oneDollar: {
                        price: '1.000000000000000000',
                        marketCap: this.bigIntToDecimal18(this.MAX_SUPPLY)
                    },
                    bitcoin: {
                        price: '50000.000000000000000000',
                        marketCap: this.bigIntToDecimal18(this.MAX_SUPPLY * BigInt(50000))
                    }
                },

                // Mathematical limits
                limits: {
                    maxUint256: this.MAX_SUPPLY.toString(),
                    maxDecimal18: this.bigIntToDecimal18(this.MAX_SUPPLY),
                    precisionMultiplier: this.PRECISION_MULTIPLIER.toString()
                }
            };

            return metrics;

        } catch (error) {
            console.error('Error calculating market metrics:', error);
            return null;
        }
    }

    /**
     * Convert BigInt to 18-decimal string representation
     * @param {BigInt} value - BigInt value
     * @returns {string} - Decimal string with 18 places
     */
    bigIntToDecimal18(value) {
        const divisor = this.PRECISION_MULTIPLIER;
        const quotient = value / divisor;
        const remainder = value % divisor;

        // Format with exactly 18 decimal places
        const remainderStr = remainder.toString().padStart(18, '0');
        return `${quotient}.${remainderStr}`;
    }

    /**
     * Convert decimal string to BigInt with 18-decimal precision
     * @param {string} decimalStr - Decimal string
     * @returns {BigInt} - BigInt representation
     */
    decimal18ToBigInt(decimalStr) {
        const parts = decimalStr.split('.');
        const wholePart = parts[0] || '0';
        const fractionalPart = (parts[1] || '').padEnd(18, '0').substring(0, 18);

        const wholeAsBigInt = BigInt(wholePart) * this.PRECISION_MULTIPLIER;
        const fractionalAsBigInt = BigInt(fractionalPart);

        return wholeAsBigInt + fractionalAsBigInt;
    }

    /**
     * Export integration data for NFT/marketplace
     * @param {Object} voiceAnalysis - Voice analysis data
     * @returns {Object} - NFT-ready metadata
     */
    exportForNFT(voiceAnalysis) {
        return {
            name: `SOUND WAVE Voice Print ${voiceAnalysis.voicePrintShortHash}`,
            description: 'High-precision voice analysis with maximum token economics integration',
            image: `https://mindx.pythai.net/faicey/voice-prints/${voiceAnalysis.voicePrintShortHash}.png`,

            attributes: [
                { trait_type: 'Token Integration', value: 'SOUND WAVE (MAX SUPPLY)' },
                { trait_type: 'Voice Quality Score', value: voiceAnalysis.qualityScoreString },
                { trait_type: 'Token Reward', value: voiceAnalysis.rewardAmountString },
                { trait_type: 'Precision', value: '18 Decimal Places' },
                { trait_type: 'Max Supply', value: this.bigIntToDecimal18(this.MAX_SUPPLY) },
                { trait_type: 'Hash Algorithm', value: 'SHA-256' },
                { trait_type: 'Blockchain Compatible', value: 'Ethereum, Polygon, BSC, Arbitrum' }
            ],

            // Extended metadata for SOUND WAVE integration
            soundWaveMetadata: {
                contractAddress: this.contractAddress,
                voicePrintHash: voiceAnalysis.voicePrintHash,
                qualityScore18Decimal: voiceAnalysis.qualityScore.toString(),
                rewardAmount18Decimal: voiceAnalysis.rewardAmount.toString(),
                maxSupply: this.MAX_SUPPLY.toString(),
                precisionMultiplier: this.PRECISION_MULTIPLIER.toString(),
                integrationVersion: '1.0.0',
                faiceyCompatible: true
            }
        };
    }
}

export default SoundWaveIntegration;