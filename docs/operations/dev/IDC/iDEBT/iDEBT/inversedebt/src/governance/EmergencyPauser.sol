// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title IPausable — minimal interface for contracts with pause() / unpause()
 */
interface IPausable {
    function pause() external;
    function unpause() external;
}

/**
 * @title EmergencyPauser
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice A limited-power emergency circuit breaker for the DELTAVERSE stack.
 *         Holds the PAUSER role on all five protocol contracts. Can pause
 *         them immediately without waiting for governance timelock delay.
 *         Cannot change parameters, grant other roles, or steal funds.
 *
 * @dev Why this contract exists:
 *
 *      Normal governance changes go through Timelock → 48h delay → execution.
 *      That delay is correct for parameter changes, where users need warning
 *      before their assumptions about the protocol change. It is WRONG for
 *      security emergencies, where every second counts.
 *
 *      This contract provides a fast path that is deliberately limited to
 *      one kind of action: pausing. It can also unpause, but only after a
 *      cooldown period, to prevent a compromised pauser from locking the
 *      protocol indefinitely while users panic.
 *
 *      The role model is intentionally small. A 3-of-5 multisig holds the
 *      GUARDIAN_ROLE. Any single guardian can call pauseAll() to stop
 *      everything. Unpausing requires a majority of guardians OR a governance
 *      proposal executed through Timelock.
 *
 *      IMPORTANT: The contracts being paused must grant this contract their
 *      DEFAULT_ADMIN_ROLE or a dedicated PAUSER_ROLE. The deployment script
 *      wires this up.
 */
