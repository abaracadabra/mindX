// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IDebtOracle } from "../interfaces/IDebtOracle.sol";

interface IAggregatorV3 {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function latestRoundData() external view returns (
        uint80  roundId,
        int256  answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80  answeredInRound
    );
}

/// @title ChainlinkAdapter
/// @notice Minimal read-only adapter that turns a Chainlink aggregator into an
///         IDebtOracle.Observation. Deployed once per feed; registered to the
///         DeltaVerseDebtOracle per Metric.
contract ChainlinkAdapter {
    IAggregatorV3 public immutable feed;
    bytes32       public immutable sourceId;
    uint8         public immutable feedDecimals;
    uint64        public immutable heartbeat; // max staleness per feed spec

    error StaleFeed(uint256 updatedAt, uint256 maxAge);
    error InvalidAnswer();

    constructor(address feed_, bytes32 sourceId_, uint64 heartbeat_) {
        feed = IAggregatorV3(feed_);
        sourceId = sourceId_;
        feedDecimals = IAggregatorV3(feed_).decimals();
        heartbeat = heartbeat_;
    }

    /// @notice Pull the latest observation, scaled to 1e18.
    function latest() external view returns (IDebtOracle.Observation memory obs) {
        (, int256 answer,, uint256 updatedAt,) = feed.latestRoundData();
        if (answer <= 0) revert InvalidAnswer();
        if (block.timestamp - updatedAt > heartbeat) {
            revert StaleFeed(updatedAt, heartbeat);
        }

        // Scale to 1e18.
        int256 scaled;
        if (feedDecimals < 18) {
            scaled = answer * int256(10 ** uint256(18 - feedDecimals));
        } else if (feedDecimals > 18) {
            scaled = answer / int256(10 ** uint256(feedDecimals - 18));
        } else {
            scaled = answer;
        }

        obs = IDebtOracle.Observation({
            value: scaled,
            timestamp: uint64(updatedAt),
            // Confidence: degrade from 1e18 toward 0 as age approaches heartbeat.
            confidence: _confidence(updatedAt),
            source: sourceId
        });
    }

    function _confidence(uint256 updatedAt) internal view returns (uint256) {
        uint256 age = block.timestamp - updatedAt;
        if (age >= heartbeat) return 0;
        return 1e18 - (age * 1e18) / heartbeat;
    }
}
