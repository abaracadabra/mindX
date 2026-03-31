/**
 * SOUND WAVE Token Deployment Script
 *
 * © Professor Codephreak - rage.pythai.net
 * Deploy maximum supply token with 18-decimal precision and voice analysis integration
 */

const { ethers } = require("hardhat");

async function main() {
    console.log("🌊 Deploying SOUND WAVE Token...");
    console.log("⚡ Maximum Supply: 2^256 - 1 with 18-decimal precision");
    console.log("🔗 Voice Analysis Integration: Enabled");

    // Get deployment account
    const [deployer] = await ethers.getSigners();
    console.log("🚀 Deploying from account:", deployer.address);

    // Check balance
    const balance = await deployer.getBalance();
    console.log("💰 Account balance:", ethers.utils.formatEther(balance), "ETH");

    if (balance.lt(ethers.utils.parseEther("0.01"))) {
        console.warn("⚠️ Low balance - ensure sufficient ETH for deployment");
    }

    // Deploy the contract
    const SoundWaveToken = await ethers.getContractFactory("SoundWaveToken");

    console.log("🔄 Deploying contract...");
    const soundWave = await SoundWaveToken.deploy();

    console.log("⏳ Waiting for deployment confirmation...");
    await soundWave.deployed();

    console.log("✅ SOUND WAVE Token deployed successfully!");
    console.log("📍 Contract address:", soundWave.address);
    console.log("🔗 Transaction hash:", soundWave.deployTransaction.hash);

    // Verify deployment
    console.log("\n📊 Verifying deployment...");

    try {
        // Get contract info
        const contractInfo = await soundWave.getContractInfo();
        const maxSupplyInfo = await soundWave.getMaximumSupplyInfo();

        console.log("\n🎯 Contract Information:");
        console.log("  Token Name:", contractInfo.tokenName);
        console.log("  Token Symbol:", contractInfo.tokenSymbol);
        console.log("  Decimals:", contractInfo.tokenDecimals.toString());
        console.log("  Total Supply:", contractInfo.currentTotalSupply.toString());
        console.log("  Voice Analysis:", contractInfo.voiceEnabled ? "Enabled" : "Disabled");

        console.log("\n💎 Maximum Supply Information:");
        console.log("  Max Supply:", maxSupplyInfo.maxSupply.toString());
        console.log("  Max Supply String:", maxSupplyInfo.maxSupplyString);
        console.log("  Description:", maxSupplyInfo.description);

        // Get deployer balance in tokens
        const deployerBalance = await soundWave.balanceOf(deployer.address);
        console.log("\n🪙 Deployer Token Balance:");
        console.log("  Balance:", deployerBalance.toString());
        console.log("  Percentage of Supply: 100% (Maximum Supply)");

        // Test precision functions
        console.log("\n🔢 Testing 18-Decimal Precision Functions:");

        const testValue = ethers.utils.parseEther("123.456789123456789123");
        const precision18 = await soundWave.toPrecision18(123);
        const fromPrecision = await soundWave.fromPrecision18(precision18);

        console.log("  Test Value (123):", precision18.toString());
        console.log("  From Precision:", fromPrecision.toString());

        // Test percentage calculation
        const percentage = await soundWave.calculatePrecisePercentage(1, 4);
        console.log("  25% with 18-decimal precision:", percentage.toString());

        // Test market cap calculation
        const pricePerToken = ethers.utils.parseEther("1"); // $1 per token
        const marketCap = await soundWave.calculateMarketCap(pricePerToken);
        console.log("  Market cap at $1/token:", marketCap.toString());

    } catch (error) {
        console.error("❌ Error verifying deployment:", error);
    }

    // Generate deployment summary
    const deploymentSummary = {
        network: (await ethers.provider.getNetwork()).name,
        contractAddress: soundWave.address,
        deployerAddress: deployer.address,
        transactionHash: soundWave.deployTransaction.hash,
        blockNumber: soundWave.deployTransaction.blockNumber,
        deploymentTime: new Date().toISOString(),

        tokenInfo: {
            name: "SOUND WAVE",
            symbol: "WAVE",
            decimals: 18,
            maxSupply: "115792089237316195423570985008687907853269984665640564039457584007913129639935",
            voiceAnalysisEnabled: true
        },

        features: [
            "Maximum possible supply (2^256 - 1)",
            "18-decimal precision mathematics",
            "Voice analysis integration",
            "Blockchain voiceprint registration",
            "NFT-compatible metadata",
            "Cross-chain compatibility",
            "Precision reward calculations"
        ],

        integrations: {
            faicey: true,
            voiceAnalysis: true,
            nftReady: true,
            crossChain: ["Ethereum", "Polygon", "BSC", "Arbitrum", "Algorand"]
        }
    };

    // Save deployment info
    const fs = require('fs');
    const deploymentPath = './deployment-soundwave.json';

    fs.writeFileSync(deploymentPath, JSON.stringify(deploymentSummary, null, 2));
    console.log(`\n💾 Deployment summary saved to ${deploymentPath}`);

    // Generate integration code
    const integrationCode = `
// SOUND WAVE Token Integration Code
// Contract Address: ${soundWave.address}

import { SoundWaveIntegration } from '../src/blockchain/SoundWaveIntegration.js';
import Web3 from 'web3';

// Initialize Web3 connection
const web3 = new Web3('YOUR_RPC_ENDPOINT');

// Initialize SOUND WAVE integration
const soundWave = new SoundWaveIntegration();

// Connect to deployed contract
const contractABI = [ /* Your contract ABI */ ];
soundWave.initContract(web3, '${soundWave.address}', contractABI);

// Process voice for blockchain integration
async function processVoiceForSoundWave(timeData, freqData) {
    const result = await soundWave.processVoiceForBlockchain(timeData, freqData);
    console.log('Voice Quality Score:', result.qualityScoreString);
    console.log('Token Reward:', result.rewardAmountString);
    return result;
}

// Register voice print on blockchain
async function registerVoice(userAddress, voiceAnalysis) {
    const tx = await soundWave.registerVoicePrintOnChain(userAddress, voiceAnalysis);
    console.log('Transaction prepared:', tx.success);
    return tx;
}
`;

    fs.writeFileSync('./integration-example.js', integrationCode);
    console.log("📝 Integration example saved to integration-example.js");

    console.log("\n🎉 SOUND WAVE Token deployment complete!");
    console.log("🌊 Maximum tokenomics with voice analysis integration ready");
    console.log("🔗 Contract can now be used with Faicey voice analysis system");

    return {
        contract: soundWave,
        address: soundWave.address,
        summary: deploymentSummary
    };
}

// Handle deployment
if (require.main === module) {
    main()
        .then(() => process.exit(0))
        .catch((error) => {
            console.error("💥 Deployment failed:", error);
            process.exit(1);
        });
}

module.exports = main;