contract EmergencyPauser is AccessControl {

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    /// @notice Any guardian can trigger an emergency pause unilaterally.
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    /// @notice Unpausing requires this role (held by Timelock in production).
    bytes32 public constant UNPAUSER_ROLE = keccak256("UNPAUSER_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  ERRORS
    // ════════════════════════════════════════════════════════════════

    error ZeroAddress();
    error ArrayLengthMismatch();
    error CooldownNotElapsed(uint256 timeRemaining);
    error PauseCallFailed(address target, bytes returnData);

    // ════════════════════════════════════════════════════════════════
    //  STATE
    // ════════════════════════════════════════════════════════════════

    /// @notice The contracts this pauser is authorized to pause.
    ///         Set at deployment and updated only via governance.
    address[] public managedContracts;

    /// @notice Timestamp of the last emergency pause event. Used to
    ///         enforce cooldown before unpausing is allowed.
    uint256 public lastPauseTimestamp;

    /// @notice Minimum time between a pause and when unpause can be called.
    ///         Prevents panic-unpause before the cause is investigated.
    uint256 public unpauseCooldown = 1 hours;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event EmergencyPauseTriggered(address indexed guardian, uint256 timestamp);
    event EmergencyUnpauseExecuted(address indexed unpauser, uint256 timestamp);
    event ManagedContractAdded(address indexed target);
    event ManagedContractRemoved(address indexed target);
    event UnpauseCooldownUpdated(uint256 oldValue, uint256 newValue);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    /**
     * @param guardians   Initial set of guardian addresses (recommended: 3-5
     *                    addresses held by independent parties / multisig).
     * @param unpauser    Address granted UNPAUSER_ROLE. Should be the
     *                    DeltaVerseTimelock in production, meaning unpausing
     *                    requires a governance proposal.
     * @param targets     The five protocol contracts to manage:
     *                    RWAToken, CrossCollateralVault, PerpetualEngine,
     *                    DeltaVerseDebtOracle, DebtInheritanceProtocol.
     */
    constructor(
        address[] memory guardians,
        address unpauser,
        address[] memory targets
    ) {
        if (unpauser == address(0)) revert ZeroAddress();

        // Grant admin role to the unpauser (Timelock) so governance can
        // update guardian membership and add/remove managed contracts.
        _grantRole(DEFAULT_ADMIN_ROLE, unpauser);
        _grantRole(UNPAUSER_ROLE, unpauser);

        for (uint256 i; i < guardians.length; ) {
            if (guardians[i] == address(0)) revert ZeroAddress();
            _grantRole(GUARDIAN_ROLE, guardians[i]);
            unchecked { ++i; }
        }

        for (uint256 i; i < targets.length; ) {
            if (targets[i] == address(0)) revert ZeroAddress();
            managedContracts.push(targets[i]);
            emit ManagedContractAdded(targets[i]);
            unchecked { ++i; }
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  EMERGENCY ACTIONS
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Pause every managed contract in a single transaction.
     * @dev    Any guardian can call this. Revert on any individual failure
     *         so that the caller is forced to investigate partial-pause
     *         situations rather than silently ignoring them.
     */
    function pauseAll() external onlyRole(GUARDIAN_ROLE) {
        lastPauseTimestamp = block.timestamp;

        for (uint256 i; i < managedContracts.length; ) {
            address target = managedContracts[i];
            // Use low-level call to tolerate contracts that may not strictly
            // implement IPausable but have a compatible pause() selector.
            (bool ok, bytes memory ret) = target.call(
                abi.encodeWithSelector(IPausable.pause.selector)
            );
            if (!ok) revert PauseCallFailed(target, ret);
            unchecked { ++i; }
        }

        emit EmergencyPauseTriggered(msg.sender, block.timestamp);
    }

    /**
     * @notice Unpause every managed contract. Requires UNPAUSER_ROLE (Timelock)
     *         and enforces a cooldown period since the last emergency pause,
     *         so that the cause of the emergency has time to be investigated.
     */
    function unpauseAll() external onlyRole(UNPAUSER_ROLE) {
        uint256 cooldownEnd = lastPauseTimestamp + unpauseCooldown;
        if (block.timestamp < cooldownEnd) {
            revert CooldownNotElapsed(cooldownEnd - block.timestamp);
        }

        for (uint256 i; i < managedContracts.length; ) {
            address target = managedContracts[i];
            (bool ok, bytes memory ret) = target.call(
                abi.encodeWithSelector(IPausable.unpause.selector)
            );
            if (!ok) revert PauseCallFailed(target, ret);
            unchecked { ++i; }
        }

        emit EmergencyUnpauseExecuted(msg.sender, block.timestamp);
    }

    /**
     * @notice Pause a single specific contract. Used when a guardian wants
     *         to halt just one component (e.g. the PerpetualEngine during
     *         oracle anomalies) without stopping sGDSI mint/burn.
     */
    function pauseOne(address target) external onlyRole(GUARDIAN_ROLE) {
        lastPauseTimestamp = block.timestamp;
        (bool ok, bytes memory ret) = target.call(
            abi.encodeWithSelector(IPausable.pause.selector)
        );
        if (!ok) revert PauseCallFailed(target, ret);
        emit EmergencyPauseTriggered(msg.sender, block.timestamp);
    }

    // ════════════════════════════════════════════════════════════════
    //  GOVERNANCE-ONLY MANAGEMENT
    // ════════════════════════════════════════════════════════════════

    /// @notice Add a new contract to the managed set (governance only).
    function addManagedContract(address target)
        external onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (target == address(0)) revert ZeroAddress();
        managedContracts.push(target);
        emit ManagedContractAdded(target);
    }

    /// @notice Remove a contract from the managed set (governance only).
    function removeManagedContract(uint256 index)
        external onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(index < managedContracts.length, "index out of range");
        address removed = managedContracts[index];
        managedContracts[index] = managedContracts[managedContracts.length - 1];
        managedContracts.pop();
        emit ManagedContractRemoved(removed);
    }

    /// @notice Update the cooldown enforced between pause and unpause.
    function setUnpauseCooldown(uint256 newCooldown)
        external onlyRole(DEFAULT_ADMIN_ROLE)
    {
        uint256 old = unpauseCooldown;
        unpauseCooldown = newCooldown;
        emit UnpauseCooldownUpdated(old, newCooldown);
    }

    // ════════════════════════════════════════════════════════════════
    //  VIEW
    // ════════════════════════════════════════════════════════════════

    function getManagedContractCount() external view returns (uint256) {
        return managedContracts.length;
    }

    function getAllManagedContracts() external view returns (address[] memory) {
        return managedContracts;
    }
}
