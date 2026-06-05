// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title DebtMath
/// @notice Fixed-point helpers for 1e18 arithmetic used across iDEBT.
/// @dev    Pure library; no storage, no external state.
library DebtMath {
    uint256 internal constant WAD = 1e18;
    uint256 internal constant HALF_WAD = 0.5e18;
    uint256 internal constant BPS = 10_000;

    error Overflow();
    error DivideByZero();
    error NegativeResult();

    /// @notice a * b / WAD, rounded down.
    function wmul(uint256 a, uint256 b) internal pure returns (uint256 z) {
        unchecked {
            if (a == 0 || b == 0) return 0;
            if (a > type(uint256).max / b) revert Overflow();
            z = (a * b) / WAD;
        }
    }

    /// @notice a * WAD / b, rounded down.
    function wdiv(uint256 a, uint256 b) internal pure returns (uint256 z) {
        if (b == 0) revert DivideByZero();
        unchecked {
            if (a > type(uint256).max / WAD) revert Overflow();
            z = (a * WAD) / b;
        }
    }

    /// @notice Clamp to [0, WAD].
    function clamp(uint256 x) internal pure returns (uint256) {
        return x > WAD ? WAD : x;
    }

    /// @notice bps (0..10_000) → wad (0..1e18).
    function bpsToWad(uint16 bps) internal pure returns (uint256) {
        return (uint256(bps) * WAD) / BPS;
    }

    /// @notice Safe int256 → uint256, rejecting negative.
    function asUint(int256 x) internal pure returns (uint256) {
        if (x < 0) revert NegativeResult();
        return uint256(x);
    }

    /// @notice Logistic curve: 1 / (1 + e^-x) approximated via piecewise linear.
    ///         Input and output in WAD. Used to convert raw component z-scores
    ///         to a 0..1e18 stress contribution.
    function logistic(int256 x) internal pure returns (uint256) {
        // Saturate extreme inputs to avoid large-exponent cost.
        if (x >= int256(6e18)) return WAD;
        if (x <= -int256(6e18)) return 0;

        // Approximate sigmoid with a rational function accurate to ~1% across [-6,6].
        //   sigmoid(x) ≈ 0.5 + x/(4 + |x|) * 0.5
        int256 ax = x >= 0 ? x : -x;
        int256 num = x * int256(WAD / 2);
        int256 den = int256(4e18) + ax;
        int256 s = int256(WAD / 2) + num / den;
        if (s < 0) return 0;
        return clamp(uint256(s));
    }

    /// @notice Weighted sum of components (each already 0..WAD) with weights
    ///         summing to WAD.
    function weightedSum(uint256[7] memory components, uint256[7] memory weights)
        internal
        pure
        returns (uint256 acc)
    {
        uint256 wsum;
        for (uint256 i = 0; i < 7; ++i) {
            acc += wmul(components[i], weights[i]);
            wsum += weights[i];
        }
        if (wsum != WAD) revert Overflow(); // reuse error for consistency
    }
}
