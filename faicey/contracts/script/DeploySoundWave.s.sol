// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";
import {SoundWaveToken} from "../src/SoundWaveToken.sol";

/**
 * DeploySoundWave — Foundry deploy script (preferred path; anvil for local).
 *
 * Local (anvil):
 *   anvil &
 *   forge script script/DeploySoundWave.s.sol \
 *     --rpc-url http://127.0.0.1:8545 --broadcast \
 *     --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
 *
 * The broadcast writes broadcast/DeploySoundWave.s.sol/<chainId>/run-latest.json,
 * from which `node script/export-abis.mjs` lifts the address into
 * dapp/deployments/<chainId>.json — the UI never hard-codes an address.
 */
contract DeploySoundWave is Script {
    function run() external returns (SoundWaveToken wav) {
        vm.startBroadcast();
        wav = new SoundWaveToken();
        console.log("SoundWaveToken (SND/WAV) deployed:", address(wav));
        console.log("MAX_SUPPLY (cap):", wav.MAX_SUPPLY());
        console.log("genesis totalSupply:", wav.totalSupply());
        vm.stopBroadcast();
    }
}
