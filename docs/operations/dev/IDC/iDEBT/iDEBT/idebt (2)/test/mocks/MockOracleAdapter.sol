// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IDebtOracle } from "../../src/interfaces/IDebtOracle.sol";

/// @notice Programmable adapter that returns a configured observation.
contract MockOracleAdapter {
    IDebtOracle.Observation public obs;

    function set(int256 value, uint256 confidence, bytes32 source) external {
        obs = IDebtOracle.Observation({
            value:      value,
            timestamp:  uint64(block.timestamp),
            confidence: confidence,
            source:     source
        });
    }

    function setStale(int256 value, uint256 confidence, bytes32 source, uint64 at) external {
        obs = IDebtOracle.Observation({
            value:      value,
            timestamp:  at,
            confidence: confidence,
            source:     source
        });
    }

    function latest() external view returns (IDebtOracle.Observation memory) {
        return obs;
    }
}
