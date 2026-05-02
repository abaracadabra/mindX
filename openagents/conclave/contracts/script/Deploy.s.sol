// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {Conclave} from "../src/Conclave.sol";
import {ConclaveBond} from "../src/ConclaveBond.sol";
import {Tessera} from "../src/Tessera.sol";
import {Censura} from "../src/Censura.sol";

/// @notice Full Conclave stack deployment.
///
///         run(tessera, censura, algoBridge) — for chains with BONAFIDE
///         already deployed. Pass the pre-deployed addresses.
///
///         runFresh(algoBridge) — deploys minimal Tessera + Censura
///         (admin = msg.sender) plus the Conclave + ConclaveBond pair.
///         Use this for Anvil and 0G Galileo where BONAFIDE is not yet
///         deployed.
contract Deploy is Script {
    function run(
        address tessera,
        address censura,
        address algoBridge
    ) external returns (Conclave conclave, ConclaveBond bondCtr) {
        vm.startBroadcast();
        address deployer = msg.sender;
        uint64 nonce = vm.getNonce(deployer);
        address predictedBond = computeCreateAddress(deployer, nonce + 1);
        conclave = new Conclave(tessera, censura, predictedBond);
        bondCtr  = new ConclaveBond(address(conclave), algoBridge);
        require(address(bondCtr) == predictedBond, "bond address mismatch");
        vm.stopBroadcast();
    }

    function runFresh(address algoBridge)
        external
        returns (
            Tessera tessera,
            Censura censura,
            Conclave conclave,
            ConclaveBond bondCtr
        )
    {
        vm.startBroadcast();
        address deployer = msg.sender;

        tessera = new Tessera(deployer);  // admin = deployer
        censura = new Censura(deployer);  // admin = deployer

        // ConclaveBond will be at deployer's nonce + 1 (after Conclave)
        uint64 nonce = vm.getNonce(deployer);
        address predictedBond = computeCreateAddress(deployer, nonce + 1);

        conclave = new Conclave(address(tessera), address(censura), predictedBond);
        bondCtr  = new ConclaveBond(address(conclave), algoBridge);
        require(address(bondCtr) == predictedBond, "bond address mismatch");

        vm.stopBroadcast();
    }
}
