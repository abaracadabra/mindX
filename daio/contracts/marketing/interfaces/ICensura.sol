// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ICensura
/// @notice Subset of BONAFIDE Censura that the marketing profile depends on.
///         Vendored locally so `[profile.marketing]` is build-self-contained;
///         must stay byte-identical to
///         `openagents/conclave/contracts/src/interfaces/ICensura.sol`.
interface ICensura {
    function score(address subject) external view returns (uint8 score);
    function report(address subject, bytes32 reason) external;
}
