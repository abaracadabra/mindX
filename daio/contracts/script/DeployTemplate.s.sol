// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {AgentRegistry} from "../agentregistry/AgentRegistry.sol";

/// @title  DeployTemplate
/// @notice A copyable, single-target deploy script for the mindX multi-chain
///         deployer (`agents/deployer`). Other projects fork this file and edit
///         the `new <Contract>(...)` leg + constructor env reads.
///
/// Required env (supplied by the deployer's FoundryDriver):
///   DEPLOYER_PRIVATE_KEY  — operator EOA for this run (vault-scoped key)
///   OWNER_MULTISIG        — owner of the deployed contract (default: deployer)
///   RECEIPT_STAGE         — receipt filename stem (default: "template")
///
/// Toggle:
///   DEPLOY_TARGET         — set to "0" to skip the deploy leg (default on)
///
/// Output: `deployments/<chainId>/<RECEIPT_STAGE>.json` with the deployed
///         address — read back by FoundryDriver.
contract DeployTemplate is Script {
    function _envOr(string memory key, string memory dflt) internal view returns (string memory) {
        try vm.envString(key) returns (string memory v) {
            return v;
        } catch {
            return dflt;
        }
    }

    function _flagOn(string memory key) internal view returns (bool) {
        return keccak256(bytes(_envOr(key, "1"))) != keccak256(bytes("0"));
    }

    function _envAddrOr(string memory key, address dflt) internal view returns (address) {
        try vm.envAddress(key) returns (address a) {
            return a == address(0) ? dflt : a;
        } catch {
            return dflt;
        }
    }

    function run() external {
        uint256 deployerPk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPk);
        address owner = _envAddrOr("OWNER_MULTISIG", deployer);
        string memory stage = _envOr("RECEIPT_STAGE", "template");

        console2.log("=== DeployTemplate ===");
        console2.log("chainid:  ", block.chainid);
        console2.log("deployer: ", deployer);
        console2.log("owner:    ", owner);

        address target;

        vm.startBroadcast(deployerPk);
        if (_flagOn("DEPLOY_TARGET")) {
            // ── EDIT THIS LEG for your project ───────────────────────────────
            AgentRegistry t = new AgentRegistry(
                _envOr("TARGET_NAME", "Template Agent Registry"),
                _envOr("TARGET_SYMBOL", "TAR"),
                owner
            );
            target = address(t);
            console2.log("target (AgentRegistry):", target);
            // ─────────────────────────────────────────────────────────────────
        }
        vm.stopBroadcast();

        _writeReceipt(stage, deployer, target);
    }

    function _writeReceipt(string memory stage, address deployer, address target) internal {
        string memory key = "deploytemplate";
        string memory body;
        body = vm.serializeUint(key, "chainId", block.chainid);
        body = vm.serializeUint(key, "blockNumber", block.number);
        body = vm.serializeAddress(key, "deployer", deployer);
        body = vm.serializeAddress(key, "target", target);

        string memory dir = string.concat("deployments/", vm.toString(block.chainid));
        string memory path = string.concat(dir, "/", stage, ".json");
        vm.writeJson(body, path);
        console2.log("receipt written         :", path);
    }
}
