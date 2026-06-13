// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

/// @notice Subset of the canonical ENS Registry we read.
interface IENSRegistry {
    function resolver(bytes32 node) external view returns (address);
}

/// @notice Subset of PublicResolver we read.
interface IRevResolver {
    function name(bytes32 node) external view returns (string memory);
    function addr(bytes32 node) external view returns (address);
}

/// @notice Phase C.1 — read-only audit of the four bankoneth registrar
///         contracts' primary-name configuration. Run after
///         `SetPrimaryNames.s.sol` (and optionally `SetForwardNames.s.sol`)
///         to confirm reverse + forward both resolve to the expected
///         pair.
///
///         Mirrors `verifyContractName()` from
///         packages/core/src/contract-naming.ts in pure Solidity so
///         operators can audit from the forge CLI without booting Node.
///
///         Env vars (all optional — unset rows are skipped):
///             SUBNAME_REGISTRAR_ADDR  /  SUBNAME_REGISTRAR_NAME
///             ETH_REGISTRAR_ADDR      /  ETH_REGISTRAR_NAME
///             DOMAIN_HOSTING_ADDR     /  DOMAIN_HOSTING_NAME
///             OFFCHAIN_REGISTRAR_ADDR /  OFFCHAIN_REGISTRAR_NAME
///             ENS_REGISTRY_ADDR       (default mainnet ENS registry)
///             PUBLIC_RESOLVER_ADDR    (default mainnet PublicResolver)
///
///         Defaults match `packages/core/src/addresses.ts` MAINNET pin.
///         Non-zero exit when any contract fails round-trip — Sepolia
///         rehearsal runbook + CI can gate on this.
contract VerifyContractNames is Script {
    // ENSIP-3 namehash("addr.reverse")
    bytes32 internal constant ADDR_REVERSE_NODE =
        0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2;

    address internal constant DEFAULT_REGISTRY =
        0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e;
    address internal constant DEFAULT_RESOLVER =
        0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63;

    function run() external {
        address registry = vm.envOr("ENS_REGISTRY_ADDR",   DEFAULT_REGISTRY);
        address fwdResolver = vm.envOr("PUBLIC_RESOLVER_ADDR", DEFAULT_RESOLVER);

        uint256 fail;
        fail += _auditOne("BankonSubnameRegistrar",
            vm.envOr("SUBNAME_REGISTRAR_ADDR",  address(0)),
            vm.envOr("SUBNAME_REGISTRAR_NAME",  string("registrar.bankon.eth")),
            registry, fwdResolver);
        fail += _auditOne("BankonEthRegistrar",
            vm.envOr("ETH_REGISTRAR_ADDR",      address(0)),
            vm.envOr("ETH_REGISTRAR_NAME",      string("eth-registrar.bankon.eth")),
            registry, fwdResolver);
        fail += _auditOne("BankonDomainHosting",
            vm.envOr("DOMAIN_HOSTING_ADDR",     address(0)),
            vm.envOr("DOMAIN_HOSTING_NAME",     string("host.bankon.eth")),
            registry, fwdResolver);
        fail += _auditOne("BankonOffchainRegistrar",
            vm.envOr("OFFCHAIN_REGISTRAR_ADDR", address(0)),
            vm.envOr("OFFCHAIN_REGISTRAR_NAME", string("offchain.bankon.eth")),
            registry, fwdResolver);

        if (fail > 0) {
            console.log("");
            console.log("=== FAILURE ===");
            console.log("Round-trip failed for", fail, "contract(s).");
            console.log("Run script/SetPrimaryNames.s.sol then script/SetForwardNames.s.sol");
            console.log("then re-run this verifier.");
            revert("contract-naming audit failed");
        }
    }

    function _auditOne(
        string memory label,
        address addr_,
        string memory expectedName,
        address registry,
        address fwdResolver
    ) internal view returns (uint256 failed) {
        console.log("");
        console.log("[", label, "]");
        if (addr_ == address(0)) {
            console.log("  SKIP - env var unset");
            return 0;
        }

        // Reverse leg.
        bytes32 reverseNode = _reverseNode(addr_);
        address reverseResolver = IENSRegistry(registry).resolver(reverseNode);
        string memory reverseName = "";
        if (reverseResolver != address(0)) {
            try IRevResolver(reverseResolver).name(reverseNode) returns (string memory n) {
                reverseName = n;
            } catch { /* leave empty */ }
        }

        // Forward leg.
        bytes32 forwardNode = _namehash(expectedName);
        address forwardAddr = address(0);
        try IRevResolver(fwdResolver).addr(forwardNode) returns (address a) {
            forwardAddr = a;
        } catch { /* leave zero */ }

        bool reverseOk = _eq(reverseName, expectedName);
        bool forwardOk = forwardAddr == addr_;

        console.log("  address    ", addr_);
        console.log("  expected   ", expectedName);
        console.log("  reverse    ", reverseName, reverseOk ? " OK" : " FAIL");
        console.log("  forward    ");
        console.log("            ", forwardAddr, forwardOk ? " OK" : " FAIL");
        console.log("  roundTrip  ", (reverseOk && forwardOk) ? "OK" : "FAIL");

        return (reverseOk && forwardOk) ? 0 : 1;
    }

    // ── helpers ────────────────────────────────────────────────────

    function _reverseNode(address a) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(ADDR_REVERSE_NODE, keccak256(_lowerHex(a))));
    }

    /// @dev Plain ENS namehash. Walks labels right-to-left.
    function _namehash(string memory name) internal pure returns (bytes32 node) {
        bytes memory b = bytes(name);
        node = bytes32(0);
        uint256 len = b.length;
        if (len == 0) return node;

        uint256 end = len;
        while (end > 0) {
            uint256 start = end;
            while (start > 0 && b[start - 1] != ".") { start--; }
            // label is b[start..end]
            bytes memory label = new bytes(end - start);
            for (uint256 i = 0; i < label.length; ++i) label[i] = b[start + i];
            bytes32 labelhash = keccak256(label);
            node = keccak256(abi.encodePacked(node, labelhash));
            end = start == 0 ? 0 : start - 1; // skip the '.'
        }
    }

    function _lowerHex(address a) internal pure returns (bytes memory out) {
        out = new bytes(40);
        uint256 v = uint160(a);
        for (uint256 i = 0; i < 40; ++i) {
            uint8 nibble = uint8((v >> (4 * (39 - i))) & 0xf);
            out[i] = nibble < 10 ? bytes1(uint8(48 + nibble)) : bytes1(uint8(87 + nibble));
        }
    }

    function _eq(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
