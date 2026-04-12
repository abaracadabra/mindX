/**
 * Token Deployer Integration with Real Contract Deployment
 *
 * © Professor Codephreak - rage.pythai.net
 * Integrates the web interface with actual contract deployment capabilities
 */

// SOUND WAVE Token compiled contract data
const SOUND_WAVE_CONTRACT = {
    // This would be populated from the actual Foundry compilation
    bytecode: "0x608060405234801561001057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060018060146101000a81548160ff0219169083151502179055507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff600281905550600260003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff337fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef60405161013e919061019d565b60405180910390a3506101b8565b6000819050919050565b61016a8161015157565b82525050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b60006101978261016c565b9050919050565b6101a78161018c565b82525050565b6101b681610151565b82525050565b61321f806101c76000396000f3fe608060405234801561001057600080fd5b50600436106102f45760003560e01c806395d89b411161019a578063a9059cbb116100e1578063dd62ed3e1161008a578063f2fde38b11610064578063f2fde38b14610988578063f46eccc4146109a4578063f887ea40146109d4576102f4565b8063dd62ed3e14610910578063e58306f914610940578063f14210a61461095c576102f4565b8063b88d4fde116100bb578063b88d4fde14610888578063c87b56dd146108a4578063d547741f146108d4576102f4565b8063a9059cbb14610812578063b0e21e8014610842578063b77a147b14610872576102f4565b8063248a9ca311610143578063313ce5671161011d578063313ce5671461077e5780636352211e1461079c57806370a08231146107cc576102f4565b8063248a9ca3146107065780632f2ff15d146107365780632f745c5914610752576102f4565b8063095ea7b311610174578063095ea7b31461066257806318160ddd1461069257806323b872dd146106b0576102f4565b806395d89b411461062a57806398650275146106485780639abc832014610652576102f4565b8063313ce567116102675780634f6ccce7116102105780636352211e116101ea5780636352211e146105925780636817c76c146105c257806370a08231146105e0578063715018a614610610576102f4565b80634f6ccce714610512578063518302271461054257806355f804b314610560576102f4565b8063372f657c11610241578063372f657c146104a257806342842e0e146104d257806342966c68146104ee576102f4565b8063313ce5671461044a57806335c6aaf814610468578063372500ab14610486576102f4565b80630c57b4b7116102c95780631e7269c5116102a35780631e7269c5146103ba57806323b872dd146103ea5780632f745c5914610406576102f4565b80630c57b4b71461033857806318160ddd146103685780631c31f71014610386576102f4565b80630100823e146102f957806301ffc9a71461031757806306fdde0314610347578063081812fc14610365578063095ea7b314610395576102f4565b600080fd5b610301610a00565b60405161030e9190612a17565b60405180910390f35b610331600480360381019061032c9190612ad4565b610a26565b60405161033e9190612b1c565b60405180910390f35b61034f610a70565b60405161035c9190612bd0565b60405180910390f35b61036d610ab0565b60405161037a9190612c4a565b60405180910390f35b6103a0600480360381019061039b9190612c9b565b610ab6565b6040516103ad9190612cd7565b60405180910390f35b6103d460048036038101906103cf9190612c9b565b610ace565b6040516103e19190612c4a565b60405180910390f35b61040460048036038101906103ff9190612cf2565b610ae6565b005b61042060048036038101906104",

    abi: [
        {
            "inputs": [],
            "stateMutability": "nonpayable",
            "type": "constructor"
        },
        {
            "anonymous": false,
            "inputs": [
                {"indexed": true, "internalType": "address", "name": "owner", "type": "address"},
                {"indexed": true, "internalType": "address", "name": "spender", "type": "address"},
                {"indexed": false, "internalType": "uint256", "name": "value", "type": "uint256"}
            ],
            "name": "Approval",
            "type": "event"
        },
        {
            "anonymous": false,
            "inputs": [
                {"indexed": true, "internalType": "address", "name": "from", "type": "address"},
                {"indexed": true, "internalType": "address", "name": "to", "type": "address"},
                {"indexed": false, "internalType": "uint256", "name": "value", "type": "uint256"}
            ],
            "name": "Transfer",
            "type": "event"
        },
        {
            "anonymous": false,
            "inputs": [
                {"indexed": true, "internalType": "address", "name": "account", "type": "address"},
                {"indexed": true, "internalType": "bytes32", "name": "voicePrintHash", "type": "bytes32"},
                {"indexed": false, "internalType": "uint256", "name": "precisionScore", "type": "uint256"}
            ],
            "name": "VoicePrintRegistered",
            "type": "event"
        },
        {
            "inputs": [],
            "name": "MAX_SUPPLY",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "name",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "symbol",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "voicePrintHash", "type": "bytes32"},
                {"internalType": "uint256", "name": "precisionScore18Decimal", "type": "uint256"}
            ],
            "name": "registerVoicePrint",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
            "name": "getVoiceAnalysisData",
            "outputs": [
                {"internalType": "bytes32", "name": "voicePrintHash", "type": "bytes32"},
                {"internalType": "uint256", "name": "analysisTimestamp", "type": "uint256"},
                {"internalType": "uint256", "name": "precisionScore", "type": "uint256"},
                {"internalType": "string", "name": "precisionDecimal", "type": "string"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "getMaximumSupplyInfo",
            "outputs": [
                {"internalType": "uint256", "name": "maxSupply", "type": "uint256"},
                {"internalType": "uint256", "name": "maxSupplyWith18Decimals", "type": "uint256"},
                {"internalType": "string", "name": "maxSupplyString", "type": "string"},
                {"internalType": "string", "name": "description", "type": "string"}
            ],
            "stateMutability": "pure",
            "type": "function"
        },
        {
            "inputs": [{"internalType": "uint256", "name": "value", "type": "uint256"}],
            "name": "toPrecision18",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "pure",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"}
            ],
            "name": "mint",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
};

// Real mainnet RPC configurations
const MAINNET_RPCS = {
    ethereum: {
        name: "Ethereum Mainnet",
        chainId: "0x1",
        rpcUrl: "https://eth-mainnet.g.alchemy.com/v2/demo",
        nativeToken: "ETH",
        explorer: "https://etherscan.io",
        faucet: null
    },
    polygon: {
        name: "Polygon",
        chainId: "0x89",
        rpcUrl: "https://polygon-rpc.com/",
        nativeToken: "MATIC",
        explorer: "https://polygonscan.com",
        faucet: null
    },
    arbitrum: {
        name: "Arbitrum One",
        chainId: "0xa4b1",
        rpcUrl: "https://arb1.arbitrum.io/rpc",
        nativeToken: "ETH",
        explorer: "https://arbiscan.io",
        faucet: null
    },
    optimism: {
        name: "Optimism",
        chainId: "0xa",
        rpcUrl: "https://mainnet.optimism.io",
        nativeToken: "ETH",
        explorer: "https://optimistic.etherscan.io",
        faucet: null
    },
    base: {
        name: "Base",
        chainId: "0x2105",
        rpcUrl: "https://mainnet.base.org",
        nativeToken: "ETH",
        explorer: "https://basescan.org",
        faucet: null
    },
    bsc: {
        name: "BSC",
        chainId: "0x38",
        rpcUrl: "https://bsc-dataseed1.binance.org/",
        nativeToken: "BNB",
        explorer: "https://bscscan.com",
        faucet: null
    },
    avalanche: {
        name: "Avalanche",
        chainId: "0xa86a",
        rpcUrl: "https://api.avax.network/ext/bc/C/rpc",
        nativeToken: "AVAX",
        explorer: "https://snowtrace.io",
        faucet: null
    },
    // Testnets with faucets
    sepolia: {
        name: "Sepolia Testnet",
        chainId: "0xaa36a7",
        rpcUrl: "https://eth-sepolia.g.alchemy.com/v2/demo",
        nativeToken: "SepoliaETH",
        explorer: "https://sepolia.etherscan.io",
        faucet: "https://sepoliafaucet.com/"
    },
    mumbai: {
        name: "Mumbai Testnet",
        chainId: "0x13881",
        rpcUrl: "https://rpc-mumbai.maticvigil.com/",
        nativeToken: "MATIC",
        explorer: "https://mumbai.polygonscan.com",
        faucet: "https://faucet.polygon.technology/"
    }
};

class TokenDeployerIntegration {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.chainId = null;
        this.contract = null;
        this.deployedAddress = null;

        console.log('🌊 Token Deployer Integration initialized');
    }

    /**
     * Connect to wallet
     */
    async connectWallet() {
        try {
            if (typeof window.ethereum === 'undefined') {
                throw new Error('MetaMask not installed');
            }

            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            this.account = accounts[0];
            this.web3 = new Web3(window.ethereum);

            // Get chain ID
            this.chainId = await window.ethereum.request({ method: 'eth_chainId' });

            console.log('✅ Wallet connected:', this.account);
            console.log('🔗 Chain ID:', this.chainId);

            return {
                success: true,
                account: this.account,
                chainId: this.chainId
            };

        } catch (error) {
            console.error('❌ Wallet connection failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Switch to specific network
     */
    async switchNetwork(chainKey) {
        try {
            const networkConfig = MAINNET_RPCS[chainKey];
            if (!networkConfig) {
                throw new Error(`Network ${chainKey} not supported`);
            }

            // Try to switch to the network
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: networkConfig.chainId }]
                });
            } catch (switchError) {
                // If the network doesn't exist, add it
                if (switchError.code === 4902) {
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: networkConfig.chainId,
                            chainName: networkConfig.name,
                            rpcUrls: [networkConfig.rpcUrl],
                            blockExplorerUrls: [networkConfig.explorer],
                            nativeCurrency: {
                                name: networkConfig.nativeToken,
                                symbol: networkConfig.nativeToken,
                                decimals: 18
                            }
                        }]
                    });
                } else {
                    throw switchError;
                }
            }

            this.chainId = networkConfig.chainId;
            console.log(`✅ Switched to ${networkConfig.name}`);

            return {
                success: true,
                network: networkConfig
            };

        } catch (error) {
            console.error('❌ Network switch failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Deploy SOUND WAVE contract
     */
    async deployContract(chainKey) {
        try {
            if (!this.web3 || !this.account) {
                throw new Error('Wallet not connected');
            }

            console.log('🚀 Starting contract deployment...');

            // Create contract instance
            const contract = new this.web3.eth.Contract(SOUND_WAVE_CONTRACT.abi);

            // Prepare deployment transaction
            const deploy = contract.deploy({
                data: SOUND_WAVE_CONTRACT.bytecode
            });

            // Estimate gas
            const gasEstimate = await deploy.estimateGas({ from: this.account });
            const gasPrice = await this.web3.eth.getGasPrice();

            console.log(`⛽ Gas estimate: ${gasEstimate.toLocaleString()}`);
            console.log(`💰 Gas price: ${this.web3.utils.fromWei(gasPrice, 'gwei')} gwei`);

            // Deploy contract
            const deployedContract = await deploy.send({
                from: this.account,
                gas: Math.floor(gasEstimate * 1.2), // Add 20% buffer
                gasPrice: gasPrice
            });

            this.deployedAddress = deployedContract.options.address;
            this.contract = deployedContract;

            console.log(`✅ Contract deployed at: ${this.deployedAddress}`);

            // Verify deployment
            const verification = await this.verifyDeployment();

            return {
                success: true,
                contractAddress: this.deployedAddress,
                transactionHash: deployedContract.transactionHash,
                gasUsed: deployedContract.gasUsed || gasEstimate,
                verification: verification
            };

        } catch (error) {
            console.error('❌ Deployment failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Verify contract deployment
     */
    async verifyDeployment() {
        try {
            if (!this.contract) {
                throw new Error('No deployed contract');
            }

            // Test basic functions
            const name = await this.contract.methods.name().call();
            const symbol = await this.contract.methods.symbol().call();
            const decimals = await this.contract.methods.decimals().call();
            const totalSupply = await this.contract.methods.totalSupply().call();

            console.log('🔍 Contract verification:', {
                name, symbol, decimals, totalSupply
            });

            return {
                success: true,
                name, symbol, decimals, totalSupply,
                isMaxSupply: totalSupply === "115792089237316195423570985008687907853269984665640564039457584007913129639935"
            };

        } catch (error) {
            console.error('❌ Verification failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Mint tokens (if caller is owner)
     */
    async mintTokens(toAddress, amount) {
        try {
            if (!this.contract) {
                throw new Error('No deployed contract');
            }

            // Convert amount to wei (18 decimals)
            const amountWei = this.web3.utils.toWei(amount.toString(), 'ether');

            const tx = await this.contract.methods.mint(toAddress, amountWei).send({
                from: this.account
            });

            console.log(`✅ Minted ${amount} WAVE to ${toAddress}`);

            return {
                success: true,
                transactionHash: tx.transactionHash,
                amount: amount,
                recipient: toAddress
            };

        } catch (error) {
            console.error('❌ Minting failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Register voice print
     */
    async registerVoicePrint(voicePrintHash, precisionScore) {
        try {
            if (!this.contract) {
                throw new Error('No deployed contract');
            }

            // Convert precision score to 18 decimal format
            const precisionWei = this.web3.utils.toWei(precisionScore.toString(), 'ether');

            const tx = await this.contract.methods.registerVoicePrint(
                voicePrintHash,
                precisionWei
            ).send({
                from: this.account
            });

            console.log('✅ Voice print registered');

            return {
                success: true,
                transactionHash: tx.transactionHash,
                voicePrintHash: voicePrintHash,
                precisionScore: precisionScore
            };

        } catch (error) {
            console.error('❌ Voice print registration failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get account balance
     */
    async getBalance(address = null) {
        try {
            const account = address || this.account;
            if (!account) {
                throw new Error('No account specified');
            }

            let balance = '0';
            let tokenBalance = '0';

            // Get native token balance
            const nativeBalance = await this.web3.eth.getBalance(account);
            balance = this.web3.utils.fromWei(nativeBalance, 'ether');

            // Get SOUND WAVE token balance (if contract deployed)
            if (this.contract) {
                const tokenBal = await this.contract.methods.balanceOf(account).call();
                tokenBalance = this.web3.utils.fromWei(tokenBal, 'ether');
            }

            return {
                success: true,
                nativeBalance: parseFloat(balance).toFixed(6),
                tokenBalance: parseFloat(tokenBalance).toFixed(6)
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Add token to wallet
     */
    async addTokenToWallet() {
        try {
            if (!this.deployedAddress) {
                throw new Error('No deployed contract');
            }

            await window.ethereum.request({
                method: 'wallet_watchAsset',
                params: {
                    type: 'ERC20',
                    options: {
                        address: this.deployedAddress,
                        symbol: 'WAVE',
                        decimals: 18,
                        image: 'https://mindx.pythai.net/faicey/logo.png'
                    }
                }
            });

            return { success: true };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get network list
     */
    getNetworkList() {
        return Object.keys(MAINNET_RPCS).map(key => ({
            key: key,
            name: MAINNET_RPCS[key].name,
            chainId: MAINNET_RPCS[key].chainId,
            nativeToken: MAINNET_RPCS[key].nativeToken,
            explorer: MAINNET_RPCS[key].explorer,
            faucet: MAINNET_RPCS[key].faucet,
            isTestnet: !!MAINNET_RPCS[key].faucet
        }));
    }
}

// Make available globally
window.TokenDeployerIntegration = TokenDeployerIntegration;

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TokenDeployerIntegration, SOUND_WAVE_CONTRACT, MAINNET_RPCS };
}