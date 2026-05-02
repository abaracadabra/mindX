// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ITessera
/// @notice Subset of the BONAFIDE Tessera interface that Conclave depends on.
///         Tessera is the soulbound W3C-DID credential anchor in BONAFIDE.
///         A holder is "seated" if they have an active, unrevoked credential.
interface ITessera {
    /// @return seated true iff `holder` has a valid, unrevoked credential.
    function hasValidCredential(address holder) external view returns (bool seated);

    /// @return did the holder's W3C DID, e.g. "did:bankon:0xabc...".
    function didOf(address holder) external view returns (string memory did);

    /// @return pubkey the Ed25519 transport pubkey bound to this credential
    ///         (32 bytes, used as the AXL peer id).
    function transportKeyOf(address holder) external view returns (bytes32 pubkey);
}
