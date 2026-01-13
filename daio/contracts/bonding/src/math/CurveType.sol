// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Bonding curve type enumeration
/// @dev Different curve types provide different price discovery mechanisms
enum CurveType {
    POWER,          // Power curve: P(S) = k * S^p (configurable exponent)
    LINEAR,         // Linear curve: P(S) = k * S (constant slope)
    EXPONENTIAL,    // Exponential spike: P(S) = k * (e^(a*S) - 1) (starts slow, spikes up)
    DECELERATING,   // Decelerating curve: P(S) = k * sqrt(S) or k * log(S+1) (starts fast, becomes stable)
    TIERED          // Tiered curve: linear increase -> flatline -> linear increase at thresholds
}
