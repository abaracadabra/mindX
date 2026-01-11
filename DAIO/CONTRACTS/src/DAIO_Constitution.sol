// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title DAIO_Constitution
 * @dev Primary governance contract enforcing constitutional constraints for the DAIO ecosystem.
 *
 * Constitutional Principles:
 * 1. Code is Law - All operations must pass validation
 * 2. 15% Diversification Mandate - Treasury diversification requirement
 * 3. Chairman's Veto - Emergency pause capability
 * 4. Immutable Tithe - 15% of profits to treasury
 */
contract DAIO_Constitution is AccessControl, ReentrancyGuard, Pausable {
    // Roles
    bytes32 public constant CHAIRMAN_ROLE = keccak256("CHAIRMAN_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");

    // Constitutional Constants
    uint256 public constant DIVERSIFICATION_MANDATE = 1500; // 15% in basis points
    uint256 public constant TREASURY_TITHE = 1500; // 15% in basis points
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public constant VOTING_QUORUM = 6667; // 66.67% in basis points

    // Action Types for validation
    enum ActionType {
        TreasuryAllocation,
        AgentCreation,
        AgentDestruction,
        GovernanceProposal,
        EmergencyAction,
        TokenTransfer
    }

    // Action structure for validation
    struct ConstitutionalAction {
        ActionType actionType;
        address initiator;
        address target;
        uint256 value;
        bytes data;
        uint256 timestamp;
        bool validated;
    }

    // Treasury tracking for diversification
    struct TreasuryState {
        uint256 totalValue;
        uint256 diversifiedValue;
        uint256 lastUpdateTime;
    }

    // State
    mapping(bytes32 => ConstitutionalAction) public actions;
    mapping(bytes32 => bool) public executedActions;
    TreasuryState public treasuryState;

    uint256 public emergencyActionCount;
    uint256 public lastEmergencyAction;

    // Events
    event ActionValidated(bytes32 indexed actionId, ActionType actionType, address initiator);
    event ActionExecuted(bytes32 indexed actionId, ActionType actionType);
    event ActionRejected(bytes32 indexed actionId, string reason);
    event ConstitutionalViolation(bytes32 indexed actionId, string violation);
    event ChairmanVetoActivated(address indexed chairman, string reason);
    event ChairmanVetoDeactivated(address indexed chairman);
    event TreasuryStateUpdated(uint256 totalValue, uint256 diversifiedValue);
    event TitheCollected(uint256 amount, address indexed from);

    // Errors
    error DiversificationViolation(uint256 required, uint256 actual);
    error TitheViolation(uint256 required, uint256 actual);
    error ActionAlreadyExecuted(bytes32 actionId);
    error ActionNotValidated(bytes32 actionId);
    error InvalidActionType();
    error Unauthorized();

    constructor(address _chairman, address _governance) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CHAIRMAN_ROLE, _chairman);
        _grantRole(GOVERNANCE_ROLE, _governance);
        _grantRole(VALIDATOR_ROLE, msg.sender);
    }

    // ============ Core Constitutional Functions ============

    /**
     * @dev Validates an action against constitutional rules
     * @param actionType Type of action being validated
     * @param initiator Address initiating the action
     * @param target Target address of the action
     * @param value Value involved in the action
     * @param data Additional action data
     * @return actionId Unique identifier for the validated action
     */
    function validateAction(
        ActionType actionType,
        address initiator,
        address target,
        uint256 value,
        bytes calldata data
    ) external onlyRole(VALIDATOR_ROLE) whenNotPaused returns (bytes32 actionId) {
        actionId = keccak256(abi.encodePacked(
            actionType,
            initiator,
            target,
            value,
            data,
            block.timestamp,
            block.number
        ));

        require(!executedActions[actionId], "Action already processed");

        // Validate based on action type
        bool isValid = _validateByType(actionType, initiator, target, value, data);

        if (!isValid) {
            emit ActionRejected(actionId, "Constitutional validation failed");
            revert InvalidActionType();
        }

        actions[actionId] = ConstitutionalAction({
            actionType: actionType,
            initiator: initiator,
            target: target,
            value: value,
            data: data,
            timestamp: block.timestamp,
            validated: true
        });

        emit ActionValidated(actionId, actionType, initiator);
        return actionId;
    }

    /**
     * @dev Checks if treasury diversification mandate is met
     * @return compliant Whether the diversification mandate is satisfied
     */
    function checkDiversificationLimit() public view returns (bool compliant) {
        if (treasuryState.totalValue == 0) return true;

        uint256 requiredDiversification = (treasuryState.totalValue * DIVERSIFICATION_MANDATE) / BASIS_POINTS;
        return treasuryState.diversifiedValue >= requiredDiversification;
    }

    /**
     * @dev Calculates the required tithe amount
     * @param profit The profit amount to calculate tithe from
     * @return titheAmount The required tithe
     */
    function calculateTithe(uint256 profit) public pure returns (uint256 titheAmount) {
        return (profit * TREASURY_TITHE) / BASIS_POINTS;
    }

    /**
     * @dev Validates tithe payment
     * @param profit The profit being distributed
     * @param titheProvided The tithe amount provided
     * @return valid Whether the tithe is sufficient
     */
    function validateTithe(uint256 profit, uint256 titheProvided) public pure returns (bool valid) {
        uint256 required = calculateTithe(profit);
        return titheProvided >= required;
    }

    // ============ Chairman's Veto (Emergency Controls) ============

    /**
     * @dev Activates emergency pause - Chairman's Veto
     * @param reason Reason for the emergency pause
     */
    function pauseSystem(string calldata reason) external onlyRole(CHAIRMAN_ROLE) {
        _pause();
        emergencyActionCount++;
        lastEmergencyAction = block.timestamp;
        emit ChairmanVetoActivated(msg.sender, reason);
    }

    /**
     * @dev Deactivates emergency pause
     */
    function unpauseSystem() external onlyRole(CHAIRMAN_ROLE) {
        _unpause();
        emit ChairmanVetoDeactivated(msg.sender);
    }

    // ============ Treasury State Management ============

    /**
     * @dev Updates treasury state for diversification tracking
     * @param totalValue Current total treasury value
     * @param diversifiedValue Current diversified asset value
     */
    function updateTreasuryState(
        uint256 totalValue,
        uint256 diversifiedValue
    ) external onlyRole(GOVERNANCE_ROLE) {
        treasuryState = TreasuryState({
            totalValue: totalValue,
            diversifiedValue: diversifiedValue,
            lastUpdateTime: block.timestamp
        });

        emit TreasuryStateUpdated(totalValue, diversifiedValue);

        // Check diversification mandate
        if (!checkDiversificationLimit()) {
            emit ConstitutionalViolation(
                bytes32(0),
                "Diversification mandate not met"
            );
        }
    }

    /**
     * @dev Records tithe collection
     * @param amount Tithe amount collected
     * @param from Source of the tithe
     */
    function recordTithe(uint256 amount, address from) external onlyRole(GOVERNANCE_ROLE) {
        emit TitheCollected(amount, from);
    }

    // ============ Action Execution ============

    /**
     * @dev Marks an action as executed
     * @param actionId The action to mark as executed
     */
    function markActionExecuted(bytes32 actionId) external onlyRole(GOVERNANCE_ROLE) {
        require(actions[actionId].validated, "Action not validated");
        require(!executedActions[actionId], "Already executed");

        executedActions[actionId] = true;
        emit ActionExecuted(actionId, actions[actionId].actionType);
    }

    // ============ View Functions ============

    /**
     * @dev Gets action details
     * @param actionId The action ID to query
     */
    function getAction(bytes32 actionId) external view returns (ConstitutionalAction memory) {
        return actions[actionId];
    }

    /**
     * @dev Checks if an action is validated and not executed
     * @param actionId The action ID to check
     */
    function isActionPending(bytes32 actionId) external view returns (bool) {
        return actions[actionId].validated && !executedActions[actionId];
    }

    /**
     * @dev Gets current treasury compliance status
     */
    function getTreasuryCompliance() external view returns (
        bool diversificationCompliant,
        uint256 totalValue,
        uint256 diversifiedValue,
        uint256 requiredDiversification
    ) {
        diversificationCompliant = checkDiversificationLimit();
        totalValue = treasuryState.totalValue;
        diversifiedValue = treasuryState.diversifiedValue;
        requiredDiversification = (totalValue * DIVERSIFICATION_MANDATE) / BASIS_POINTS;
    }

    // ============ Internal Functions ============

    /**
     * @dev Internal validation logic based on action type
     */
    function _validateByType(
        ActionType actionType,
        address initiator,
        address target,
        uint256 value,
        bytes calldata data
    ) internal view returns (bool) {
        if (actionType == ActionType.TreasuryAllocation) {
            // Validate treasury allocation doesn't violate diversification
            return _validateTreasuryAllocation(value);
        } else if (actionType == ActionType.AgentCreation) {
            // Validate agent creation requirements
            return _validateAgentCreation(initiator, data);
        } else if (actionType == ActionType.AgentDestruction) {
            // Validate agent destruction
            return _validateAgentDestruction(target);
        } else if (actionType == ActionType.GovernanceProposal) {
            // Validate governance proposal
            return _validateGovernanceProposal(initiator, data);
        } else if (actionType == ActionType.EmergencyAction) {
            // Emergency actions require chairman role
            return hasRole(CHAIRMAN_ROLE, initiator);
        } else if (actionType == ActionType.TokenTransfer) {
            // Validate token transfers
            return _validateTokenTransfer(initiator, target, value);
        }

        return false;
    }

    function _validateTreasuryAllocation(uint256 value) internal view returns (bool) {
        // Ensure allocation doesn't violate diversification mandate
        if (treasuryState.totalValue == 0) return true;

        uint256 newTotal = treasuryState.totalValue > value ?
            treasuryState.totalValue - value : 0;
        uint256 requiredDiversification = (newTotal * DIVERSIFICATION_MANDATE) / BASIS_POINTS;

        return treasuryState.diversifiedValue >= requiredDiversification;
    }

    function _validateAgentCreation(address initiator, bytes calldata) internal view returns (bool) {
        // Only governance can create agents
        return hasRole(GOVERNANCE_ROLE, initiator);
    }

    function _validateAgentDestruction(address) internal pure returns (bool) {
        // Agent destruction validation
        return true; // Governance check happens at higher level
    }

    function _validateGovernanceProposal(address initiator, bytes calldata) internal view returns (bool) {
        // Validate proposal initiator has appropriate role
        return hasRole(GOVERNANCE_ROLE, initiator);
    }

    function _validateTokenTransfer(address, address target, uint256) internal pure returns (bool) {
        // Basic transfer validation
        return target != address(0);
    }
}
