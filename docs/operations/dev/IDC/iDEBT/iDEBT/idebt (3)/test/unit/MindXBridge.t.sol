// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test }        from "forge-std/Test.sol";
import { MindXBridge } from "../../src/integrations/MindXBridge.sol";
import { IMindX }      from "../../src/interfaces/IMindX.sol";

contract MindXBridgeTest is Test {
    MindXBridge bridge;
    address admin = address(0xA11CE);
    uint256 mindxPk = 0x11111;
    address mindxAddr;

    function setUp() public {
        mindxAddr = vm.addr(mindxPk);
        bridge = new MindXBridge(admin, mindxAddr);
    }

    function _sign(IMindX.Attestation memory a) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            bridge.ATTESTATION_TYPEHASH(),
            a.requestId, a.claimHash, a.issuedAt, a.modelVersion, a.riskScore, a.subject
        ));
        bytes32 domain = bytes32(0); // read via view
        // We'll compute digest via EIP712 helper: use domainSeparator from contract
        // by accessing public getter (we don't expose it; recompute):
        bytes32 typeHash = keccak256(
            "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
        );
        bytes32 nameHash = keccak256(bytes("iDEBT-mindX"));
        bytes32 versionHash = keccak256(bytes("1"));
        domain = keccak256(abi.encode(typeHash, nameHash, versionHash, block.chainid, address(bridge)));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(mindxPk, digest);
        return abi.encodePacked(r, s, v);
    }

    function test_Settle_RecordsRiskScore() public {
        IMindX.Attestation memory a = IMindX.Attestation({
            requestId:    bytes32("REQ1"),
            claimHash:    keccak256("claim"),
            issuedAt:     uint64(block.timestamp),
            modelVersion: 963,
            riskScore:    4_250, // 42.50%
            subject:      address(0xBEEF)
        });
        bytes memory sig = _sign(a);
        bridge.settle(a, sig);

        (uint16 score, uint64 at) = bridge.latestRiskScore(address(0xBEEF));
        assertEq(score, 4_250);
        assertEq(at, uint64(block.timestamp));
    }

    function test_Settle_RevertsOnReplay() public {
        IMindX.Attestation memory a = IMindX.Attestation({
            requestId:    bytes32("REQ2"),
            claimHash:    keccak256("claim"),
            issuedAt:     uint64(block.timestamp),
            modelVersion: 963,
            riskScore:    3_000,
            subject:      address(0xBEEF)
        });
        bytes memory sig = _sign(a);
        bridge.settle(a, sig);
        vm.expectRevert(IMindX.AttestationReplayed.selector);
        bridge.settle(a, sig);
    }

    function test_RejectsUnknownSigner() public {
        uint256 evilPk = 0x22222;
        IMindX.Attestation memory a = IMindX.Attestation({
            requestId:    bytes32("REQ3"),
            claimHash:    keccak256("claim"),
            issuedAt:     uint64(block.timestamp),
            modelVersion: 963,
            riskScore:    1_000,
            subject:      address(0xBEEF)
        });
        bytes32 structHash = keccak256(abi.encode(
            bridge.ATTESTATION_TYPEHASH(),
            a.requestId, a.claimHash, a.issuedAt, a.modelVersion, a.riskScore, a.subject
        ));
        bytes32 nameHash = keccak256(bytes("iDEBT-mindX"));
        bytes32 versionHash = keccak256(bytes("1"));
        bytes32 typeHash = keccak256(
            "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
        );
        bytes32 domain = keccak256(abi.encode(typeHash, nameHash, versionHash, block.chainid, address(bridge)));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(evilPk, digest);
        bytes memory sig = abi.encodePacked(r, s, v);

        vm.expectRevert(IMindX.BadSignature.selector);
        bridge.settle(a, sig);
    }
}
