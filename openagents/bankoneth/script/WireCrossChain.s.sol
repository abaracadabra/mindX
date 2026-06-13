// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

import {BankonInftAdapter}      from "../contracts/BankonInftAdapter.sol";
import {BankonX402Attestor}     from "../contracts/BankonX402Attestor.sol";
import {BankonAgenticPlaceHook} from "../contracts/BankonAgenticPlaceHook.sol";

/// @title  WireCrossChain
/// @notice Post-deploy admin transactions executed by the BANKON Treasury Safe
///         on the Ethereum side. Wires the cross-chain references that can
///         only be known after DeployEthereum + DeployZeroG have both run.
///
///         Env vars consumed:
///           - TREASURY_PK              Treasury Safe operator key (or simulated EOA)
///           - INFT_ADAPTER_ADDR        BankonInftAdapter address (from DeployEthereum)
///           - X402_ATTESTOR_ADDR       BankonX402Attestor address (from DeployEthereum)
///           - AGENTICPLACE_HOOK_ADDR   BankonAgenticPlaceHook address (from DeployEthereum)
///           - ZEROG_INFT_ADDR          iNFT_7857 contract on 0G (from DeployZeroG)
///           - ZEROG_CHAIN_ID           16601 (Galileo testnet) or 0G mainnet id
///           - ERC6551_IMPL_ADDR        ERC-6551 account implementation contract address
///           - X402_FACILITATOR_ADDR    GoPlausible (or self-hosted) facilitator EOA
///           - AGENTICPLACE_WEBHOOK_URL agenticplace.pythai.net indexer webhook URL
contract WireCrossChain is Script {
    function run() external {
        uint256 pk = vm.envUint("TREASURY_PK");

        address inftAdapter      = vm.envAddress("INFT_ADAPTER_ADDR");
        address x402Attestor     = vm.envAddress("X402_ATTESTOR_ADDR");
        address agenticPlaceHook = vm.envAddress("AGENTICPLACE_HOOK_ADDR");

        address zeroGiNFT        = vm.envAddress("ZEROG_INFT_ADDR");
        uint256 zeroGChainId     = vm.envUint("ZEROG_CHAIN_ID");
        address erc6551Impl      = vm.envAddress("ERC6551_IMPL_ADDR");
        address facilitator      = vm.envAddress("X402_FACILITATOR_ADDR");
        string  memory webhook   = vm.envString("AGENTICPLACE_WEBHOOK_URL");

        vm.startBroadcast(pk);

        // Cross-chain iNFT binding.
        BankonInftAdapter(inftAdapter).setZeroGiNFTContract(zeroGiNFT, zeroGChainId);
        BankonInftAdapter(inftAdapter).setErc6551Implementation(erc6551Impl);

        // x402 facilitator pubkey.
        BankonX402Attestor(x402Attestor).setFacilitator(facilitator, true);

        // AgenticPlace indexer webhook (off-chain delivery path).
        BankonAgenticPlaceHook(agenticPlaceHook).setWebhookURL(webhook);

        vm.stopBroadcast();

        console.log("WireCrossChain complete");
        console.log("  inftAdapter.zeroGiNFTContract =", zeroGiNFT);
        console.log("  inftAdapter.zeroGChainId      =", zeroGChainId);
        console.log("  inftAdapter.erc6551Impl       =", erc6551Impl);
        console.log("  x402Attestor.facilitator      =", facilitator);
        console.log("  agenticPlaceHook.webhook      =", webhook);
    }
}
