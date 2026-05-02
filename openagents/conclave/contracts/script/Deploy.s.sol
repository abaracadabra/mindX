// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {Conclave} from "../src/Conclave.sol";
import {ConclaveBond} from "../src/ConclaveBond.sol";

/// @notice Two-step deployment: ConclaveBond's `conclave` immutable
///         points at Conclave; Conclave's `bond` immutable points at
///         ConclaveBond. We resolve the chicken-and-egg by deploying
///         Conclave with a CREATE2 prediction of the bond address, or
///         (simpler, what we do here) by deploying with a placeholder
///         and then swapping. For a real mainnet deploy, use the
///         CREATE2 path; this script is fine for testnets.
contract Deploy is Script {
    function run(
        address tessera,
        address censura,
        address algoBridge
    ) external returns (Conclave conclave, ConclaveBond bondCtr) {
        vm.startBroadcast();

        // Predict the bond address via nonce arithmetic, deploy Conclave
        // with that prediction, then deploy bond.
        address deployer = msg.sender;
        uint64 nonce = vm.getNonce(deployer);
        // Conclave will use nonce N, bondCtr will use nonce N+1.
        address predictedBond = computeCreateAddress(deployer, nonce + 1);

        conclave = new Conclave(tessera, censura, predictedBond);
        bondCtr  = new ConclaveBond(address(conclave), algoBridge);
        require(address(bondCtr) == predictedBond, "bond address mismatch");

        vm.stopBroadcast();
    }
}
