// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {THOTLib} from "../../THOT/libraries/THOTLib.sol";

/**
 * @title THOTLibTest
 * @notice Exercises Merkle commitment + Matryoshka prefix binding +
 *         RFC-6962 internal-node prefix + Solidity↔Python parity.
 *
 *         The parity test is the load-bearing one: it pins a known-good
 *         THOT8 packing + leaf hash that was produced by running
 *         `python validate.py` against seed=42 in the companion
 *         daio/contracts/THOT/python/ codec. If THOTLib drifts from
 *         the Python implementation, this test catches it at compile-time.
 */
contract THOTLibTest is Test {

    /// keccak256("THOT4096/leaf/v1") — must match THOTLib.LEAF_DOMAIN_4096
    bytes32 internal constant EXPECTED_LEAF_DOMAIN_4096 =
        0x6a2eb3245f906bbdfb322c5b4bbb6a66575ccc4dafd646358807d584a766e471;

    /// keccak256("THOT8/head/v1") — must match THOTLib.LEAF_DOMAIN_THOT8
    bytes32 internal constant EXPECTED_LEAF_DOMAIN_THOT8 =
        0x1eb5121703668e5b2a4de3e555064003b5cee4b3a91186eec0360791229e0e42;

    /// keccak256("THOT/tombstone/v1") — must match THOTLib.TOMBSTONE
    bytes32 internal constant EXPECTED_TOMBSTONE =
        0x5e5322bedf5f9f03f60b809513d373c39858173dc17312f5cec1a6ccdee9a65e;

    /// Pinned by `python validate.py` (seed=42). See
    /// daio/contracts/THOT/python/README.md for reproduction.
    bytes2  internal constant PARITY_THOT8_PACKED  = bytes2(0x599a);
    bytes32 internal constant PARITY_THOT8_HASH    =
        0x082a79ac6f4dc8b39325d907066f368be315954631a28f163270a6a15d0c4a25;

    // -----------------------------------------------------------------
    //                       Domain separator constants
    // -----------------------------------------------------------------

    function test_DomainSeparators_MatchSpec() public pure {
        assertEq(THOTLib.LEAF_DOMAIN_4096,  EXPECTED_LEAF_DOMAIN_4096);
        assertEq(THOTLib.LEAF_DOMAIN_THOT8, EXPECTED_LEAF_DOMAIN_THOT8);
        assertEq(THOTLib.TOMBSTONE,         EXPECTED_TOMBSTONE);
        assertEq(bytes32(THOTLib.NODE_PREFIX), bytes32(bytes1(0x01)));
    }

    // -----------------------------------------------------------------
    //                Solidity ↔ Python parity
    // -----------------------------------------------------------------

    /// @notice Hard-coded fixture from python validate.py (seed=42).
    ///         If THOTLib.hashTernaryHead and the Python codec stop
    ///         agreeing, this test fails immediately.
    function test_Parity_TernaryHeadMatchesPython() public pure {
        bytes32 onchain = THOTLib.hashTernaryHead(PARITY_THOT8_PACKED);
        assertEq(onchain, PARITY_THOT8_HASH,
                 "Solidity hashTernaryHead diverges from Python ternary_head_leaf");
    }

    // -----------------------------------------------------------------
    //                       Merkle root
    // -----------------------------------------------------------------

    function _fakeLeaves(uint256 n) internal pure returns (bytes32[] memory leaves) {
        leaves = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            leaves[i] = keccak256(abi.encodePacked("leaf", i));
        }
    }

    function test_MerkleRoot_PowerOfTwo() public pure {
        bytes32[] memory leaves = _fakeLeaves(64);
        bytes32 root = THOTLib.merkleRoot(leaves);
        assertTrue(root != bytes32(0), "non-zero root");
    }

    function test_MerkleRoot_TombstonePadding() public pure {
        // 12 leaves (THOT768 prefix shape) — must pad to 16 with TOMBSTONE.
        bytes32[] memory leaves = _fakeLeaves(12);
        bytes32 root  = THOTLib.merkleRoot(leaves);
        bytes32 root2 = THOTLib.merkleRoot(leaves);
        assertTrue(root != bytes32(0), "padded root non-zero");
        assertEq(root, root2, "deterministic");
    }

    function test_MerkleRoot_EmptyReturnsTombstone() public pure {
        bytes32[] memory none = new bytes32[](0);
        assertEq(THOTLib.merkleRoot(none), THOTLib.TOMBSTONE);
    }

    function test_MerkleRoot_DifferentLeavesDifferentRoots() public pure {
        bytes32[] memory a = _fakeLeaves(16);
        bytes32[] memory b = _fakeLeaves(16);
        b[3] = keccak256("perturbed");
        assertTrue(THOTLib.merkleRoot(a) != THOTLib.merkleRoot(b),
                   "perturbation detected");
    }

    /// @notice Pin the RFC-6962 internal-node prefix: a 2-leaf merkle
    ///         must hash via keccak(0x01 ‖ L ‖ R), NOT bare keccak(L ‖ R).
    function test_MerkleRoot_AppliesNodePrefix() public pure {
        bytes32 left  = bytes32(uint256(1));
        bytes32 right = bytes32(uint256(2));
        bytes32[] memory pair = new bytes32[](2);
        pair[0] = left;
        pair[1] = right;
        bytes32 actual   = THOTLib.merkleRoot(pair);
        bytes32 expected = keccak256(abi.encodePacked(THOTLib.NODE_PREFIX, left, right));
        bytes32 wrong    = keccak256(abi.encodePacked(left, right));
        assertEq(actual, expected,  "internal node missing 0x01 prefix");
        assertTrue(actual != wrong, "must NOT be bare keccak(L||R)");
    }

    // -----------------------------------------------------------------
    //                    Ternary head encoding
    // -----------------------------------------------------------------

    function test_TernaryHead_RejectsReservedCodon() public {
        // Codon 0 set to 0b11 (reserved).
        bytes2 packed = bytes2(uint16(0x0003));
        vm.expectRevert(abi.encodeWithSelector(
            THOTLib.InvalidTernaryEncoding.selector, packed
        ));
        THOTLib.hashTernaryHead(packed);
    }

    function test_TernaryHead_RejectsReservedCodonAtAnyPosition() public {
        // Codon at position 3 (bits 6-7) set to 0b11.
        bytes2 packed = bytes2(uint16(0x00C0));
        vm.expectRevert(abi.encodeWithSelector(
            THOTLib.InvalidTernaryEncoding.selector, packed
        ));
        THOTLib.hashTernaryHead(packed);
    }

    function test_TernaryHead_DifferentInputsDifferentHashes() public pure {
        bytes32 a = THOTLib.hashTernaryHead(bytes2(0x0101));
        bytes32 b = THOTLib.hashTernaryHead(bytes2(0x0102));
        assertTrue(a != b, "different inputs must yield different hashes");
    }

    // -----------------------------------------------------------------
    //                       Length validation
    // -----------------------------------------------------------------

    function test_AssertPrefixLeavesLength_THOT768() public {
        // 12 leaves is correct for THOT768.
        THOTLib.assertPrefixLeavesLength(768, 12);
        // 11 or 13 must revert.
        vm.expectRevert(abi.encodeWithSelector(
            THOTLib.PrefixLeavesLengthMismatch.selector, 768, 11, 12
        ));
        THOTLib.assertPrefixLeavesLength(768, 11);
    }

    function test_AssertPrefixLeavesLength_THOT1024() public {
        THOTLib.assertPrefixLeavesLength(1024, 16);
        vm.expectRevert();
        THOTLib.assertPrefixLeavesLength(1024, 15);
    }

    function test_AssertPrefixLeavesLength_THOT2048() public {
        THOTLib.assertPrefixLeavesLength(2048, 32);
        vm.expectRevert();
        THOTLib.assertPrefixLeavesLength(2048, 31);
    }

    function test_AssertPrefixLeavesLength_InvalidDim() public {
        vm.expectRevert(abi.encodeWithSelector(
            THOTLib.InvalidDimension.selector, 1234
        ));
        THOTLib.assertPrefixLeavesLength(1234, 5);
    }

    // -----------------------------------------------------------------
    //                Matryoshka prefix verification
    // -----------------------------------------------------------------

    function test_PrefixVerify_THOT1024_HappyPath() public pure {
        bytes32[] memory parentLeaves = _fakeLeaves(64);
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);

        bytes32[] memory prefixLeaves = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) prefixLeaves[i] = parentLeaves[i];
        bytes32 prefixRoot = THOTLib.merkleRoot(prefixLeaves);

        bytes32[] memory empty = new bytes32[](0);
        bytes32[] memory siblings = _rightSiblingsFor1024(parentLeaves);

        bool ok = THOTLib.verifyPrefix(parentRoot, 1024, prefixRoot, prefixLeaves, empty, siblings);
        assertTrue(ok, "1024 prefix verifies");
    }

    function test_PrefixVerify_RejectsWrongPrefixRoot() public {
        bytes32[] memory parentLeaves = _fakeLeaves(64);
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);

        bytes32[] memory prefixLeaves = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) prefixLeaves[i] = parentLeaves[i];

        bytes32 fakeRoot = keccak256("attacker root");
        bytes32[] memory empty = new bytes32[](0);
        bytes32[] memory siblings = _rightSiblingsFor1024(parentLeaves);

        vm.expectRevert();   // PrefixRootMismatch
        THOTLib.verifyPrefix(parentRoot, 1024, fakeRoot, prefixLeaves, empty, siblings);
    }

    function test_PrefixVerify_SilentSwapImpossible() public pure {
        bytes32[] memory parentA = _fakeLeaves(64);
        bytes32[] memory parentB = new bytes32[](64);
        for (uint256 i = 0; i < 64; i++) {
            parentB[i] = keccak256(abi.encodePacked("alt", i));
        }
        bytes32 rootA = THOTLib.merkleRoot(parentA);
        bytes32 rootB = THOTLib.merkleRoot(parentB);

        bytes32[] memory prefixLeaves = new bytes32[](16);
        for (uint256 i = 0; i < 16; i++) prefixLeaves[i] = parentA[i];
        bytes32 prefixRoot = THOTLib.merkleRoot(prefixLeaves);

        bytes32[] memory empty = new bytes32[](0);
        bytes32[] memory siblings = _rightSiblingsFor1024(parentA);

        bool ok = THOTLib.verifyPrefix(rootB, 1024, prefixRoot, prefixLeaves, empty, siblings);
        assertFalse(ok, "cannot rebind parentA prefix to parentB");

        ok = THOTLib.verifyPrefix(rootA, 1024, prefixRoot, prefixLeaves, empty, siblings);
        assertTrue(ok, "binds correctly to parentA");
    }

    function test_PrefixVerify_THOT768_WithCoWitness() public pure {
        bytes32[] memory parentLeaves = _fakeLeaves(64);
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);

        bytes32[] memory prefixLeaves = new bytes32[](12);
        for (uint256 i = 0; i < 12; i++) prefixLeaves[i] = parentLeaves[i];
        bytes32 prefixRoot = THOTLib.merkleRoot(prefixLeaves);   // tombstone-padded

        bytes32[] memory coWit = new bytes32[](4);
        for (uint256 i = 0; i < 4; i++) coWit[i] = parentLeaves[12 + i];

        bytes32[] memory siblings = _rightSiblingsFor1024(parentLeaves);

        bool ok = THOTLib.verifyPrefix(parentRoot, 768, prefixRoot, prefixLeaves, coWit, siblings);
        assertTrue(ok, "768 with co-witness verifies");
    }

    function test_PrefixVerify_RejectsBadLeafCount() public {
        // 5 prefix leaves cannot be a THOT768 (which needs 12).
        bytes32[] memory parentLeaves = _fakeLeaves(64);
        bytes32 parentRoot = THOTLib.merkleRoot(parentLeaves);

        bytes32[] memory bad = new bytes32[](5);
        for (uint256 i = 0; i < 5; i++) bad[i] = parentLeaves[i];

        bytes32[] memory empty = new bytes32[](0);
        bytes32[] memory siblings = new bytes32[](2);

        vm.expectRevert();   // PrefixLeavesLengthMismatch
        THOTLib.verifyPrefix(parentRoot, 768, bytes32(0), bad, empty, siblings);
    }

    // -----------------------------------------------------------------
    //                ternary-head Merkle inclusion
    // -----------------------------------------------------------------

    function test_TernaryHead_InclusionProof_HappyPath() public pure {
        // Build a 4-leaf tree where leaf 1 is the ternary head.
        bytes32 head    = THOTLib.hashTernaryHead(bytes2(0x599a));
        bytes32 leaf0   = keccak256("l0");
        bytes32 leaf2   = keccak256("l2");
        bytes32 leaf3   = keccak256("l3");

        bytes32[] memory leaves = new bytes32[](4);
        leaves[0] = leaf0;
        leaves[1] = head;
        leaves[2] = leaf2;
        leaves[3] = leaf3;
        bytes32 root = THOTLib.merkleRoot(leaves);

        // Inclusion path for index 1: sibling at level 0 is leaf0 (left),
        // then sibling at level 1 is hash(0x01, leaf2, leaf3) (right).
        bytes32[] memory path = new bytes32[](2);
        path[0] = leaf0;
        path[1] = keccak256(abi.encodePacked(THOTLib.NODE_PREFIX, leaf2, leaf3));

        assertTrue(THOTLib.verifyTernaryHead(root, head, path, 1));
    }

    function test_TernaryHead_InclusionProof_RejectsWrongLeaf() public pure {
        bytes32 head    = THOTLib.hashTernaryHead(bytes2(0x599a));
        bytes32 leaf0   = keccak256("l0");
        bytes32 leaf2   = keccak256("l2");
        bytes32 leaf3   = keccak256("l3");

        bytes32[] memory leaves = new bytes32[](4);
        leaves[0] = leaf0;
        leaves[1] = head;
        leaves[2] = leaf2;
        leaves[3] = leaf3;
        bytes32 root = THOTLib.merkleRoot(leaves);

        bytes32[] memory path = new bytes32[](2);
        path[0] = leaf0;
        path[1] = keccak256(abi.encodePacked(THOTLib.NODE_PREFIX, leaf2, leaf3));

        bytes32 fakeHead = THOTLib.hashTernaryHead(bytes2(0x5555));
        assertFalse(THOTLib.verifyTernaryHead(root, fakeHead, path, 1));
    }

    // -----------------------------------------------------------------
    //                          Helpers
    // -----------------------------------------------------------------

    /// @dev Right-sibling path for the 16-leaf THOT1024 prefix subtree
    ///      inside a 64-leaf parent. Rebuilt level-by-level applying the
    ///      NODE_PREFIX so it exactly matches `merkleRoot`'s computation.
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

        // 16-leaf prefix sits at level 4. Climb is 2 steps: pair with
        // l4[1], then pair with l5[1].
        siblings = new bytes32[](2);
        siblings[0] = l4[1];
        siblings[1] = l5[1];
    }
}
