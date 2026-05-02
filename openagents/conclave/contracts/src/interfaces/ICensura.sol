// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ICensura
/// @notice Subset of the BONAFIDE Censura reputation interface.
///         Scores are uint8 (0-255) and decay/grow per Censura's rules.
interface ICensura {
    /// @return score current reputation score for `subject`.
    function score(address subject) external view returns (uint8 score);

    /// @notice Report a member for protocol abuse. Slashes some reputation.
    /// @dev Implementation-defined; Conclave only needs the function selector.
    function report(address subject, bytes32 reason) external;
}
