// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {BubbleRoomV4} from "../src/BubbleRoomV4.sol";
import {DeltaGenesisSBT} from "../src/DeltaGenesisSBT.sol";
import {SeedRegistry} from "../src/SeedRegistry.sol";
import {DeltaVerseOrchestrator} from "../src/DeltaVerseOrchestrator.sol";
import {BubbleRoomSpawn} from "../src/BubbleRoomSpawn.sol";
import {EmergenceTraits} from "../src/EmergenceTraits.sol";
import {SwarmGovernance} from "../src/SwarmGovernance.sol";
import {TombRegistry} from "../src/TombRegistry.sol";

/**
 * @title  Deploy — the DeltaVerse NeuralNode room suite
 * @notice Deploys all 8 NeuralNode contracts in dependency order and writes a
 *         receipt whose keys EXACTLY match `data/config/blockchain_addresses.json`
 *         (the "137"/"1284" section). After a real run, copy the receipt addresses
 *         into that file to flip `agents/deltaverse/DeltaVerseGate` (`POST /gate`)
 *         from fail-closed to live — no Python change required.
 *
 *         Consumed by `agents/deployer` (FoundryDriver) via the `neuralnode.deploy`
 *         manifest, which reads `deployments/<chainId>/<RECEIPT_STAGE>.json`.
 */
contract Deploy is Script {
    function _envOr(string memory k, string memory d) internal view returns (string memory) {
        try vm.envString(k) returns (string memory v) { return v; } catch { return d; }
    }

    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        string memory stage = _envOr("RECEIPT_STAGE", "neuralnode");

        console2.log("=== Deploy NeuralNode suite ===");
        console2.log("chainid: ", block.chainid);
        console2.log("deployer:", vm.addr(pk));

        vm.startBroadcast(pk);
        BubbleRoomV4 room = new BubbleRoomV4();
        DeltaGenesisSBT sbt = new DeltaGenesisSBT();
        SeedRegistry seeds = new SeedRegistry();
        DeltaVerseOrchestrator orch = new DeltaVerseOrchestrator(address(room));
        BubbleRoomSpawn spawn = new BubbleRoomSpawn(address(room));
        EmergenceTraits traits = new EmergenceTraits(address(room), address(spawn));
        SwarmGovernance gov = new SwarmGovernance(address(room), address(traits));
        TombRegistry tomb = new TombRegistry(address(room), address(sbt), address(traits));
        vm.stopBroadcast();

        string memory o = "neuralnode";
        vm.serializeAddress(o, "bubbleRoomV4", address(room));
        vm.serializeAddress(o, "deltaGenesisSBT", address(sbt));
        vm.serializeAddress(o, "seedRegistry", address(seeds));
        vm.serializeAddress(o, "deltaVerseOrchestrator", address(orch));
        vm.serializeAddress(o, "bubbleRoomSpawn", address(spawn));
        vm.serializeAddress(o, "emergenceTraits", address(traits));
        vm.serializeAddress(o, "swarmGovernance", address(gov));
        string memory json = vm.serializeAddress(o, "tombRegistry", address(tomb));

        string memory dir = string.concat("deployments/", vm.toString(block.chainid));
        vm.createDir(dir, true);
        vm.writeJson(json, string.concat(dir, "/", stage, ".json"));

        console2.log("BubbleRoomV4 (room):   ", address(room));
        console2.log("BubbleRoomSpawn:       ", address(spawn));
    }
}
