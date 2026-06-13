// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IDebtOracle } from "../interfaces/IDebtOracle.sol";

/// @dev Minimal Synthetix V3 Core proxy surface used here.
interface ISynthetixV3Core {
    function getMarketTotalDebt(uint128 marketId) external view returns (int256);
    function getMarketCollateral(uint128 marketId) external view returns (uint256);
    function getMarketDebtPerShare(uint128 marketId) external view returns (int256);
}

/// @title SynthetixV3Adapter
/// @notice Surfaces the aggregate debt/collateral ratio of a Synthetix V3 market
///         as a stress signal. The adapter does NOT take any custody — it is a
///         view-only transform of canonical Synthetix V3 state into an
///         IDebtOracle.Observation.
contract SynthetixV3Adapter {
    ISynthetixV3Core public immutable core;
    uint128          public immutable marketId;
    bytes32          public immutable sourceId;

    error NoCollateral();

    constructor(address core_, uint128 marketId_, bytes32 sourceId_) {
        core = ISynthetixV3Core(core_);
        marketId = marketId_;
        sourceId = sourceId_;
    }

    /// @notice Latest observation: debt-to-collateral ratio scaled to 1e18.
    ///         Positive values indicate debt > 0; negative indicate net surplus.
    function latest() external view returns (IDebtOracle.Observation memory obs) {
        int256 debt = core.getMarketTotalDebt(marketId);
        uint256 coll = core.getMarketCollateral(marketId);
        if (coll == 0) revert NoCollateral();

        int256 ratio = (debt * int256(1e18)) / int256(coll);

        obs = IDebtOracle.Observation({
            value: ratio,
            timestamp: uint64(block.timestamp),
            confidence: 1e18,
            source: sourceId
        });
    }
}
