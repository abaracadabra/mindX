// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {THOTCommitmentRegistry} from "../../THOT/commitment/THOTCommitmentRegistry.sol";
import {THOTLib} from "../../THOT/libraries/THOTLib.sol";

/**
 * @title THOTCommitmentRegistryTest
 * @notice Covers issuance, revocation (CENSURA_ROLE), prefix
 *         registration with proper 6-arg call (the zip's test was broken
 *         here), recordEdge access control + no-overwrite, and the
 *         ITHOTCommitmentRegistry view surface that iNFT_7857 consumes.
 */
contract THOTCommitmentRegistryTest is Test {
    THOTCommitmentRegistry public registry;

    address public gate;
    address public admin;
    address public issuer;
    address public stranger;
    address public censor;

    function setUp() public {
        gate     = makeAddr("bankon-gate");
        admin    = makeAddr("admin-multisig");
        issuer   = makeAddr("issuer-A");
        stranger = makeAddr("stranger");
        censor   = makeAddr("censura-quorum");

        registry = new THOTCommitmentRegistry(gate, admin);

        vm.prank(gate);
        registry.authorizeIssuer(issuer);

        // Grant CENSURA_ROLE to a dedicated address (admin already has it
        // from the constructor). Read the role constant FIRST so vm.prank
        // doesn't get consumed by the public-getter call.
        bytes32 censuraRole = registry.CENSURA_ROLE();
        vm.prank(admin);
        registry.grantRole(censuraRole, censor);
    }

    // -----------------------------------------------------------------
    //                  Constructor + roles
    // -----------------------------------------------------------------

    function test_Constructor_RejectsZeroGate() public {
        vm.expectRevert(THOTCommitmentRegistry.ZeroAddress.selector);
        new THOTCommitmentRegistry(address(0), admin);
    }

    function test_Constructor_RejectsZeroAdmin() public {
        vm.expectRevert(THOTCommitmentRegistry.ZeroAddress.selector);
        new THOTCommitmentRegistry(gate, address(0));
    }

    function test_Admin_HasCensuraRoleAtDeploy() public view {
        assertTrue(registry.hasRole(registry.CENSURA_ROLE(), admin));
        assertTrue(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_GateRotation_OnlyDefaultAdmin() public {
        address newGate = makeAddr("new-gate");
        vm.prank(stranger);
        vm.expectRevert();
        registry.setBankonIdentityGate(newGate);

        vm.prank(admin);
        registry.setBankonIdentityGate(newGate);
        assertEq(registry.bankonIdentityGate(), newGate);
    }

    function test_GateRotation_RejectsZero() public {
        vm.prank(admin);
        vm.expectRevert(THOTCommitmentRegistry.ZeroAddress.selector);
        registry.setBankonIdentityGate(address(0));
    }

    // -----------------------------------------------------------------
    //                  Issuer authorization
    // -----------------------------------------------------------------

    function test_AuthorizeIssuer_OnlyGate() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.NotIdentityGate.selector, stranger
        ));
        registry.authorizeIssuer(stranger);
    }

    function test_GateCanRevokeIssuer() public {
        vm.prank(gate);
        registry.revokeIssuer(issuer);
        assertFalse(registry.authorizedIssuers(issuer));
    }

    function test_AuthorizeIssuer_RejectsZero() public {
        vm.prank(gate);
        vm.expectRevert(THOTCommitmentRegistry.ZeroAddress.selector);
        registry.authorizeIssuer(address(0));
    }

    // -----------------------------------------------------------------
    //                          Issuance
    // -----------------------------------------------------------------

    function test_IssueTHOT4096_HappyPath() public {
        bytes32 root = keccak256("root-1");
        bytes32 head = keccak256("head-1");
        vm.prank(issuer);
        registry.issueTHOT4096(root, head, 255, "ipfs://payload", "ipfs://meta");

        (
            bytes32 r,
            bytes32 h,
            uint256 idx,
            address iss,
            ,
            ,
            ,
            bool exists
        ) = registry.parents(root);
        assertEq(r, root);
        assertEq(h, head);
        assertEq(idx, 255);
        assertEq(iss, issuer);
        assertTrue(exists);

        // ITHOTCommitmentRegistry views.
        assertTrue(registry.isRegistered(root));
        assertFalse(registry.isRevoked(root));
        assertEq(registry.ternaryHeadOf(root), head);
    }

    function test_IssueTHOT4096_RejectsUnauthorized() public {
        bytes32 root = keccak256("root-2");
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.NotAuthorizedIssuer.selector, stranger
        ));
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
    }

    function test_IssueTHOT4096_RejectsDuplicate() public {
        bytes32 root = keccak256("root-3");
        vm.startPrank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTAlreadyExists.selector, root
        ));
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
        vm.stopPrank();
    }

    // -----------------------------------------------------------------
    //                  Revocation (CENSURA_ROLE)
    // -----------------------------------------------------------------

    function test_Revoke_HappyPath() public {
        bytes32 root = keccak256("root-revoke");
        vm.prank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");

        vm.prank(censor);
        registry.revoke(root, "backdoor discovered");
        assertTrue(registry.isRevoked(root));
        assertTrue(registry.isRegistered(root), "revoke preserves registration");
        assertEq(registry.revocationReasons(root), "backdoor discovered");
    }

    function test_Revoke_OnlyCensura() public {
        bytes32 root = keccak256("root-rev-auth");
        vm.prank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");

        vm.prank(stranger);
        vm.expectRevert();
        registry.revoke(root, "no");
    }

    function test_Revoke_UnknownRoot() public {
        bytes32 unknown = keccak256("nope");
        vm.prank(censor);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTNotFound.selector, unknown
        ));
        registry.revoke(unknown, "no");
    }

    function test_Revoke_RejectsReissue() public {
        bytes32 root = keccak256("root-doubletap");
        vm.prank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
        vm.prank(censor);
        registry.revoke(root, "censured");
        // Even after we delete the parent (we don't), revocation flag
        // persists and blocks any re-issuance attempts using the same root.
        // Here we just check that re-issuance is blocked by THOTAlreadyExists
        // before the THOTRevokedAtIssuance check could fire.
        vm.prank(issuer);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTAlreadyExists.selector, root
        ));
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
    }

    function test_Unrevoke_HappyPath() public {
        bytes32 root = keccak256("root-unrev");
        vm.prank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
        vm.prank(censor);
        registry.revoke(root, "false positive");
        assertTrue(registry.isRevoked(root));
        vm.prank(censor);
        registry.unrevoke(root);
        assertFalse(registry.isRevoked(root));
        assertEq(registry.revocationReasons(root), "");
    }

    // -----------------------------------------------------------------
    //                  Prefix registration
    // -----------------------------------------------------------------

    function _registerParent(bytes32 root) internal {
        vm.prank(issuer);
        registry.issueTHOT4096(root, bytes32(0), 0, "cid", "meta");
    }

    function _emptyBytes32() internal pure returns (bytes32[] memory empty) {
        empty = new bytes32[](0);
    }

    function test_RegisterPrefix_RejectsInvalidDimension() public {
        bytes32 root = keccak256("root-pre-A");
        _registerParent(root);
        bytes32[] memory empty = _emptyBytes32();

        // The 6-arg call (zip's test was wrong here with 5 args).
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.InvalidPrefixDimension.selector, uint16(1234)
        ));
        registry.registerPrefix(root, 1234, bytes32(0), empty, empty, empty);
    }

    function test_RegisterPrefix_RejectsUnknownParent() public {
        bytes32 unknown = keccak256("never-issued");
        bytes32[] memory empty = _emptyBytes32();
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTNotFound.selector, unknown
        ));
        registry.registerPrefix(unknown, 768, bytes32(0), empty, empty, empty);
    }

    function test_RegisterPrefix_RejectsBadLeafCount() public {
        // Parent registered, but prefixLeaves array length is wrong for THOT1024.
        bytes32 root = keccak256("root-pre-B");
        _registerParent(root);

        bytes32[] memory bad = new bytes32[](5);
        for (uint256 i = 0; i < 5; i++) bad[i] = bytes32(uint256(i));

        bytes32[] memory empty = _emptyBytes32();

        vm.expectRevert();   // PrefixLeavesLengthMismatch from THOTLib
        registry.registerPrefix(root, 1024, bytes32(0), bad, empty, empty);
    }

    function test_RegisterPrefix_HappyPath_THOT1024() public {
        // Build a real prefix proof against a synthetic 64-leaf parent.
        bytes32[] memory parentLeaves = new bytes32[](64);
        for (uint256 i = 0; i < 64; i++) {
            parentLeaves[i] = keccak256(abi.encodePacked("p", i));
        }
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);

        // Register that root in the registry.
        vm.prank(issuer);
        registry.issueTHOT4096(parentRoot, bytes32(0), 0, "cid", "meta");

        // First 16 leaves = THOT1024 prefix.
        bytes32[] memory prefixLeaves = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) prefixLeaves[i] = parentLeaves[i];
        bytes32 prefixRoot = THOTLib.merkleRoot(prefixLeaves);

        bytes32[] memory empty = _emptyBytes32();
        bytes32[] memory siblings = _rightSiblingsFor1024(parentLeaves);

        registry.registerPrefix(parentRoot, 1024, prefixRoot, prefixLeaves, empty, siblings);

        (bytes32 storedRoot, bool exists) = registry.getPrefix(parentRoot, 1024);
        assertTrue(exists);
        assertEq(storedRoot, prefixRoot);
    }

    function test_RegisterPrefix_RejectsDuplicate() public {
        bytes32[] memory parentLeaves = new bytes32[](64);
        for (uint256 i = 0; i < 64; i++) {
            parentLeaves[i] = keccak256(abi.encodePacked("dup", i));
        }
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);
        vm.prank(issuer);
        registry.issueTHOT4096(parentRoot, bytes32(0), 0, "cid", "meta");

        bytes32[] memory prefixLeaves = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) prefixLeaves[i] = parentLeaves[i];
        bytes32 prefixRoot = THOTLib.merkleRoot(prefixLeaves);

        bytes32[] memory empty = _emptyBytes32();
        bytes32[] memory siblings = _rightSiblingsFor1024(parentLeaves);

        registry.registerPrefix(parentRoot, 1024, prefixRoot, prefixLeaves, empty, siblings);

        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.PrefixAlreadyRegistered.selector, parentRoot, uint16(1024)
        ));
        registry.registerPrefix(parentRoot, 1024, prefixRoot, prefixLeaves, empty, siblings);
    }

    // -----------------------------------------------------------------
    //                  Diagonal edges
    // -----------------------------------------------------------------

    function test_RecordEdge_OnlyAuthorizedIssuer() public {
        bytes32 a = keccak256("e-a");
        bytes32 b = keccak256("e-b");
        vm.startPrank(issuer);
        registry.issueTHOT4096(a, bytes32(0), 0, "cid", "meta");
        registry.issueTHOT4096(b, bytes32(0), 0, "cid", "meta");
        vm.stopPrank();

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.NotAuthorizedIssuer.selector, stranger
        ));
        registry.recordEdge(a, b, THOTCommitmentRegistry.EdgeKind.Distillation, bytes32(0));
    }

    function test_RecordEdge_HappyPath() public {
        bytes32 teacher = keccak256("teacher-4096");
        bytes32 student = keccak256("student-768");

        vm.startPrank(issuer);
        registry.issueTHOT4096(teacher, bytes32(0), 0, "ipfs://t", "ipfs://tm");
        registry.issueTHOT4096(student, bytes32(0), 0, "ipfs://s", "ipfs://sm");

        bytes32 attest = keccak256("attestation-1");
        bytes32 edgeId = registry.recordEdge(
            teacher, student, THOTCommitmentRegistry.EdgeKind.Distillation, attest
        );
        vm.stopPrank();
        assertTrue(edgeId != bytes32(0));

        (bytes32 fr, bytes32 to,, bytes32 a,, ) = registry.edges(edgeId);
        assertEq(fr, teacher);
        assertEq(to, student);
        assertEq(a, attest);
    }

    function test_RecordEdge_NoOverwrite() public {
        bytes32 a = keccak256("dup-a");
        bytes32 b = keccak256("dup-b");
        vm.startPrank(issuer);
        registry.issueTHOT4096(a, bytes32(0), 0, "cid", "meta");
        registry.issueTHOT4096(b, bytes32(0), 0, "cid", "meta");

        bytes32 edgeId =
            registry.recordEdge(a, b, THOTCommitmentRegistry.EdgeKind.Projection, keccak256("v1"));

        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.EdgeAlreadyRecorded.selector, edgeId
        ));
        registry.recordEdge(a, b, THOTCommitmentRegistry.EdgeKind.Projection, keccak256("v2"));
        vm.stopPrank();
    }

    function test_RecordEdge_RejectsUnknownFromOrTo() public {
        bytes32 known = keccak256("known");
        vm.prank(issuer);
        registry.issueTHOT4096(known, bytes32(0), 0, "cid", "meta");

        bytes32 unknown = keccak256("unknown");
        vm.startPrank(issuer);
        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTNotFound.selector, unknown
        ));
        registry.recordEdge(known, unknown, THOTCommitmentRegistry.EdgeKind.Projection, bytes32(0));

        vm.expectRevert(abi.encodeWithSelector(
            THOTCommitmentRegistry.THOTNotFound.selector, unknown
        ));
        registry.recordEdge(unknown, known, THOTCommitmentRegistry.EdgeKind.Projection, bytes32(0));
        vm.stopPrank();
    }

    // -----------------------------------------------------------------
    //                          Helpers
    // -----------------------------------------------------------------

    function _rightSiblingsFor1024(bytes32[] memory parentLeaves)
        internal
        pure
        returns (bytes32[] memory siblings)
    {
        bytes1 P = THOTLib.NODE_PREFIX;

        bytes32[] memory l1 = new bytes32[](32);
        for (uint256 i = 0; i < 32; i++) {
            l1[i] = keccak256(abi.encodePacked(P, parentLeaves[2 * i], parentLeaves[2 * i + 1]));
        }
        bytes32[] memory l2 = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) {
            l2[i] = keccak256(abi.encodePacked(P, l1[2 * i], l1[2 * i + 1]));
        }
        bytes32[] memory l3 = new bytes32[](8);
        for (uint256 i = 0; i < 8; i++) {
            l3[i] = keccak256(abi.encodePacked(P, l2[2 * i], l2[2 * i + 1]));
        }
        bytes32[] memory l4 = new bytes32[](4);
        for (uint256 i = 0; i < 4; i++) {
            l4[i] = keccak256(abi.encodePacked(P, l3[2 * i], l3[2 * i + 1]));
        }
        bytes32[] memory l5 = new bytes32[](2);
        for (uint256 i = 0; i < 2; i++) {
            l5[i] = keccak256(abi.encodePacked(P, l4[2 * i], l4[2 * i + 1]));
        }

        siblings = new bytes32[](2);
        siblings[0] = l4[1];
        siblings[1] = l5[1];
    }
}
