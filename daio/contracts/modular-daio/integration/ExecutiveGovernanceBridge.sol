// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/governance/DAIOGovernance.sol";
import "../../executive-governance/ExecutiveGovernance.sol";
import "../../daio/constitution/DAIO_Constitution.sol";

/**
 * @title ExecutiveGovernanceBridge
 * @dev Bridges existing DAIO governance with CEO + Seven Soldiers executive governance
 *
 * Key Features:
 * - Routes critical proposals to executive approval
 * - Constitutional validation for all actions
 * - Emergency coordination across systems
 * - Complete audit trail aggregation
 */
contract ExecutiveGovernanceBridge is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant BRIDGE_OPERATOR_ROLE = keccak256("BRIDGE_OPERATOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Core system contracts
    DAIOGovernance public immutable daioGovernance;
    ExecutiveGovernance public immutable executiveGovernance;
    DAIO_Constitution public immutable constitution;

    // Proposal routing configuration
    struct ProposalRoute {
        bool requiresExecutiveApproval;
        uint256 executiveThreshold;
        uint256 emergencyDelay;
        bool constitutionalValidation;
        address[] requiredExecutives;
    }

    // Executive approval tracking
    struct ExecutiveApproval {
        uint256 daioProposalId;
        uint256 executiveProposalId;
        bool approved;
        bool executed;
        uint256 approvalTime;
        uint256 expirationTime;
        address[] approvers;
        mapping(address => bool) hasApproved;
    }

    mapping(uint256 => ProposalRoute) public proposalRoutes;
    mapping(uint256 => ExecutiveApproval) public executiveApprovals;
    mapping(bytes4 => bool) public criticalMethods;

    uint256 public nextApprovalId;
    uint256 public defaultExecutiveThreshold = 5; // 5 of 8 executives
    uint256 public emergencyExecutionDelay = 24 hours;

    event ProposalRouted(
        uint256 indexed daioProposalId,
        uint256 indexed executiveProposalId,
        address indexed proposer,
        string proposalType
    );

    event ExecutiveApprovalGranted(
        uint256 indexed approvalId,
        uint256 indexed daioProposalId,
        address indexed approver,
        uint256 timestamp
    );

    event EmergencyExecution(
        uint256 indexed proposalId,
        address indexed executor,
        string reason,
        uint256 timestamp
    );

    event ConstitutionalViolation(
        uint256 indexed proposalId,
        address indexed violator,
        string violation,
        uint256 timestamp
    );

    constructor(
        address _daioGovernance,
        address _executiveGovernance,
        address _constitution,
        address _admin
    ) {
        require(_daioGovernance != address(0), "Invalid DAIO governance");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_constitution != address(0), "Invalid constitution");
        require(_admin != address(0), "Invalid admin");

        daioGovernance = DAIOGovernance(_daioGovernance);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        constitution = DAIO_Constitution(_constitution);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(BRIDGE_OPERATOR_ROLE, _admin);
        _grantRole(EMERGENCY_ROLE, _admin);

        _initializeCriticalMethods();
    }

    /**
     * @dev Initialize critical methods that require executive approval
     */
    function _initializeCriticalMethods() internal {
        // Treasury operations
        criticalMethods[bytes4(keccak256("allocateFunds(address,uint256)"))] = true;
        criticalMethods[bytes4(keccak256("withdrawFromTreasury(address,uint256)"))] = true;
        criticalMethods[bytes4(keccak256("investFunds(address,uint256)"))] = true;

        // Governance changes
        criticalMethods[bytes4(keccak256("updateGovernanceSettings(bytes)"))] = true;
        criticalMethods[bytes4(keccak256("addGovernanceExtension(address)"))] = true;
        criticalMethods[bytes4(keccak256("removeGovernanceExtension(address)"))] = true;

        // Constitutional changes
        criticalMethods[bytes4(keccak256("proposeConstitutionalAmendment(bytes)"))] = true;
        criticalMethods[bytes4(keccak256("updateConstitutionalParameters(bytes)"))] = true;

        // Emergency procedures
        criticalMethods[bytes4(keccak256("activateEmergencyMode()"))] = true;
        criticalMethods[bytes4(keccak256("pauseSystemOperations()"))] = true;
    }

    /**
     * @dev Route proposal from DAIO governance to executive approval if required
     */
    function routeProposal(
        uint256 daioProposalId,
        bytes calldata proposalData,
        string calldata proposalType,
        address[] calldata requiredExecutives
    ) external onlyRole(BRIDGE_OPERATOR_ROLE) nonReentrant whenNotPaused returns (uint256) {
        require(_requiresExecutiveApproval(proposalData), "Proposal does not require executive approval");

        // Validate against constitution
        require(constitution.validateProposal(proposalData), "Constitutional violation");

        // Create executive approval tracking
        uint256 approvalId = nextApprovalId++;
        ExecutiveApproval storage approval = executiveApprovals[approvalId];
        approval.daioProposalId = daioProposalId;
        approval.approved = false;
        approval.executed = false;
        approval.approvalTime = 0;
        approval.expirationTime = block.timestamp + 30 days;
        approval.approvers = new address[](0);

        // Submit to executive governance
        uint256 executiveProposalId = executiveGovernance.submitProposal(
            proposalData,
            proposalType,
            requiredExecutives,
            defaultExecutiveThreshold
        );

        approval.executiveProposalId = executiveProposalId;

        // Configure routing
        proposalRoutes[daioProposalId] = ProposalRoute({
            requiresExecutiveApproval: true,
            executiveThreshold: defaultExecutiveThreshold,
            emergencyDelay: emergencyExecutionDelay,
            constitutionalValidation: true,
            requiredExecutives: requiredExecutives
        });

        emit ProposalRouted(daioProposalId, executiveProposalId, msg.sender, proposalType);
        return approvalId;
    }

    /**
     * @dev Executive approves a routed proposal
     */
    function approveProposal(
        uint256 approvalId
    ) external nonReentrant whenNotPaused {
        ExecutiveApproval storage approval = executiveApprovals[approvalId];
        require(approval.daioProposalId > 0, "Invalid approval ID");
        require(!approval.hasApproved[msg.sender], "Already approved");
        require(block.timestamp <= approval.expirationTime, "Approval expired");

        // Verify executive role
        require(executiveGovernance.hasExecutiveRole(msg.sender), "Not an executive");

        approval.hasApproved[msg.sender] = true;
        approval.approvers.push(msg.sender);

        // Check if threshold reached
        if (approval.approvers.length >= defaultExecutiveThreshold) {
            approval.approved = true;
            approval.approvalTime = block.timestamp;

            // Execute on DAIO governance if approved
            daioGovernance.executeProposal(approval.daioProposalId);
            approval.executed = true;
        }

        emit ExecutiveApprovalGranted(approvalId, approval.daioProposalId, msg.sender, block.timestamp);
    }

    /**
     * @dev Emergency execution by CEO with constitutional constraints
     */
    function emergencyExecute(
        uint256 daioProposalId,
        string calldata reason
    ) external onlyRole(EMERGENCY_ROLE) nonReentrant {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can emergency execute");

        // Constitutional emergency validation
        require(constitution.validateEmergencyAction(msg.sender, reason), "Emergency action rejected");

        // Execute immediately
        daioGovernance.executeProposal(daioProposalId);

        emit EmergencyExecution(daioProposalId, msg.sender, reason, block.timestamp);
    }

    /**
     * @dev Check if proposal data requires executive approval
     */
    function _requiresExecutiveApproval(bytes calldata proposalData) internal view returns (bool) {
        if (proposalData.length < 4) return false;

        bytes4 methodSig = bytes4(proposalData[:4]);
        return criticalMethods[methodSig];
    }

    /**
     * @dev Aggregate audit data from all systems
     */
    function getAuditData(
        uint256 fromBlock,
        uint256 toBlock
    ) external view returns (
        bytes[] memory daioEvents,
        bytes[] memory executiveEvents,
        bytes[] memory bridgeEvents
    ) {
        // Aggregate events from all systems for compliance reporting
        // Implementation would query event logs from each system

        return (new bytes[](0), new bytes[](0), new bytes[](0));
    }

    /**
     * @dev Constitutional compliance check
     */
    function validateConstitutionalCompliance(
        address target,
        bytes calldata data,
        uint256 value
    ) external view returns (bool, string memory) {
        return constitution.validateAction(target, data, value);
    }

    /**
     * @dev Update executive approval threshold
     */
    function updateExecutiveThreshold(
        uint256 newThreshold
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newThreshold >= 3 && newThreshold <= 8, "Invalid threshold");
        defaultExecutiveThreshold = newThreshold;
    }

    /**
     * @dev Add critical method that requires executive approval
     */
    function addCriticalMethod(
        bytes4 methodSig
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        criticalMethods[methodSig] = true;
    }

    /**
     * @dev Remove critical method
     */
    function removeCriticalMethod(
        bytes4 methodSig
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        criticalMethods[methodSig] = false;
    }

    /**
     * @dev Emergency pause bridge operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause bridge operations
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @dev Get proposal route configuration
     */
    function getProposalRoute(uint256 proposalId) external view returns (ProposalRoute memory) {
        return proposalRoutes[proposalId];
    }

    /**
     * @dev Get executive approval status
     */
    function getApprovalStatus(uint256 approvalId) external view returns (
        uint256 daioProposalId,
        uint256 executiveProposalId,
        bool approved,
        bool executed,
        uint256 approvalCount,
        uint256 requiredApprovals
    ) {
        ExecutiveApproval storage approval = executiveApprovals[approvalId];
        return (
            approval.daioProposalId,
            approval.executiveProposalId,
            approval.approved,
            approval.executed,
            approval.approvers.length,
            defaultExecutiveThreshold
        );
    }

    /**
     * @dev Check if address has approved specific proposal
     */
    function hasApproved(uint256 approvalId, address executive) external view returns (bool) {
        return executiveApprovals[approvalId].hasApproved[executive];
    }
}