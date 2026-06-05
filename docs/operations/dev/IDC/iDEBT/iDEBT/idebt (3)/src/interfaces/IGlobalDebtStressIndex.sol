// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IDebtOracle } from "./IDebtOracle.sol";

/// @title IGlobalDebtStressIndex
/// @notice Aggregated stress score 0..1e18 with structural breakdown.
interface IGlobalDebtStressIndex {
    /// @notice Stress regime emitted when the index crosses thresholds.
    enum Regime { Calm, Elevated, Distress, Crisis, Default }

    struct Snapshot {
        uint256 index;       // aggregate 0..1e18
        Regime regime;
        uint64  timestamp;
        uint256 debtGDP;     // component 0..1e18
        uint256 cds;         // component 0..1e18
        uint256 yieldInv;    // component 0..1e18
        uint256 realRate;    // component 0..1e18
        uint256 dxy;         // component 0..1e18
        uint256 vix;         // component 0..1e18
        uint256 gold;        // component 0..1e18
    }

    event IndexUpdated(uint256 index, Regime regime, uint64 timestamp);
    event RegimeTransition(Regime from, Regime to, uint64 timestamp);
    event WeightsUpdated(uint256[7] weights);

    error InvalidWeights();
    error FrozenOracle(IDebtOracle.Metric metric);

    /// @notice Latest stress snapshot.
    function latestSnapshot() external view returns (Snapshot memory);

    /// @notice Pure scalar of the aggregate stress score 0..1e18.
    function score() external view returns (uint256);

    /// @notice Current regime.
    function regime() external view returns (Regime);

    /// @notice Recompute the index from underlying oracles.
    function poke() external returns (Snapshot memory);
}
