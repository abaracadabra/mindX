// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Token type enumeration for bonding curve deployments
/// @dev Allows selection of different token implementations
enum TokenType {
    CURVE_TOKEN,        // Standard bonding curve token (default)
    REFLECTION_REWARD,  // Reflection token with reward distribution
    REBASE_TOKEN       // Rebase token (DeltaV-style)
}
