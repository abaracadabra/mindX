// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

/**
 * @title ITHOTCommitmentRegistry
 * @notice Cryptographic substrate interface for THOT4096 Merkle commitments.
 *
 *         This is INTENTIONALLY DISTINCT from ITHOTRegistry (the
 *         discovery/rating registry at THOT/interfaces/ITHOTRegistry.sol):
 *
 *         - ITHOTRegistry            tracks model name, parameter count,
 *                                    ratings, deployment count — discovery.
 *         - ITHOTCommitmentRegistry  tracks canonical Merkle roots, ternary
 *                                    heads, prefix bindings, revocations —
 *                                    cryptographic substrate.
 *
 *         They coexist. Both are queried by AgenticPlace and iNFT_7857
 *         for different purposes.
 *
 *         Concrete implementation: THOT/commitment/THOTCommitmentRegistry.sol.
 *         Consumed by:             inft/iNFT_7857.sol (attachThotRoot +
 *                                                       transfer revoke gate).
 */
interface ITHOTCommitmentRegistry {
    /// @notice True iff a canonical THOT4096 with this root has been issued.
    function isRegistered(bytes32 root) external view returns (bool);

    /// @notice True iff the root has been censura-revoked.
    function isRevoked(bytes32 root) external view returns (bool);

    /// @notice The ternary-head sub-leaf hash committed for this THOT4096,
    ///         or bytes32(0) if not registered.
    function ternaryHeadOf(bytes32 root) external view returns (bytes32);

    /// @notice Lookup a Matryoshka prefix root for a registered parent.
    /// @param  parentRoot Canonical THOT4096 root.
    /// @param  prefixDim  One of {768, 1024, 2048}.
    /// @return prefixRoot The prefix root, or bytes32(0) when !exists.
    /// @return exists     Whether a prefix has been registered at this dim.
    function getPrefix(bytes32 parentRoot, uint16 prefixDim)
        external
        view
        returns (bytes32 prefixRoot, bool exists);
}
