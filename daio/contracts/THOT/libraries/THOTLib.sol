// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

/**
 * @title THOTLib
 * @notice Pure-function library for THOT Merkle commitment verification
 *         and Matryoshka prefix binding.
 *
 *         Canonical leaf layout (THOTS.md §9):
 *           - 64 leaves of 64 dimensions each for THOT4096
 *           - 32 leaves for THOT2048 prefix
 *           - 16 leaves for THOT1024 prefix
 *           - 12 leaves for THOT768  prefix (padded to 16 with TOMBSTONE)
 *           -  1 dedicated ternary head leaf for THOT8 (sub-leaf artifact)
 *
 *         All hashes are Keccak-256. Domain separators
 *           - LEAF_DOMAIN_4096   for THOT4096 leaves
 *           - LEAF_DOMAIN_THOT8  for the ternary head sub-leaf
 *           - NODE_PREFIX        (single byte 0x01) on every internal node
 *         eliminate the second-preimage / leaf-vs-node confusion attack
 *         (RFC-6962 §2.1; OpenZeppelin#3091; Bitcoin CVE-2012-2459).
 *
 *         Cypherpunk2048 alignment. Companion off-chain codec:
 *         daio/contracts/THOT/python/thot/merkle.py.
 */
library THOTLib {
    // -----------------------------------------------------------------
    //                       Domain separators
    // -----------------------------------------------------------------

    /// keccak256("THOT4096/leaf/v1")
    bytes32 internal constant LEAF_DOMAIN_4096 =
        0x6a2eb3245f906bbdfb322c5b4bbb6a66575ccc4dafd646358807d584a766e471;

    /// keccak256("THOT8/head/v1")
    bytes32 internal constant LEAF_DOMAIN_THOT8 =
        0x1eb5121703668e5b2a4de3e555064003b5cee4b3a91186eec0360791229e0e42;

    /// keccak256("THOT/tombstone/v1")
    bytes32 internal constant TOMBSTONE =
        0x5e5322bedf5f9f03f60b809513d373c39858173dc17312f5cec1a6ccdee9a65e;

    /// RFC-6962 internal-node prefix. Every Merkle internal-node hash is
    /// computed as keccak256(NODE_PREFIX ‖ left ‖ right). This prevents an
    /// attacker from passing internal-node bytes off as a leaf or vice
    /// versa. The Python companion at THOT/python/thot/merkle.py uses the
    /// identical byte and MUST be kept in sync.
    bytes1 internal constant NODE_PREFIX = 0x01;

    // -----------------------------------------------------------------
    //                            Errors
    // -----------------------------------------------------------------

    error InvalidDimension(uint256 dim);
    error InvalidTernaryEncoding(bytes2 codon);
    error PrefixRootMismatch(bytes32 expected, bytes32 actual);
    error PrefixLeavesLengthMismatch(uint256 dim, uint256 got, uint256 expected);

    // -----------------------------------------------------------------
    //                       Canonical dimensions
    // -----------------------------------------------------------------

    /// @notice The five canonical THOT dimensions.
    /// @dev    Smaller dims are Matryoshka-provable prefixes of larger ones.
    function canonicalDimensions() internal pure returns (uint16[5] memory dims) {
        dims[0] = 8;
        dims[1] = 768;
        dims[2] = 1024;
        dims[3] = 2048;
        dims[4] = 4096;
    }

    /// @notice Number of 64-dim leaves required to cover a given dim, plus
    ///         padded power-of-two count after tombstone padding.
    /// @dev    For dim=8 the THOT8 is a single sub-leaf artifact (not a
    ///         Merkle prefix), but is modelled here as 1 leaf for layout
    ///         consistency.
    function leafCountForDim(uint256 dim)
        internal
        pure
        returns (uint256 leafCount, uint256 paddedCount)
    {
        if (dim == 8) {
            leafCount = 1;
        } else if (dim == 768 || dim == 1024 || dim == 2048 || dim == 4096) {
            leafCount = (dim + 63) / 64;     // 12 / 16 / 32 / 64 respectively
        } else {
            revert InvalidDimension(dim);
        }
        paddedCount = _nextPowerOfTwo(leafCount);
    }

    /// @notice Assert that a provided prefixLeaves array has the canonical
    ///         length for the asserted dimension. Cheap upfront rejection so
    ///         downstream merkleRoot/verifyPrefix never sees malformed input.
    ///
    /// @dev    Reverts with PrefixLeavesLengthMismatch on mismatch. Used by
    ///         THOTCommitmentRegistry.registerPrefix before the expensive
    ///         tree reconstruction.
    function assertPrefixLeavesLength(uint256 dim, uint256 leavesLen) internal pure {
        (uint256 expected, ) = leafCountForDim(dim);
        if (leavesLen != expected) {
            revert PrefixLeavesLengthMismatch(dim, leavesLen, expected);
        }
    }

    // -----------------------------------------------------------------
    //                      Leaf-level hashing
    // -----------------------------------------------------------------

    /**
     * @notice Hash a single 64-dim chunk into a Merkle leaf.
     * @param  index     Leaf index in [0, 64).
     * @param  dimStart  First dimension covered by this leaf.
     * @param  dimEnd    Last dimension covered (exclusive).
     * @param  chunk     128 bytes of fp16 (64 values).
     * @return Leaf hash, domain-separated by LEAF_DOMAIN_4096.
     */
    function hashLeaf4096(
        uint32 index,
        uint16 dimStart,
        uint16 dimEnd,
        bytes calldata chunk
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(LEAF_DOMAIN_4096, index, dimStart, dimEnd, chunk));
    }

    /**
     * @notice Hash the ternary-head sub-leaf for THOT8.
     * @param  packedTernary  Two bytes encoding eight ternary values
     *                        (2 bits each, LSB-first within the word —
     *                         see THOTS.md §3.2 and THOT/python/thot/thot8_cpu.py).
     * @return Domain-separated leaf hash.
     * @dev    Reverts on any reserved codon (0b11) per THOTS.md §3.2.
     */
    function hashTernaryHead(bytes2 packedTernary) internal pure returns (bytes32) {
        _validateTernary(packedTernary);
        return keccak256(abi.encodePacked(LEAF_DOMAIN_THOT8, packedTernary, bytes30(0)));
    }

    /// @dev Reverts if any 2-bit codon equals the reserved 0b11.
    function _validateTernary(bytes2 packedTernary) private pure {
        uint16 v = uint16(packedTernary);
        for (uint256 i = 0; i < 8; i++) {
            uint256 codon = (v >> (i * 2)) & 0x3;
            if (codon == 0x3) revert InvalidTernaryEncoding(packedTernary);
        }
    }

    // -----------------------------------------------------------------
    //                      Merkle root computation
    // -----------------------------------------------------------------

    /**
     * @notice Compute the Merkle root of an ordered leaf array, padding
     *         with TOMBSTONE up to the next power of two. Internal-node
     *         hashing applies NODE_PREFIX per RFC-6962.
     * @param  leaves Ordered leaves.
     * @return Merkle root (32 bytes).
     */
    function merkleRoot(bytes32[] memory leaves) internal pure returns (bytes32) {
        uint256 n = leaves.length;
        if (n == 0) return TOMBSTONE;
        uint256 padded = _nextPowerOfTwo(n);

        bytes32[] memory layer = new bytes32[](padded);
        for (uint256 i = 0; i < n; i++) layer[i] = leaves[i];
        for (uint256 i = n; i < padded; i++) layer[i] = TOMBSTONE;

        while (layer.length > 1) {
            uint256 half = layer.length / 2;
            bytes32[] memory next = new bytes32[](half);
            for (uint256 i = 0; i < half; i++) {
                next[i] = keccak256(abi.encodePacked(
                    NODE_PREFIX, layer[2 * i], layer[2 * i + 1]
                ));
            }
            layer = next;
        }
        return layer[0];
    }

    // -----------------------------------------------------------------
    //                Matryoshka prefix-binding verification
    // -----------------------------------------------------------------

    /**
     * @notice Verify that prefixRoot is the canonical Matryoshka prefix
     *         root of parentRoot at dimension prefixDim.
     *
     *  Three modes (matching THOT/python/thot/matryoshka.py):
     *
     *    Mode A — Pure Merkle prefix (power-of-two-aligned dims).
     *      THOT1024 (16 leaves) and THOT2048 (32 leaves). The prefix root
     *      IS the parent's subtree root at the corresponding level.
     *      `coWitnessLeaves` is empty.
     *
     *    Mode B — Merkle prefix with co-witness leaves (non-pow2 dims).
     *      THOT768 (12 leaves padded to 16). The canonical prefix root is
     *      the tombstone-padded Merkle root of the 12 prefix leaves. The
     *      parent tree at the same internal node uses real data at
     *      positions 12..15. `coWitnessLeaves` reveals those 4 leaves so
     *      the verifier can reconstruct the parent subtree node.
     *
     *    Mode C — Sibling commitment (THOT8). Handled by registry equality
     *      with the stored ternaryHead, not by this function.
     *
     * @param  parentRoot      Canonical THOT4096 root.
     * @param  prefixDim       One of {768, 1024, 2048}.
     * @param  prefixRoot      Asserted prefix root.
     * @param  prefixLeaves    Actual leaves covering [0, prefixDim). Length
     *                         must satisfy assertPrefixLeavesLength.
     * @param  coWitnessLeaves Extra leaves needed when prefix is non-pow2.
     *                         Empty for Mode A.
     * @param  rightSiblings   Right-sibling hashes from the parent subtree
     *                         node up to (not including) the parent root.
     */
    function verifyPrefix(
        bytes32 parentRoot,
        uint256 prefixDim,
        bytes32 prefixRoot,
        bytes32[] memory prefixLeaves,
        bytes32[] memory coWitnessLeaves,
        bytes32[] memory rightSiblings
    ) internal pure returns (bool) {
        // (0) Length sanity. Cheap rejection so downstream work is bounded.
        assertPrefixLeavesLength(prefixDim, prefixLeaves.length);

        // (1) Recompute the canonical prefix root (tombstone-padded inside).
        bytes32 reconstructedPrefix = merkleRoot(prefixLeaves);
        if (reconstructedPrefix != prefixRoot) {
            revert PrefixRootMismatch(reconstructedPrefix, prefixRoot);
        }

        // (2) Reconstruct the parent subtree node from real data.
        bytes32 subtreeNode;
        if (coWitnessLeaves.length == 0) {
            subtreeNode = prefixRoot;
        } else {
            bytes32[] memory combined = new bytes32[](
                prefixLeaves.length + coWitnessLeaves.length
            );
            for (uint256 i = 0; i < prefixLeaves.length; i++) {
                combined[i] = prefixLeaves[i];
            }
            for (uint256 j = 0; j < coWitnessLeaves.length; j++) {
                combined[prefixLeaves.length + j] = coWitnessLeaves[j];
            }
            subtreeNode = merkleRoot(combined);
        }

        // (3) Climb to the parent root via right siblings, applying the
        //     NODE_PREFIX on every step to match merkleRoot.
        bytes32 cursor = subtreeNode;
        for (uint256 i = 0; i < rightSiblings.length; i++) {
            cursor = keccak256(abi.encodePacked(
                NODE_PREFIX, cursor, rightSiblings[i]
            ));
        }
        return cursor == parentRoot;
    }

    /**
     * @notice Verify that ternaryHeadLeaf is the dedicated THOT8 sub-leaf
     *         of parentRoot, given its Merkle inclusion proof.
     *
     * @dev    Climb applies NODE_PREFIX on every step to match merkleRoot
     *         and the off-chain Python implementation.
     */
    function verifyTernaryHead(
        bytes32 parentRoot,
        bytes32 ternaryHeadLeaf,
        bytes32[] memory path,
        uint256 leafIndex
    ) internal pure returns (bool) {
        bytes32 cursor = ternaryHeadLeaf;
        uint256 idx = leafIndex;
        for (uint256 i = 0; i < path.length; i++) {
            if (idx & 1 == 0) {
                cursor = keccak256(abi.encodePacked(NODE_PREFIX, cursor, path[i]));
            } else {
                cursor = keccak256(abi.encodePacked(NODE_PREFIX, path[i], cursor));
            }
            idx >>= 1;
        }
        return cursor == parentRoot;
    }

    // -----------------------------------------------------------------
    //                          Internal utils
    // -----------------------------------------------------------------

    function _nextPowerOfTwo(uint256 n) private pure returns (uint256) {
        if (n <= 1) return 1;
        uint256 p = 1;
        while (p < n) p <<= 1;
        return p;
    }
}
