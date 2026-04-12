/**
 * SOUND WAVE Token Contract Deployer
 *
 * © Professor Codephreak - rage.pythai.net
 * Multi-chain contract deployment system with real bytecode integration
 */

import Web3 from 'web3';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

// Import compiled contract artifacts from Foundry
const SoundWaveArtifact = require('../contracts/out/SoundWaveToken.sol/SoundWaveToken.json');

export class ContractDeployer {
    constructor() {
        this.web3 = null;
        this.deployerAccount = null;
        this.gasPrice = null;
        this.gasLimit = 5000000; // Default gas limit

        // Chain configurations
        this.chainConfigs = {
            ethereum: {
                name: "Ethereum Mainnet",
                chainId: 1,
                rpcUrl: "https://mainnet.infura.io/v3/YOUR_INFURA_KEY",
                nativeToken: "ETH",
                explorer: "https://etherscan.io",
                gasMultiplier: 1.2
            },
            polygon: {
                name: "Polygon",
                chainId: 137,
                rpcUrl: "https://polygon-rpc.com",
                nativeToken: "MATIC",
                explorer: "https://polygonscan.com",
                gasMultiplier: 1.5
            },
            arbitrum: {
                name: "Arbitrum One",
                chainId: 42161,
                rpcUrl: "https://arb1.arbitrum.io/rpc",
                nativeToken: "ETH",
                explorer: "https://arbiscan.io",
                gasMultiplier: 1.1
            },
            optimism: {
                name: "Optimism",
                chainId: 10,
                rpcUrl: "https://mainnet.optimism.io",
                nativeToken: "ETH",
                explorer: "https://optimistic.etherscan.io",
                gasMultiplier: 1.1
            },
            base: {
                name: "Base",
                chainId: 8453,
                rpcUrl: "https://mainnet.base.org",
                nativeToken: "ETH",
                explorer: "https://basescan.org",
                gasMultiplier: 1.1
            },
            bsc: {
                name: "Binance Smart Chain",
                chainId: 56,
                rpcUrl: "https://bsc-dataseed1.binance.org",
                nativeToken: "BNB",
                explorer: "https://bscscan.com",
                gasMultiplier: 1.3
            },
            avalanche: {
                name: "Avalanche",
                chainId: 43114,
                rpcUrl: "https://api.avax.network/ext/bc/C/rpc",
                nativeToken: "AVAX",
                explorer: "https://snowtrace.io",
                gasMultiplier: 1.2
            },
            fantom: {
                name: "Fantom",
                chainId: 250,
                rpcUrl: "https://rpc.ftm.tools",
                nativeToken: "FTM",
                explorer: "https://ftmscan.com",
                gasMultiplier: 1.3
            },
            cronos: {
                name: "Cronos",
                chainId: 25,
                rpcUrl: "https://evm.cronos.org",
                nativeToken: "CRO",
                explorer: "https://cronoscan.com",
                gasMultiplier: 1.4
            },
            // Testnets
            sepolia: {
                name: "Sepolia Testnet",
                chainId: 11155111,
                rpcUrl: "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
                nativeToken: "ETH",
                explorer: "https://sepolia.etherscan.io",
                gasMultiplier: 1.0
            },
            goerli: {
                name: "Goerli Testnet",
                chainId: 5,
                rpcUrl: "https://goerli.infura.io/v3/YOUR_INFURA_KEY",
                nativeToken: "ETH",
                explorer: "https://goerli.etherscan.io",
                gasMultiplier: 1.0
            },
            mumbai: {
                name: "Mumbai Testnet",
                chainId: 80001,
                rpcUrl: "https://rpc-mumbai.maticvigil.com",
                nativeToken: "MATIC",
                explorer: "https://mumbai.polygonscan.com",
                gasMultiplier: 1.0
            }
        };

        console.log('🌊 SOUND WAVE Contract Deployer initialized');
        console.log('🔗 Multi-chain EVM deployment system ready');
    }

