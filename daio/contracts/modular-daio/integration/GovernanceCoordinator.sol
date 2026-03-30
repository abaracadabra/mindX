// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/governance/DAIOGovernance.sol";
import "../../daio/governance/KnowledgeHierarchyDAIO.sol";
import "./ExecutiveGovernanceBridge.sol";
import "../../executive-governance/ExecutiveGovernance.sol";

/**
 * @title GovernanceCoordinator
 * @dev Orchestrates multi-layer governance across DAIO, AI-weighted voting, and executive approval
 *
 * Decision Flow:
 * 1. Standard governance (DAIOGovernance) → AI-weighted voting (KnowledgeHierarchyDAIO)
 * 2. Executive approval (ExecutiveGovernance) via ExecutiveGovernanceBridge
 * 3. Constitutional validation throughout process
 * 4. Emergency escalation procedures
 */
contract GovernanceCoordinator is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant COORDINATOR_ROLE = keccak256("COORDINATOR_ROLE");
    bytes32 public constant EMERGENCY_COORDINATOR_ROLE = keccak256("EMERGENCY_COORDINATOR_ROLE");

    // Core governance contracts
    DAIOGovernance public immutable daioGovernance;
    KnowledgeHierarchyDAIO public immutable knowledgeHierarchy;
    ExecutiveGovernanceBridge public immutable executiveBridge;
    ExecutiveGovernance public immutable executiveGovernance;

    // Governance decision stages
    enum DecisionStage {
        COMMUNITY_VOTING,      // Standard DAIO community voting
        AI_CONSENSUS,          // AI-weighted knowledge hierarchy voting
        EXECUTIVE_REVIEW,      // CEO + Seven Soldiers review
        CONSTITUTIONAL_CHECK,  // Final constitutional validation
        EXECUTED,             // Successfully executed
        REJECTED,             // Rejected at any stage
        EMERGENCY_BYPASS      // Emergency CEO execution
    }

    // Comprehensive proposal tracking
    struct GovernanceProposal {
        uint256 id;
        address proposer;
        bytes proposalData;
        string description;
        string proposalType;

        // Stage tracking
        DecisionStage currentStage;
        uint256 stageStartTime;
        bool completed;
        bool emergency;

        // Voting results
        uint256 communityVotes;
        uint256 communitySupport;
        uint256 aiKnowledgeScore;
        uint256 aiConsensusLevel;
        uint256 executiveApprovals;
        bool constitutionalCompliant;

        // Execution details
        uint256 executionTime;
        address executor;
        bool executionSuccessful;
        string rejectionReason;

        // Related proposal IDs
        uint256 daioProposalId;
        uint256 knowledgeProposalId;
        uint256 executiveProposalId;
    }

    // Stage configuration
    struct StageConfig {
        uint256 duration;           // Maximum time for this stage
        uint256 requiredThreshold;  // Required approval threshold
        bool canSkip;              // Can this stage be skipped
        bool requiresUnanimous;    // Requires unanimous approval
    }

    mapping(uint256 => GovernanceProposal) public proposals;
    mapping(DecisionStage => StageConfig) public stageConfigs;
    mapping(bytes4 => bool) public emergencyMethods;
    mapping(address => uint256) public proposalCounts;

    uint256 public nextProposalId = 1;
    uint256 public totalProposals;
    uint256 public successfulProposals;

    // Stage duration defaults (can be configured per proposal type)
    uint256 public constant DEFAULT_COMMUNITY_DURATION = 7 days;
    uint256 public constant DEFAULT_AI_DURATION = 3 days;
    uint256 public constant DEFAULT_EXECUTIVE_DURATION = 5 days;
    uint256 public constant DEFAULT_CONSTITUTIONAL_DURATION = 1 days;

    event ProposalSubmitted(
        uint256 indexed proposalId,
        address indexed proposer,
        string proposalType,
        DecisionStage initialStage
    );

    event StageTransition(
        uint256 indexed proposalId,
        DecisionStage fromStage,
        DecisionStage toStage,
        uint256 timestamp
    );

    event DecisionReached(
        uint256 indexed proposalId,
        DecisionStage stage,
        bool approved,
        uint256 votes,
        uint256 threshold
    );

    event ProposalExecuted(
        uint256 indexed proposalId,
        address indexed executor,
        bool successful,
        uint256 timestamp
    );

    event EmergencyEscalation(
        uint256 indexed proposalId,
        address indexed escalator,
        string reason,
        uint256 timestamp
    );

    constructor(
        address _daioGovernance,
        address _knowledgeHierarchy,
        address _executiveBridge,
        address _executiveGovernance,
        address _admin
    ) {
        require(_daioGovernance != address(0), "Invalid DAIO governance");
        require(_knowledgeHierarchy != address(0), "Invalid knowledge hierarchy");
        require(_executiveBridge != address(0), "Invalid executive bridge");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_admin != address(0), "Invalid admin");

        daioGovernance = DAIOGovernance(_daioGovernance);
        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
        executiveBridge = ExecutiveGovernanceBridge(_executiveBridge);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(COORDINATOR_ROLE, _admin);
        _grantRole(EMERGENCY_COORDINATOR_ROLE, _admin);

        _initializeStageConfigs();
        _initializeEmergencyMethods();
    }

    /**
     * @dev Initialize default stage configurations
     */
    function _initializeStageConfigs() internal {
        stageConfigs[DecisionStage.COMMUNITY_VOTING] = StageConfig({
            duration: DEFAULT_COMMUNITY_DURATION,
            requiredThreshold: 5000, // 50% support
            canSkip: false,
            requiresUnanimous: false
        });

        stageConfigs[DecisionStage.AI_CONSENSUS] = StageConfig({
            duration: DEFAULT_AI_DURATION,
            requiredThreshold: 6700, // 67% AI consensus
            canSkip: false,
            requiresUnanimous: false
        });

        stageConfigs[DecisionStage.EXECUTIVE_REVIEW] = StageConfig({
            duration: DEFAULT_EXECUTIVE_DURATION,
            requiredThreshold: 5, // 5 of 8 executives
            canSkip: false,
            requiresUnanimous: false
        });

        stageConfigs[DecisionStage.CONSTITUTIONAL_CHECK] = StageConfig({
            duration: DEFAULT_CONSTITUTIONAL_DURATION,
            requiredThreshold: 10000, // Must be constitutional
            canSkip: false,
            requiresUnanimous: true
        });
    }

    /**
     * @dev Initialize emergency method signatures
     */
    function _initializeEmergencyMethods() internal {
        emergencyMethods[bytes4(keccak256("pauseSystem()"))] = true;
        emergencyMethods[bytes4(keccak256("emergencyWithdraw(address,uint256)"))] = true;
        emergencyMethods[bytes4(keccak256("activateSecurityProtocol()"))] = true;
        emergencyMethods[bytes4(keccak256("freezeAssets(address)"))] = true;
    }

    /**
     * @dev Submit proposal to coordinated governance process
     */
    function submitProposal(
        bytes calldata proposalData,
        string calldata description,
        string calldata proposalType,
        bool isEmergency
    ) external nonReentrant whenNotPaused returns (uint256) {
        require(proposalData.length > 0, "Empty proposal data");
        require(bytes(description).length > 0, "Empty description");

        uint256 proposalId = nextProposalId++;
        totalProposals++;
        proposalCounts[msg.sender]++;

        // Determine initial stage based on proposal type and emergency status
        DecisionStage initialStage = isEmergency ?
            DecisionStage.EMERGENCY_BYPASS :
            DecisionStage.COMMUNITY_VOTING;

        // Create comprehensive proposal tracking
        GovernanceProposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposer = msg.sender;
        proposal.proposalData = proposalData;
        proposal.description = description;
        proposal.proposalType = proposalType;
        proposal.currentStage = initialStage;
        proposal.stageStartTime = block.timestamp;
        proposal.emergency = isEmergency;

        // Submit to initial governance layer
        if (isEmergency) {
            _handleEmergencyProposal(proposalId);
        } else {
            _initiateStandardGovernance(proposalId);
        }

        emit ProposalSubmitted(proposalId, msg.sender, proposalType, initialStage);
        return proposalId;
    }

    /**
     * @dev Initiate standard governance process
     */
    function _initiateStandardGovernance(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        // Submit to DAIO community governance
        uint256 daioProposalId = daioGovernance.submitProposal(
            proposal.proposalData,
            proposal.description,
            proposal.proposalType
        );
        proposal.daioProposalId = daioProposalId;
    }

    /**
     * @dev Handle emergency proposal bypass
     */
    function _handleEmergencyProposal(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        // Validate emergency method
        bytes4 methodSig = bytes4(proposal.proposalData[:4]);
        require(emergencyMethods[methodSig], "Not an emergency method");

        // Route directly to executive governance for CEO approval
        uint256 executiveProposalId = executiveBridge.routeProposal(
            proposalId,
            proposal.proposalData,
            proposal.proposalType,
            new address[](1) // Only CEO required for emergency
        );
        proposal.executiveProposalId = executiveProposalId;
    }

    /**
     * @dev Process stage completion and advance to next stage
     */
    function advanceStage(
        uint256 proposalId,
        uint256 votes,
        uint256 support
    ) external onlyRole(COORDINATOR_ROLE) nonReentrant {
        GovernanceProposal storage proposal = proposals[proposalId];
        require(!proposal.completed, "Proposal already completed");

        DecisionStage currentStage = proposal.currentStage;
        StageConfig memory config = stageConfigs[currentStage];

        // Check if stage duration exceeded
        if (block.timestamp > proposal.stageStartTime + config.duration) {
            _rejectProposal(proposalId, "Stage timeout exceeded");
            return;
        }

        // Check if threshold met
        bool approved = support >= config.requiredThreshold;
        if (!approved && !config.canSkip) {
            _rejectProposal(proposalId, "Insufficient support");
            return;
        }

        // Update voting results for current stage
        _updateVotingResults(proposalId, currentStage, votes, support);

        // Advance to next stage
        DecisionStage nextStage = _getNextStage(currentStage);
        _transitionToStage(proposalId, nextStage);

        emit DecisionReached(proposalId, currentStage, approved, votes, config.requiredThreshold);
    }

    /**
     * @dev Update voting results for specific stage
     */
    function _updateVotingResults(
        uint256 proposalId,
        DecisionStage stage,
        uint256 votes,
        uint256 support
    ) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        if (stage == DecisionStage.COMMUNITY_VOTING) {
            proposal.communityVotes = votes;
            proposal.communitySupport = support;
        } else if (stage == DecisionStage.AI_CONSENSUS) {
            proposal.aiKnowledgeScore = votes;
            proposal.aiConsensusLevel = support;
        } else if (stage == DecisionStage.EXECUTIVE_REVIEW) {
            proposal.executiveApprovals = votes;
        }
    }

    /**
     * @dev Get next governance stage
     */
    function _getNextStage(DecisionStage currentStage) internal pure returns (DecisionStage) {
        if (currentStage == DecisionStage.COMMUNITY_VOTING) {
            return DecisionStage.AI_CONSENSUS;
        } else if (currentStage == DecisionStage.AI_CONSENSUS) {
            return DecisionStage.EXECUTIVE_REVIEW;
        } else if (currentStage == DecisionStage.EXECUTIVE_REVIEW) {
            return DecisionStage.CONSTITUTIONAL_CHECK;
        } else if (currentStage == DecisionStage.CONSTITUTIONAL_CHECK) {
            return DecisionStage.EXECUTED;
        } else if (currentStage == DecisionStage.EMERGENCY_BYPASS) {
            return DecisionStage.EXECUTED;
        }
        return DecisionStage.REJECTED;
    }

    /**
     * @dev Transition proposal to next stage
     */
    function _transitionToStage(uint256 proposalId, DecisionStage newStage) internal {
        GovernanceProposal storage proposal = proposals[proposalId];
        DecisionStage oldStage = proposal.currentStage;

        proposal.currentStage = newStage;
        proposal.stageStartTime = block.timestamp;

        if (newStage == DecisionStage.AI_CONSENSUS) {
            _initiateAIConsensus(proposalId);
        } else if (newStage == DecisionStage.EXECUTIVE_REVIEW) {
            _initiateExecutiveReview(proposalId);
        } else if (newStage == DecisionStage.CONSTITUTIONAL_CHECK) {
            _initiateConstitutionalCheck(proposalId);
        } else if (newStage == DecisionStage.EXECUTED) {
            _executeProposal(proposalId);
        }

        emit StageTransition(proposalId, oldStage, newStage, block.timestamp);
    }

    /**
     * @dev Initiate AI consensus voting
     */
    function _initiateAIConsensus(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        uint256 knowledgeProposalId = knowledgeHierarchy.submitProposal(
            proposal.proposalData,
            proposal.description,
            proposal.proposalType
        );
        proposal.knowledgeProposalId = knowledgeProposalId;
    }

    /**
     * @dev Initiate executive review
     */
    function _initiateExecutiveReview(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        // Determine required executives based on proposal type
        address[] memory requiredExecutives = _getRequiredExecutives(proposal.proposalType);

        uint256 executiveProposalId = executiveBridge.routeProposal(
            proposalId,
            proposal.proposalData,
            proposal.proposalType,
            requiredExecutives
        );
        proposal.executiveProposalId = executiveProposalId;
    }

    /**
     * @dev Initiate constitutional compliance check
     */
    function _initiateConstitutionalCheck(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        (bool compliant, ) = executiveBridge.validateConstitutionalCompliance(
            address(this),
            proposal.proposalData,
            0
        );

        proposal.constitutionalCompliant = compliant;

        if (compliant) {
            _transitionToStage(proposalId, DecisionStage.EXECUTED);
        } else {
            _rejectProposal(proposalId, "Constitutional violation");
        }
    }

    /**
     * @dev Execute approved proposal
     */
    function _executeProposal(uint256 proposalId) internal {
        GovernanceProposal storage proposal = proposals[proposalId];

        try daioGovernance.executeProposal(proposal.daioProposalId) {
            proposal.completed = true;
            proposal.executionSuccessful = true;
            proposal.executionTime = block.timestamp;
            proposal.executor = address(this);
            successfulProposals++;

            emit ProposalExecuted(proposalId, address(this), true, block.timestamp);
        } catch Error(string memory reason) {
            _rejectProposal(proposalId, reason);
        }
    }

    /**
     * @dev Reject proposal with reason
     */
    function _rejectProposal(uint256 proposalId, string memory reason) internal {
        GovernanceProposal storage proposal = proposals[proposalId];
        proposal.currentStage = DecisionStage.REJECTED;
        proposal.completed = true;
        proposal.rejectionReason = reason;
        proposal.executionSuccessful = false;
    }

    /**
     * @dev Get required executives for proposal type
     */
    function _getRequiredExecutives(string memory proposalType) internal view returns (address[] memory) {
        // Implementation would determine required executives based on proposal type
        // For now, return empty array (all executives can vote)
        return new address[](0);
    }

    /**
     * @dev Emergency escalation by authorized roles
     */
    function emergencyEscalate(
        uint256 proposalId,
        string calldata reason
    ) external onlyRole(EMERGENCY_COORDINATOR_ROLE) nonReentrant {
        GovernanceProposal storage proposal = proposals[proposalId];
        require(!proposal.completed, "Proposal already completed");

        proposal.currentStage = DecisionStage.EMERGENCY_BYPASS;
        proposal.emergency = true;
        proposal.stageStartTime = block.timestamp;

        emit EmergencyEscalation(proposalId, msg.sender, reason, block.timestamp);
    }

    /**
     * @dev Get comprehensive proposal status
     */
    function getProposalStatus(uint256 proposalId) external view returns (
        GovernanceProposal memory proposal,
        uint256 stageTimeRemaining,
        bool canAdvance
    ) {
        proposal = proposals[proposalId];

        StageConfig memory config = stageConfigs[proposal.currentStage];
        uint256 elapsed = block.timestamp - proposal.stageStartTime;
        stageTimeRemaining = elapsed >= config.duration ? 0 : config.duration - elapsed;

        canAdvance = !proposal.completed && stageTimeRemaining > 0;

        return (proposal, stageTimeRemaining, canAdvance);
    }

    /**
     * @dev Get governance statistics
     */
    function getGovernanceStats() external view returns (
        uint256 totalProposalsCount,
        uint256 successfulProposalsCount,
        uint256 successRate,
        uint256 activeProposals
    ) {
        totalProposalsCount = totalProposals;
        successfulProposalsCount = successfulProposals;
        successRate = totalProposals > 0 ? (successfulProposals * 10000) / totalProposals : 0;

        // Count active proposals
        activeProposals = 0;
        for (uint256 i = 1; i < nextProposalId; i++) {
            if (!proposals[i].completed) {
                activeProposals++;
            }
        }

        return (totalProposalsCount, successfulProposalsCount, successRate, activeProposals);
    }

    /**
     * @dev Update stage configuration
     */
    function updateStageConfig(
        DecisionStage stage,
        uint256 duration,
        uint256 threshold,
        bool canSkip,
        bool requiresUnanimous
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        stageConfigs[stage] = StageConfig({
            duration: duration,
            requiredThreshold: threshold,
            canSkip: canSkip,
            requiresUnanimous: requiresUnanimous
        });
    }

    /**
     * @dev Emergency pause coordination
     */
    function emergencyPause() external onlyRole(EMERGENCY_COORDINATOR_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause coordination
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}