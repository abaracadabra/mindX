// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {iNFT_7857}       from "../contracts/inft/iNFT_7857.sol";

/// @title  DeployZeroG
/// @notice Deploys the ERC-7857 iNFT contract on 0G Galileo (16601) or 0G
///         mainnet. The Ethereum-side BankonInftAdapter is wired to this
///         contract via the post-deploy WireCrossChain script.
///
///         Run:
///           FOUNDRY_PROFILE=zerog forge script script/DeployZeroG.s.sol \
///               --rpc-url $ZEROG_RPC --broadcast --sender $DEPLOYER
///
///         Env vars consumed:
///           - DEPLOYER_PK       private key of the deploy EOA
///           - TREASURY_ADDR     admin / minter wallet (BANKON Treasury Safe)
contract DeployZeroG is Script {
    function run() external returns (address inftAddr) {
        uint256 pk        = vm.envUint("DEPLOYER_PK");
        address treasury  = vm.envAddress("TREASURY_ADDR");

        vm.startBroadcast(pk);

        // iNFT_7857 constructor signature — see contracts/inft/iNFT_7857.sol.
        //   (name_, symbol_, admin, royaltyReceiver, royaltyFeeBps,
        //    oracle_, treasury_, cloneFeeWei_)
        // The treasury holds admin, royalty, oracle, and treasury roles at
        // bootstrap; the 0G-side minter role is granted to the bridge worker
        // via a follow-up admin tx after WireCrossChain.
        inftAddr = address(new iNFT_7857(
            "Bankon Agent NFT",
            "BAGENT",
            treasury,                  // admin
            treasury,                  // royaltyReceiver
            500,                       // 5.00% default royalty
            treasury,                  // oracle bootstrap
            treasury,                  // treasury for clone-fee receipts
            0                          // cloneFeeWei — disabled at launch
        ));

        vm.stopBroadcast();

        console.log("iNFT_7857 (0G) deployed:", inftAddr);
        console.log("Chain id:", block.chainid);
        console.log("Next step: run script/WireCrossChain.s.sol on Ethereum");
    }
}