    /**
     * Initialize Web3 connection for specific chain
     * @param {string} chainKey - Chain identifier
     * @param {string} privateKey - Deployer private key (optional)
     */
    async initializeChain(chainKey, privateKey = null) {
        try {
            const chainConfig = this.chainConfigs[chainKey];
            if (!chainConfig) {
                throw new Error(`Unsupported chain: ${chainKey}`);
            }

            console.log(`🔗 Connecting to ${chainConfig.name}...`);

            // Initialize Web3
            this.web3 = new Web3(chainConfig.rpcUrl);

            // Set deployer account
            if (privateKey) {
                const account = this.web3.eth.accounts.privateKeyToAccount(privateKey);
                this.web3.eth.accounts.wallet.add(account);
                this.deployerAccount = account.address;
                console.log(`🔑 Deployer account: ${this.deployerAccount}`);
            }

            // Get current gas price
            this.gasPrice = await this.web3.eth.getGasPrice();
            console.log(`⛽ Current gas price: ${this.web3.utils.fromWei(this.gasPrice, 'gwei')} gwei`);

            return {
                success: true,
                chainConfig: chainConfig,
                gasPrice: this.gasPrice,
                deployerAccount: this.deployerAccount
            };

        } catch (error) {
            console.error('Chain initialization failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Estimate gas for SOUND WAVE contract deployment
     * @param {string} chainKey - Target chain
     * @returns {Object} - Gas estimation result
     */
    async estimateDeploymentGas(chainKey) {
        try {
            if (!this.web3) {
                throw new Error('Web3 not initialized');
            }

            const chainConfig = this.chainConfigs[chainKey];
            const contract = new this.web3.eth.Contract(SoundWaveArtifact.abi);

            // Estimate gas for deployment
            const deployTx = contract.deploy({
                data: SoundWaveArtifact.bytecode.object
            });

            const estimatedGas = await deployTx.estimateGas({
                from: this.deployerAccount
            });

            // Apply chain-specific gas multiplier
            const adjustedGas = Math.ceil(estimatedGas * chainConfig.gasMultiplier);
            const totalCost = this.web3.utils.toBN(adjustedGas).mul(this.web3.utils.toBN(this.gasPrice));

            return {
                success: true,
                estimatedGas: estimatedGas,
                adjustedGas: adjustedGas,
                gasPrice: this.gasPrice,
                gasPriceGwei: this.web3.utils.fromWei(this.gasPrice, 'gwei'),
                totalCost: totalCost.toString(),
                totalCostEth: this.web3.utils.fromWei(totalCost, 'ether'),
                chainName: chainConfig.name,
                nativeToken: chainConfig.nativeToken
            };

        } catch (error) {
            console.error('Gas estimation failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Deploy SOUND WAVE token contract
     * @param {string} chainKey - Target chain
     * @param {Object} options - Deployment options
     * @returns {Object} - Deployment result
     */
    async deployContract(chainKey, options = {}) {
        try {
            if (!this.web3 || !this.deployerAccount) {
                throw new Error('Web3 or deployer account not initialized');
            }

            const chainConfig = this.chainConfigs[chainKey];
            console.log(`🚀 Deploying SOUND WAVE token on ${chainConfig.name}...`);

            // Create contract instance
            const contract = new this.web3.eth.Contract(SoundWaveArtifact.abi);

            // Prepare deployment transaction
            const deployTx = contract.deploy({
                data: SoundWaveArtifact.bytecode.object
            });

            // Get gas estimation
            const gasEstimate = await deployTx.estimateGas({
                from: this.deployerAccount
            });

            const gasLimit = options.gasLimit || Math.ceil(gasEstimate * chainConfig.gasMultiplier);
            const gasPrice = options.gasPrice || this.gasPrice;

            console.log(`⛽ Gas limit: ${gasLimit.toLocaleString()}`);
            console.log(`💰 Gas price: ${this.web3.utils.fromWei(gasPrice, 'gwei')} gwei`);

            // Deploy the contract
            const deploymentResult = await deployTx.send({
                from: this.deployerAccount,
                gas: gasLimit,
                gasPrice: gasPrice
            });

            const contractAddress = deploymentResult.options.address;
            const transactionHash = deploymentResult.transactionHash;
            const blockNumber = deploymentResult.blockNumber;

            console.log(`✅ Contract deployed successfully!`);
            console.log(`📍 Address: ${contractAddress}`);
            console.log(`🔗 Transaction: ${transactionHash}`);

            // Verify contract deployment
            const verificationResult = await this.verifyDeployment(contractAddress);

            const result = {
                success: true,
                contractAddress: contractAddress,
                transactionHash: transactionHash,
                blockNumber: blockNumber,
                gasUsed: deploymentResult.gasUsed,
                gasPrice: gasPrice,
                totalCost: this.web3.utils.toBN(deploymentResult.gasUsed).mul(this.web3.utils.toBN(gasPrice)).toString(),
                chainName: chainConfig.name,
                chainId: chainConfig.chainId,
                explorerUrl: `${chainConfig.explorer}/address/${contractAddress}`,
                verification: verificationResult,
                tokenInfo: {
                    name: "SOUND WAVE",
                    symbol: "WAVE",
                    decimals: 18,
                    maxSupply: "115792089237316195423570985008687907853269984665640564039457584007913129639935"
                }
            };

            return result;

        } catch (error) {
            console.error('Contract deployment failed:', error);
            return {
                success: false,
                error: error.message,
                chainName: this.chainConfigs[chainKey]?.name
            };
        }
    }

    /**
     * Verify contract deployment by calling basic functions
     * @param {string} contractAddress - Deployed contract address
     * @returns {Object} - Verification result
     */
    async verifyDeployment(contractAddress) {
        try {
            console.log('🔍 Verifying contract deployment...');

            const contract = new this.web3.eth.Contract(SoundWaveArtifact.abi, contractAddress);

            // Test basic contract functions
            const name = await contract.methods.name().call();
            const symbol = await contract.methods.symbol().call();
            const decimals = await contract.methods.decimals().call();
            const totalSupply = await contract.methods.totalSupply().call();

            console.log('✅ Contract verification successful');
            console.log(`📋 Token: ${name} (${symbol})`);
            console.log(`🔢 Decimals: ${decimals}`);
            console.log(`💎 Total Supply: ${totalSupply}`);

            return {
                success: true,
                name: name,
                symbol: symbol,
                decimals: decimals,
                totalSupply: totalSupply,
                isMaxSupply: totalSupply === "115792089237316195423570985008687907853269984665640564039457584007913129639935"
            };

        } catch (error) {
            console.error('Contract verification failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get account balance on specific chain
     * @param {string} address - Account address
     * @param {string} chainKey - Chain identifier
     * @returns {Object} - Balance information
     */
    async getAccountBalance(address, chainKey) {
        try {
            if (!this.web3) {
                await this.initializeChain(chainKey);
            }

            const balance = await this.web3.eth.getBalance(address);
            const balanceEth = this.web3.utils.fromWei(balance, 'ether');
            const chainConfig = this.chainConfigs[chainKey];

            return {
                success: true,
                balance: balance,
                balanceFormatted: parseFloat(balanceEth).toFixed(6),
                nativeToken: chainConfig.nativeToken,
                chainName: chainConfig.name
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Generate contract interaction code for deployed contract
     * @param {string} contractAddress - Contract address
     * @param {string} chainKey - Chain identifier
     * @returns {string} - JavaScript code for contract interaction
     */
    generateInteractionCode(contractAddress, chainKey) {
        const chainConfig = this.chainConfigs[chainKey];

        return `
// SOUND WAVE Token Contract Interaction Code
// Deployed on ${chainConfig.name} at ${contractAddress}

import Web3 from 'web3';

// Initialize Web3 connection
const web3 = new Web3('${chainConfig.rpcUrl}');

// Contract ABI (subset)
const contractABI = ${JSON.stringify(SoundWaveArtifact.abi, null, 2)};

// Create contract instance
const soundWaveContract = new web3.eth.Contract(contractABI, '${contractAddress}');

// Example usage:

// Get token information
async function getTokenInfo() {
    const name = await soundWaveContract.methods.name().call();
    const symbol = await soundWaveContract.methods.symbol().call();
    const totalSupply = await soundWaveContract.methods.totalSupply().call();

    console.log('Token Info:', { name, symbol, totalSupply });
}

// Register voice print (requires wallet connection)
async function registerVoicePrint(account, voicePrintHash, precisionScore) {
    const tx = await soundWaveContract.methods.registerVoicePrint(
        voicePrintHash,
        precisionScore
    ).send({ from: account });

    console.log('Voice print registered:', tx.transactionHash);
}

// Get voice analysis data
async function getVoiceData(account) {
    const result = await soundWaveContract.methods.getVoiceAnalysisData(account).call();
    console.log('Voice data:', result);
}

// Check balance
async function getBalance(account) {
    const balance = await soundWaveContract.methods.balanceOf(account).call();
    const balanceFormatted = web3.utils.fromWei(balance, 'ether');
    console.log('Balance:', balanceFormatted, 'WAVE');
}

// Export for use
export { soundWaveContract, getTokenInfo, registerVoicePrint, getVoiceData, getBalance };
`;
    }

    /**
     * Batch deploy to multiple chains
     * @param {Array} chainKeys - List of chain identifiers
     * @param {string} privateKey - Deployer private key
     * @param {Object} options - Deployment options
     * @returns {Object} - Batch deployment results
     */
    async batchDeploy(chainKeys, privateKey, options = {}) {
        const results = {};
        const deploymentSummary = {
            successful: [],
            failed: [],
            totalGasUsed: 0,
            totalCostEth: 0
        };

        console.log(`🌊 Starting batch deployment to ${chainKeys.length} chains...`);

        for (const chainKey of chainKeys) {
            try {
                console.log(`\n🔄 Deploying to ${this.chainConfigs[chainKey].name}...`);

                // Initialize chain
                const initResult = await this.initializeChain(chainKey, privateKey);
                if (!initResult.success) {
                    throw new Error(initResult.error);
                }

                // Deploy contract
                const deployResult = await this.deployContract(chainKey, options);

                if (deployResult.success) {
                    results[chainKey] = deployResult;
                    deploymentSummary.successful.push({
                        chain: chainKey,
                        address: deployResult.contractAddress,
                        txHash: deployResult.transactionHash
                    });

                    deploymentSummary.totalGasUsed += deployResult.gasUsed;
                    deploymentSummary.totalCostEth += parseFloat(
                        this.web3.utils.fromWei(deployResult.totalCost, 'ether')
                    );
                } else {
                    throw new Error(deployResult.error);
                }

                // Wait between deployments to avoid rate limits
                if (options.delayBetweenDeployments) {
                    await this.sleep(options.delayBetweenDeployments);
                }

            } catch (error) {
                console.error(`❌ Deployment to ${chainKey} failed:`, error.message);
                results[chainKey] = {
                    success: false,
                    error: error.message,
                    chainName: this.chainConfigs[chainKey].name
                };

                deploymentSummary.failed.push({
                    chain: chainKey,
                    error: error.message
                });
            }
        }

        console.log('\n🎉 Batch deployment completed!');
        console.log(`✅ Successful: ${deploymentSummary.successful.length}`);
        console.log(`❌ Failed: ${deploymentSummary.failed.length}`);
        console.log(`⛽ Total gas used: ${deploymentSummary.totalGasUsed.toLocaleString()}`);
        console.log(`💰 Total cost: ${deploymentSummary.totalCostEth.toFixed(6)} ETH`);

        return {
            results: results,
            summary: deploymentSummary
        };
    }

    /**
     * Get supported chains list
     * @returns {Array} - List of supported chains
     */
    getSupportedChains() {
        return Object.keys(this.chainConfigs).map(key => ({
            key: key,
            name: this.chainConfigs[key].name,
            chainId: this.chainConfigs[key].chainId,
            nativeToken: this.chainConfigs[key].nativeToken,
            explorer: this.chainConfigs[key].explorer,
            isTestnet: ['sepolia', 'goerli', 'mumbai'].includes(key)
        }));
    }

    // Utility function
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

export default ContractDeployer;