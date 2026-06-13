// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {X402ChainRegistry} from "../src/X402ChainRegistry.sol";
import {X402EVMFacilitator} from "../src/X402EVMFacilitator.sol";

/// @notice Deploy the EVM x402 settlement layer: registry (Base + Arc USDC) + facilitator, and
///         allowlist the BANKON facilitator EOA. Admin/owner = bankon.eth (override via env).
contract DeployX402EVM is Script {
    // canonical USDC
    address constant USDC_BASE = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant USDC_ARC  = 0x3600000000000000000000000000000000000000;

    function run() external {
        address admin = vm.envOr("BANKON_OWNER", 0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169); // bankon.eth
        address facilitator = vm.envOr("BANKON_X402_FACILITATOR", admin);

        vm.startBroadcast();
        X402ChainRegistry reg = new X402ChainRegistry(admin);
        reg.setChain(8453, USDC_BASE);    // Base
        reg.setChain(5042002, USDC_ARC);  // Arc (Circle)
        X402EVMFacilitator fac = new X402EVMFacilitator(admin, reg);
        fac.setFacilitator(facilitator, true);
        vm.stopBroadcast();

        console2.log("X402ChainRegistry:", address(reg));
        console2.log("X402EVMFacilitator:", address(fac));
        console2.log("facilitator allowlisted:", facilitator);
    }
}
