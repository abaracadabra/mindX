// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script, console2 } from "forge-std/Script.sol";

import { Deploy } from "./Deploy.s.sol";
import { MockERC20 } from "../../test/mocks/MockERC20.sol";

/// @title DeployTestnet
/// @notice Testnet-only bootstrap: first deploys a mock USDC if
///         `SETTLEMENT_TOKEN` is unset, then runs the full Deploy script.
contract DeployTestnet is Script {
    function run() external returns (Deploy.Addresses memory a) {
        address settlement = vm.envOr("SETTLEMENT_TOKEN", address(0));
        if (settlement == address(0)) {
            uint256 pk = vm.envUint("PRIVATE_KEY");
            vm.startBroadcast(pk);
            MockERC20 usdc = new MockERC20("Test USDC", "tUSDC", 6);
            usdc.mint(vm.envAddress("DEPLOYER_ADDRESS"), 10_000_000e6);
            vm.stopBroadcast();
            settlement = address(usdc);
            console2.log("Deployed mock USDC at", settlement);
            vm.setEnv("SETTLEMENT_TOKEN", vm.toString(settlement));
        }
        Deploy d = new Deploy();
        a = d.run();
    }
}
