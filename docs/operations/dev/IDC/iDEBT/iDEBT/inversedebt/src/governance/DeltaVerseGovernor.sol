// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/governance/Governor.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorSettings.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorVotesQuorumFraction.sol";
import "@openzeppelin/contracts/governance/extensions/GovernorTimelockControl.sol";
import "@openzeppelin/contracts/governance/utils/IVotes.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title DeltaVerseGovernor
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Token-weighted governance contract for the Debt Inheritance Protocol.
 *         Accepts proposals from holders above the proposal threshold, runs
 *         token-weighted voting with a configurable quorum, and if a proposal
 *         passes, queues it in the DeltaVerseTimelock for delayed execution.
 *
 * @dev This contract composes five OpenZeppelin Governor extensions:
 *
 *      1. GovernorSettings — stores votingDelay, votingPeriod, proposalThreshold
 *         as mutable state that can be changed through governance itself.
 *
 *      2. GovernorCountingSimple — implements Against/For/Abstain vote counting.
 *         Simple majority of (For) vs (For + Against) wins if quorum is met.
 *         Abstain votes count toward quorum but not toward the outcome.
 *
 *      3. GovernorVotes — reads voting power from an IVotes token (any
 *         ERC20Votes token works: THRUST, PAIMINT, or a future DELTAVERSE
 *         governance token). Voting power is measured as of the proposal
 *         snapshot, not current balance, which prevents flash-loan governance
 *         attacks.
 *
 *      4. GovernorVotesQuorumFraction — defines quorum as a fraction of total
 *         token supply at the snapshot block. Initial quorum is 4% which is
 *         the Compound/Uniswap standard.
 *
 *      5. GovernorTimelockControl — routes passed proposals through the
 *         DeltaVerseTimelock for delayed execution. Adds a queue() step
 *         between voting end and execution.
 *
 *      LIFECYCLE OF A PROPOSAL:
 *      Phase 1: Pending — created by propose(), waits votingDelay blocks
 *      Phase 2: Active — voting window is open for votingPeriod blocks
 *      Phase 3: Succeeded — vote ended with quorum met and For > Against
 *      Phase 4: Queued — proposal scheduled in Timelock with minDelay
 *      Phase 5: Executed — anyone can call execute() after Timelock delay
 *
 *      RECOMMENDED PRODUCTION PARAMETERS:
 *      - votingDelay: 1 day (time between propose and voting start)
 *      - votingPeriod: 1 week (time during which votes can be cast)
 *      - proposalThreshold: 0.1% of token supply (e.g. 100k of 100M)
 *      - quorumFraction: 4% of token supply
 *      - timelock minDelay: 48 hours
 *
 *      These values create a roughly 10-day end-to-end governance cycle,
 *      which is long enough to allow informed participation and short enough
 *      to respond to changing conditions.
 */
contract DeltaVerseGovernor is
    Governor,
    GovernorSettings,
    GovernorCountingSimple,
    GovernorVotes,
    GovernorVotesQuorumFraction,
    GovernorTimelockControl
{
    /**
     * @param token     The governance token (must implement IVotes).
     *                  Recommended: THRUST, PAIMINT, or a purpose-built
     *                  ERC20Votes token for the protocol.
     * @param timelock  The DeltaVerseTimelock that will queue passed proposals.
     */
    constructor(IVotes token, TimelockController timelock)
        Governor("DeltaVerseGovernor")
        // GovernorSettings(votingDelay, votingPeriod, proposalThreshold)
        // 7200 blocks ~= 1 day at 12s/block on mainnet
        // 50400 blocks ~= 1 week
        // 100_000e18 proposal threshold (adjust to token decimals)
        GovernorSettings(7200, 50400, 100_000e18)
        GovernorVotes(token)
        // 4% quorum — Compound/Uniswap standard
        GovernorVotesQuorumFraction(4)
        GovernorTimelockControl(timelock)
    {}

    // ════════════════════════════════════════════════════════════════
    //  REQUIRED OVERRIDES
    // ════════════════════════════════════════════════════════════════
    //
    //  Because we inherit from multiple Governor extensions that implement
    //  the same virtual functions, Solidity requires us to explicitly
    //  override each one and specify the inheritance order. These are not
    //  custom logic — they simply delegate to the inherited implementations
    //  in the correct order.

    function votingDelay()
        public view override(Governor, GovernorSettings) returns (uint256)
    {
        return super.votingDelay();
    }

    function votingPeriod()
        public view override(Governor, GovernorSettings) returns (uint256)
    {
        return super.votingPeriod();
    }

    function quorum(uint256 blockNumber)
        public view override(Governor, GovernorVotesQuorumFraction) returns (uint256)
    {
        return super.quorum(blockNumber);
    }

    function state(uint256 proposalId)
        public view override(Governor, GovernorTimelockControl) returns (ProposalState)
    {
        return super.state(proposalId);
    }

    function proposalNeedsQueuing(uint256 proposalId)
        public view override(Governor, GovernorTimelockControl) returns (bool)
    {
        return super.proposalNeedsQueuing(proposalId);
    }

    function proposalThreshold()
        public view override(Governor, GovernorSettings) returns (uint256)
    {
        return super.proposalThreshold();
    }

    function _queueOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
        returns (uint48)
    {
        return super._queueOperations(
            proposalId, targets, values, calldatas, descriptionHash
        );
    }

    function _executeOperations(
        uint256 proposalId,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
    {
        super._executeOperations(
            proposalId, targets, values, calldatas, descriptionHash
        );
    }

    function _cancel(
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas,
        bytes32 descriptionHash
    )
        internal
        override(Governor, GovernorTimelockControl)
        returns (uint256)
    {
        return super._cancel(targets, values, calldatas, descriptionHash);
    }

    function _executor()
        internal view override(Governor, GovernorTimelockControl) returns (address)
    {
        return super._executor();
    }
}
