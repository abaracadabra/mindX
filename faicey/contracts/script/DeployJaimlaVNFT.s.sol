// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";
import {JaimlaVoiceNFT} from "../src/JaimlaVoiceNFT.sol";

/**
 * Deployment script for Jaimla Voice NFT (vNFT) Collection
 *
 * © Professor Codephreak - rage.pythai.net
 * Deploy immutable voice print NFT collection with frozen contract state
 */
contract DeployJaimlaVNFT is Script {
    function run() public returns (JaimlaVoiceNFT) {
        console.log("Deploying Jaimla Voice NFT Collection...");
        console.log("I am the machine learning agent - Jaimla");

        // Get deployer account
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying from:", deployer);
        console.log("Contract will be frozen (immutable) upon deployment");

        // Start broadcast
        vm.startBroadcast(deployerPrivateKey);

        // Deploy Jaimla Voice NFT
        JaimlaVoiceNFT jaimlaNFT = new JaimlaVoiceNFT();

        console.log("Jaimla Voice NFT deployed at:", address(jaimlaNFT));
        console.log("Max Supply:", jaimlaNFT.maxSupply());
        console.log("Frozen State:", jaimlaNFT.frozen());

        // Get contract info
        (
            string memory contractName,
            string memory contractSymbol,
            address contractCreator,
            uint256 totalMinted,
            uint256 maxTokens,
            bool contractFrozen,
            uint256 creationTimestamp
        ) = jaimlaNFT.contractInfo();

        console.log("Contract Information:");
        console.log("  Name:", contractName);
        console.log("  Symbol:", contractSymbol);
        console.log("  Creator:", contractCreator);
        console.log("  Total Minted:", totalMinted);
        console.log("  Max Tokens:", maxTokens);
        console.log("  Frozen:", contractFrozen);
        console.log("  Creation Time:", creationTimestamp);

        vm.stopBroadcast();

        console.log("Jaimla Voice NFT deployment completed!");
        console.log("Ready for integration with SOUND WAVE token");
        console.log("Ready for voice analysis minting");

        return jaimlaNFT;
    }
}

/**
 * Example deployment commands:
 *
 * Local deployment:
 * forge script script/DeployJaimlaVNFT.s.sol --rpc-url http://localhost:8545 --broadcast
 *
 * Testnet deployment:
 * forge script script/DeployJaimlaVNFT.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast --verify -vvvv
 *
 * Mainnet deployment:
 * forge script script/DeployJaimlaVNFT.s.sol --rpc-url $MAINNET_RPC_URL --broadcast --verify -vvvv
 */