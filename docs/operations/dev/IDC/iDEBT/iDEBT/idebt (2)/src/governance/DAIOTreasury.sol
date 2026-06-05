// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { TimelockController } from "@openzeppelin/contracts/governance/TimelockController.sol";

/// @title DAIOTreasury
/// @notice Thin wrapper around OZ TimelockController used as both:
///           - the executor for DAIO proposals, and
///           - the sink/holder of protocol fees and the iDEBT reserve.
/// @dev    Separate from the Governor so voting and execution have distinct
///         trust boundaries.
contract DAIOTreasury is TimelockController {
    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors,
        address admin
    ) TimelockController(minDelay, proposers, executors, admin) {}

    // OZ v5 TimelockController already defines `receive()` and `fallback()`;
    // we inherit them. No overrides required.
}
