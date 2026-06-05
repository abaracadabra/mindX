// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title DeltaVerseTimelock
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Production timelock controller that holds DEFAULT_ADMIN_ROLE across
 *         the entire DELTAVERSE Debt Inheritance Protocol stack.
 *
 * @dev This contract is a thin wrapper around OpenZeppelin's TimelockController
 *      with no additional logic. Its purpose is solely to provide a named,
 *      auditable artifact that clearly represents "the timelock of this protocol"
 *      in block explorers and governance interfaces.
 *
 *      The TimelockController enforces a mandatory minimum delay between when
 *      a governance action is scheduled and when it can be executed. Any call
 *      that modifies protocol parameters (changing oracle heartbeat, adjusting
 *      fees, pausing, granting roles, etc.) must flow through this contract
 *      and wait for the delay to elapse before taking effect.
 *
 *      ROLE MODEL:
 *      - PROPOSER_ROLE:  Held by the DeltaVerseGovernor contract.
 *                        Only the Governor can schedule operations.
 *      - EXECUTOR_ROLE:  Held by address(0) which means "anyone".
 *                        This is safe because operations can only execute
 *                        after the delay and only if they were scheduled
 *                        by a proposer.
 *      - CANCELLER_ROLE: Held by a small emergency multisig. If a malicious
 *                        proposal somehow passes, the multisig can cancel
 *                        it before execution.
 *      - TIMELOCK_ADMIN: Held by the Timelock itself (self-administered).
 *                        No external admin can bypass the delay.
 *
 *      RECOMMENDED DELAY:
 *      - 48 hours for routine parameter changes
 *      - Longer delays (7 days) can be enforced at the Governor level
 *        for high-impact changes by requiring higher quorum/vote thresholds.
 *
 *      DEPLOYMENT SEQUENCE:
 *      1. Deploy DeltaVerseTimelock with initial proposer = deployer
 *         (this is a bootstrap proposer; it will be revoked after Governor exists)
 *      2. Deploy DeltaVerseGovernor with this timelock's address
 *      3. Grant PROPOSER_ROLE to the Governor
 *      4. Revoke PROPOSER_ROLE from the deployer
 *      5. Renounce TIMELOCK_ADMIN_ROLE from the deployer
 *      6. Transfer DEFAULT_ADMIN_ROLE of each of the 5 stack contracts to
 *         this Timelock contract
 */
contract DeltaVerseTimelock is TimelockController {
    /**
     * @param minDelay    Minimum delay in seconds before a scheduled operation
     *                    can be executed. Recommended: 172800 (48 hours).
     * @param proposers   Addresses granted PROPOSER_ROLE. In production, this
     *                    should contain only the deployer as a bootstrap; the
     *                    Governor contract will be granted PROPOSER_ROLE after
     *                    its deployment, and the deployer's proposer role
     *                    will be revoked.
     * @param executors   Addresses granted EXECUTOR_ROLE. Pass [address(0)] to
     *                    allow anyone to execute scheduled operations after
     *                    the delay has elapsed. This is the recommended setting
     *                    because it removes censorship risk.
     * @param admin       Initial admin. Should be the deployer for bootstrap,
     *                    then renounced. Pass address(0) to have the Timelock
     *                    self-administer from construction (safer but requires
     *                    the Governor to be deployed atomically).
     */
    constructor(
        uint256 minDelay,
        address[] memory proposers,
        address[] memory executors,
        address admin
    )
        TimelockController(minDelay, proposers, executors, admin)
    {}
}
