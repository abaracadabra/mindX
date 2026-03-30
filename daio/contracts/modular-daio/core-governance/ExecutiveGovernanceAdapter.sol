// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/governance/KnowledgeHierarchyDAIO.sol";
import "../../executive-governance/ExecutiveGovernance.sol";
import "../../daio/constitution/DAIO_Constitution.sol";
import "../../daio/timelock/DAIOTimelock.sol";

/**
 * @title ExecutiveGovernanceAdapter
 * @dev Bridges existing KnowledgeHierarchyDAIO with CEO + Seven Soldiers executive governance
 *
 * Key Features:
 * - Routes critical decisions to executive approval
 * - Maintains AI-weighted voting with human oversight
 * - Constitutional validation for all actions
 * - Emergency procedures with CEO override
 * - Complete audit integration
 */
contract ExecutiveGovernanceAdapter is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant ADAPTER_ADMIN_ROLE = keccak256("ADAPTER_ADMIN_ROLE");
    bytes32 public constant PROPOSAL_ROUTER_ROLE = keccak256("PROPOSAL_ROUTER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Core governance contracts
    KnowledgeHierarchyDAIO public immutable knowledgeHierarchy;
    ExecutiveGovernance public immutable executiveGovernance;
    DAIO_Constitution public immutable constitution;
    DAIOTimelock public immutable timelock;

    // Proposal routing and tracking
    struct RoutedProposal {
        uint256 knowledgeProposalId;
        uint256 executiveProposalId;
        address proposer;
        bytes proposalData;
        string description;
        ProposalType proposalType;
        ProposalStatus status;
        uint256 creationTime;
        uint256 aiConsensusTime;
        uint256 executiveApprovalTime;
        uint256 executionTime;
        mapping(address => bool) executiveApprovals;
        uint256 approvalCount;
        bool requiresUnanimous;
    }

    enum ProposalType {
        STRATEGIC_EVOLUTION,
        ECONOMIC,
        CONSTITUTIONAL,
        OPERATIONAL
    }

    enum ProposalStatus {
        SUBMITTED,           // Submitted to Knowledge Hierarchy
        AI_CONSENSUS,        // AI consensus achieved
        EXECUTIVE_REVIEW,    // Under executive review
        EXECUTIVE_APPROVED,  // Executive approval received
        TIMELOCK_PENDING,    // Waiting for timelock
        EXECUTED,           // Successfully executed
        REJECTED,           // Rejected at any stage
        EMERGENCY_EXECUTED  // Emergency CEO execution
    }

    mapping(uint256 => RoutedProposal) public routedProposals;
    mapping(ProposalType => uint256) public requiredExecutiveApprovals;
    mapping(ProposalType => bool) public requiresExecutiveApproval;
    mapping(ProposalType => uint256) public timelockDelays;

    uint256 public nextProposalId = 1;
    uint256 public defaultExecutiveThreshold = 5; // 5 of 8 executives
    uint256 public emergencyTimelockBypass = 24 hours;

    event ProposalRouted(
        uint256 indexed routedProposalId,
        uint256 indexed knowledgeProposalId,
        address indexed proposer,
        ProposalType proposalType
    );

    event AIConsensusAchieved(
        uint256 indexed routedProposalId,
        uint256 consensusLevel,
        uint256 timestamp
    );

    event ExecutiveApprovalReceived(
        uint256 indexed routedProposalId,
        address indexed executive,
        uint256 approvalCount,
        uint256 required
    );

    event ExecutiveApprovalComplete(
        uint256 indexed routedProposalId,
        uint256 finalApprovalCount,
        uint256 timestamp
    );

    event EmergencyBypass(
        uint256 indexed routedProposalId,
        address indexed ceo,
        string reason,
        uint256 timestamp
    );

    event ProposalExecuted(
        uint256 indexed routedProposalId,
        bool successful,
        bytes result,
        uint256 timestamp
    );

    constructor(
        address _knowledgeHierarchy,
        address _executiveGovernance,
        address _constitution,
        address _timelock,
        address _admin
    ) {
        require(_knowledgeHierarchy != address(0), "Invalid knowledge hierarchy");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_constitution != address(0), "Invalid constitution");
        require(_timelock != address(0), "Invalid timelock");
        require(_admin != address(0), "Invalid admin");

        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        constitution = DAIO_Constitution(_constitution);
        timelock = DAIOTimelock(_timelock);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADAPTER_ADMIN_ROLE, _admin);
        _grantRole(PROPOSAL_ROUTER_ROLE, _admin);
        _grantRole(EMERGENCY_ROLE, _admin);

        _initializeProposalTypes();
    }

    /**
     * @dev Initialize proposal type configurations
     */
    function _initializeProposalTypes() internal {
        // Strategic Evolution - 7 of 8 executives, unanimous for major changes
        requiredExecutiveApprovals[ProposalType.STRATEGIC_EVOLUTION] = 7;
        requiresExecutiveApproval[ProposalType.STRATEGIC_EVOLUTION] = true;
        timelockDelays[ProposalType.STRATEGIC_EVOLUTION] = 7 days;

        // Economic - 5 of 8 executives
        requiredExecutiveApprovals[ProposalType.ECONOMIC] = 5;
        requiresExecutiveApproval[ProposalType.ECONOMIC] = true;
        timelockDelays[ProposalType.ECONOMIC] = 3 days;

        // Constitutional - All 8 executives (CEO + Seven Soldiers)
        requiredExecutiveApprovals[ProposalType.CONSTITUTIONAL] = 8;
        requiresExecutiveApproval[ProposalType.CONSTITUTIONAL] = true;
        timelockDelays[ProposalType.CONSTITUTIONAL] = 14 days;

        // Operational - 3 of 8 executives
        requiredExecutiveApprovals[ProposalType.OPERATIONAL] = 3;
        requiresExecutiveApproval[ProposalType.OPERATIONAL] = false; // Can skip executive approval
        timelockDelays[ProposalType.OPERATIONAL] = 1 days;
    }

    /**
     * @dev Submit proposal through knowledge hierarchy with executive routing
     */
    function submitProposal(
        bytes calldata proposalData,
        string calldata description,
        ProposalType proposalType
    ) external nonReentrant whenNotPaused returns (uint256) {
        // Constitutional pre-validation
        require(constitution.validateProposal(proposalData), "Constitutional violation");

        uint256 routedProposalId = nextProposalId++;

        // Submit to Knowledge Hierarchy for AI consensus
        uint256 knowledgeProposalId = knowledgeHierarchy.submitProposal(
            proposalData,
            description,
            _proposalTypeToString(proposalType)
        );

        // Create routed proposal tracking
        RoutedProposal storage proposal = routedProposals[routedProposalId];
        proposal.knowledgeProposalId = knowledgeProposalId;
        proposal.proposer = msg.sender;
        proposal.proposalData = proposalData;
        proposal.description = description;
        proposal.proposalType = proposalType;
        proposal.status = ProposalStatus.SUBMITTED;
        proposal.creationTime = block.timestamp;
        proposal.requiresUnanimous = (proposalType == ProposalType.CONSTITUTIONAL);

        emit ProposalRouted(routedProposalId, knowledgeProposalId, msg.sender, proposalType);
        return routedProposalId;
    }

    /**
     * @dev Process AI consensus from Knowledge Hierarchy
     */
    function processAIConsensus(
        uint256 routedProposalId,
        uint256 consensusLevel
    ) external onlyRole(PROPOSAL_ROUTER_ROLE) nonReentrant {
        RoutedProposal storage proposal = routedProposals[routedProposalId];
        require(proposal.status == ProposalStatus.SUBMITTED, "Invalid status");

        // Validate AI consensus meets requirements (67% threshold)
        require(consensusLevel >= 6700, "Insufficient AI consensus");

        proposal.status = ProposalStatus.AI_CONSENSUS;
        proposal.aiConsensusTime = block.timestamp;

        emit AIConsensusAchieved(routedProposalId, consensusLevel, block.timestamp);

        // Route to executive approval if required
        if (requiresExecutiveApproval[proposal.proposalType]) {
            _routeToExecutiveApproval(routedProposalId);
        } else {
            // Skip executive approval for operational proposals
            _routeToTimelock(routedProposalId);
        }
    }

    /**
     * @dev Route to executive approval
     */
    function _routeToExecutiveApproval(uint256 routedProposalId) internal {
        RoutedProposal storage proposal = routedProposals[routedProposalId];

        proposal.status = ProposalStatus.EXECUTIVE_REVIEW;

        // Submit to Executive Governance
        address[] memory requiredExecutives = new address[](0); // All executives can participate

        uint256 executiveProposalId = executiveGovernance.submitProposal(
            proposal.proposalData,
            proposal.description,
            requiredExecutives,
            requiredExecutiveApprovals[proposal.proposalType]
        );

        proposal.executiveProposalId = executiveProposalId;
    }

    /**
     * @dev Process executive approval
     */
    function processExecutiveApproval(
        uint256 routedProposalId,
        address executive
    ) external onlyRole(PROPOSAL_ROUTER_ROLE) nonReentrant {
        RoutedProposal storage proposal = routedProposals[routedProposalId];
        require(proposal.status == ProposalStatus.EXECUTIVE_REVIEW, "Invalid status");
        require(!proposal.executiveApprovals[executive], "Already approved");
        require(executiveGovernance.hasExecutiveRole(executive), "Not an executive");

        proposal.executiveApprovals[executive] = true;
        proposal.approvalCount++;

        emit ExecutiveApprovalReceived(
            routedProposalId,
            executive,
            proposal.approvalCount,
            requiredExecutiveApprovals[proposal.proposalType]
        );

        // Check if sufficient approvals received
        if (proposal.approvalCount >= requiredExecutiveApprovals[proposal.proposalType]) {
            proposal.status = ProposalStatus.EXECUTIVE_APPROVED;
            proposal.executiveApprovalTime = block.timestamp;

            emit ExecutiveApprovalComplete(routedProposalId, proposal.approvalCount, block.timestamp);

            // Route to timelock
            _routeToTimelock(routedProposalId);
        }
    }

    /**
     * @dev Route to timelock for delayed execution
     */
    function _routeToTimelock(uint256 routedProposalId) internal {
        RoutedProposal storage proposal = routedProposals[routedProposalId];

        proposal.status = ProposalStatus.TIMELOCK_PENDING;

        // Schedule execution through timelock
        uint256 delay = timelockDelays[proposal.proposalType];
        timelock.schedule(
            address(this),
            0,
            proposal.proposalData,
            bytes32(0),
            bytes32(routedProposalId),
            delay
        );
    }

    /**
     * @dev Execute proposal after timelock delay
     */
    function executeProposal(
        uint256 routedProposalId
    ) external nonReentrant whenNotPaused {
        RoutedProposal storage proposal = routedProposals[routedProposalId];
        require(proposal.status == ProposalStatus.TIMELOCK_PENDING, "Invalid status");

        // Execute through timelock
        try timelock.execute(
            address(this),
            0,
            proposal.proposalData,
            bytes32(0),
            bytes32(routedProposalId)
        ) returns (bytes memory result) {
            proposal.status = ProposalStatus.EXECUTED;
            proposal.executionTime = block.timestamp;

            emit ProposalExecuted(routedProposalId, true, result, block.timestamp);
        } catch Error(string memory reason) {
            proposal.status = ProposalStatus.REJECTED;

            emit ProposalExecuted(routedProposalId, false, bytes(reason), block.timestamp);
        }
    }

    /**
     * @dev Emergency CEO bypass with constitutional limits
     */
    function emergencyBypass(
        uint256 routedProposalId,
        string calldata reason
    ) external onlyRole(EMERGENCY_ROLE) nonReentrant {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can bypass");

        RoutedProposal storage proposal = routedProposals[routedProposalId];
        require(proposal.status != ProposalStatus.EXECUTED, "Already executed");
        require(proposal.status != ProposalStatus.REJECTED, "Already rejected");

        // Constitutional emergency validation
        require(constitution.validateEmergencyAction(msg.sender, reason), "Emergency action rejected");

        proposal.status = ProposalStatus.EMERGENCY_EXECUTED;
        proposal.executionTime = block.timestamp;

        emit EmergencyBypass(routedProposalId, msg.sender, reason, block.timestamp);

        // Execute immediately
        (bool success, bytes memory result) = address(this).call(proposal.proposalData);
        emit ProposalExecuted(routedProposalId, success, result, block.timestamp);
    }

    /**
     * @dev Get comprehensive proposal status
     */
    function getProposalStatus(uint256 routedProposalId) external view returns (
        ProposalStatus status,
        uint256 approvalCount,
        uint256 requiredApprovals,
        uint256 timeRemaining,
        bool canExecute
    ) {
        RoutedProposal storage proposal = routedProposals[routedProposalId];

        status = proposal.status;
        approvalCount = proposal.approvalCount;
        requiredApprovals = requiredExecutiveApprovals[proposal.proposalType];

        // Calculate time remaining for current stage
        timeRemaining = 0;
        if (status == ProposalStatus.TIMELOCK_PENDING) {
            uint256 delay = timelockDelays[proposal.proposalType];
            uint256 readyTime = proposal.executiveApprovalTime + delay;
            timeRemaining = block.timestamp >= readyTime ? 0 : readyTime - block.timestamp;
            canExecute = (timeRemaining == 0);
        }

        return (status, approvalCount, requiredApprovals, timeRemaining, canExecute);
    }

    /**
     * @dev Check if executive has approved proposal
     */
    function hasExecutiveApproved(
        uint256 routedProposalId,
        address executive
    ) external view returns (bool) {
        return routedProposals[routedProposalId].executiveApprovals[executive];
    }

    /**
     * @dev Get proposal details
     */
    function getProposalDetails(uint256 routedProposalId) external view returns (
        address proposer,
        bytes memory proposalData,
        string memory description,
        ProposalType proposalType,
        uint256 knowledgeProposalId,
        uint256 executiveProposalId
    ) {
        RoutedProposal storage proposal = routedProposals[routedProposalId];

        return (
            proposal.proposer,
            proposal.proposalData,
            proposal.description,
            proposal.proposalType,
            proposal.knowledgeProposalId,
            proposal.executiveProposalId
        );
    }

    /**
     * @dev Convert proposal type to string
     */
    function _proposalTypeToString(ProposalType proposalType) internal pure returns (string memory) {
        if (proposalType == ProposalType.STRATEGIC_EVOLUTION) {
            return "Strategic Evolution";
        } else if (proposalType == ProposalType.ECONOMIC) {
            return "Economic";
        } else if (proposalType == ProposalType.CONSTITUTIONAL) {
            return "Constitutional";
        } else {
            return "Operational";
        }
    }

    /**
     * @dev Update proposal type configuration
     */
    function updateProposalTypeConfig(
        ProposalType proposalType,
        uint256 requiredApprovals,
        bool requiresApproval,
        uint256 timelockDelay
    ) external onlyRole(ADAPTER_ADMIN_ROLE) {
        require(requiredApprovals <= 8, "Cannot require more than 8 approvals");
        require(timelockDelay <= 30 days, "Timelock delay too long");

        requiredExecutiveApprovals[proposalType] = requiredApprovals;
        requiresExecutiveApproval[proposalType] = requiresApproval;
        timelockDelays[proposalType] = timelockDelay;
    }

    /**
     * @dev Update default executive threshold
     */
    function updateDefaultExecutiveThreshold(
        uint256 newThreshold
    ) external onlyRole(ADAPTER_ADMIN_ROLE) {
        require(newThreshold >= 3 && newThreshold <= 8, "Invalid threshold");
        defaultExecutiveThreshold = newThreshold;
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}