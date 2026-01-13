// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title DAIOTimelock
 * @notice Timelock controller wrapper for DAIO governance
 * @dev Provides time-delayed execution for governance proposals
 */
contract DAIOTimelock is TimelockController {
    constructor(
        uint256 _minDelay,      // Minimum delay before execution (seconds)
        address[] memory proposers,  // Addresses allowed to propose
        address[] memory executors,  // Addresses allowed to execute
        address admin            // Admin address (can be address(0) for self-administered)
    ) TimelockController(_minDelay, proposers, executors, admin) {
        require(proposers.length > 0, "No proposers");
        require(executors.length > 0, "No executors");
    }
}
