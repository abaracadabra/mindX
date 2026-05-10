// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ITessera
/// @notice Subset of BONAFIDE Tessera that the marketing profile depends on.
///         Vendored locally so `[profile.marketing]` is build-self-contained;
///         must stay byte-identical to
///         `openagents/conclave/contracts/src/interfaces/ITessera.sol`.
interface ITessera {
    function hasValidCredential(address holder) external view returns (bool seated);
    function didOf(address holder) external view returns (string memory did);
    function transportKeyOf(address holder) external view returns (bytes32 pubkey);
}
