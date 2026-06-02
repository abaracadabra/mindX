// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

/// @notice Subset of PublicResolver we call.
interface IPubResolver {
    function addr(bytes32 node) external view returns (address);
    function setAddr(bytes32 node, address a) external;
}

/// @notice Phase C.2 — operator-broadcast script that closes the forward-
///         record gap from `docs/CONTRACT_NAMING_AUDIT.md` (Gap #1).
///         After `SetPrimaryNames.s.sol` wires reverse records, this
///         script sets `PublicResolver.addr(namehash(name))` for each
///         registrar so resolvers like Etherscan + viem.getEnsName can
///         round-trip the primary back to the contract address.
///
///         Idempotent: skips any `(name, addr)` pair already wired
///         correctly. Reverts if the deployer wallet lacks
///         REGISTRAR_ROLE / authorisation on the PublicResolver.
///
///         Env vars (mirror SetPrimaryNames.s.sol):
///             DEPLOYER_PK
///             SUBNAME_REGISTRAR_ADDR  /  SUBNAME_REGISTRAR_NAME
///             ETH_REGISTRAR_ADDR      /  ETH_REGISTRAR_NAME
///             DOMAIN_HOSTING_ADDR     /  DOMAIN_HOSTING_NAME
///             OFFCHAIN_REGISTRAR_ADDR /  OFFCHAIN_REGISTRAR_NAME
///             PUBLIC_RESOLVER_ADDR    (default mainnet)
contract SetForwardNames is Script {
    address internal constant DEFAULT_RESOLVER =
        0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63;

    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PK");
        address resolver = vm.envOr("PUBLIC_RESOLVER_ADDR", DEFAULT_RESOLVER);

        vm.startBroadcast(pk);

        _maybeSetForward(resolver,
            vm.envOr("SUBNAME_REGISTRAR_ADDR",  address(0)),
            vm.envOr("SUBNAME_REGISTRAR_NAME",  string("registrar.bankon.eth")));
        _maybeSetForward(resolver,
            vm.envOr("ETH_REGISTRAR_ADDR",      address(0)),
            vm.envOr("ETH_REGISTRAR_NAME",      string("eth-registrar.bankon.eth")));
        _maybeSetForward(resolver,
            vm.envOr("DOMAIN_HOSTING_ADDR",     address(0)),
            vm.envOr("DOMAIN_HOSTING_NAME",     string("host.bankon.eth")));
        _maybeSetForward(resolver,
            vm.envOr("OFFCHAIN_REGISTRAR_ADDR", address(0)),
            vm.envOr("OFFCHAIN_REGISTRAR_NAME", string("offchain.bankon.eth")));

        vm.stopBroadcast();

        console.log("");
        console.log("Next: forge script script/VerifyContractNames.s.sol -vv");
    }

    function _maybeSetForward(address resolver, address target, string memory name) internal {
        console.log("");
        console.log("[", name, "]");
        if (target == address(0)) { console.log("  SKIP - addr env unset"); return; }

        bytes32 node = _namehash(name);
        address current;
        try IPubResolver(resolver).addr(node) returns (address a) { current = a; } catch {}

        if (current == target) {
            console.log("  OK - forward already wired to", target);
            return;
        }
        console.log("  setAddr -> target:", target);
        console.logBytes32(node);
        IPubResolver(resolver).setAddr(node, target);
    }

    function _namehash(string memory name) internal pure returns (bytes32 node) {
        bytes memory b = bytes(name);
        node = bytes32(0);
        uint256 len = b.length;
        if (len == 0) return node;

        uint256 end = len;
        while (end > 0) {
            uint256 start = end;
            while (start > 0 && b[start - 1] != ".") { start--; }
            bytes memory label = new bytes(end - start);
            for (uint256 i = 0; i < label.length; ++i) label[i] = b[start + i];
            bytes32 labelhash = keccak256(label);
            node = keccak256(abi.encodePacked(node, labelhash));
            end = start == 0 ? 0 : start - 1;
        }
    }
}
