// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title  OpenBDKTimelock — the OVERLORD governance delay
 * @author Professor Codephreak / openBDK
 * @notice A named OZ TimelockController. After deployment the bridge/allocation
 *         contracts hand their admin to THIS timelock (the OVERLORD), so every
 *         privileged action is queued for `minDelay` and publicly visible before
 *         it can execute. The OWNER wallet is the sole proposer/executor — the
 *         software/deploy key holds nothing.
 *
 * @dev    proposers == executors == [owner] is the canonical "single human owner
 *         behind a transparency delay" topology. Pass address(0) admin so the
 *         timelock self-administers (no external admin backdoor).
 */
contract OpenBDKTimelock is TimelockController {
    constructor(uint256 minDelay, address owner)
        TimelockController(minDelay, _solo(owner), _solo(owner), address(0))
    {}

    function _solo(address a) private pure returns (address[] memory arr) {
        arr = new address[](1);
        arr[0] = a;
    }
}
