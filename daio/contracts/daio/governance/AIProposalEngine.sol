// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./KnowledgeHierarchyDAIO.sol";
import "./TriumvirateGovernance.sol";
import "../treasury/TreasuryFeeCollector.sol";

/**
 * @title AIProposalEngine
 * @notice AI proposal creation and validation with learning mechanisms
 * @dev Extends AI capabilities while maintaining human oversight for fund control
 */
contract AIProposalEngine is AccessControl, ReentrancyGuard {

    bytes32 public constant AI_AGENT_ROLE = keccak256("AI_AGENT_ROLE");
    bytes32 public constant HUMAN_SPONSOR_ROLE = keccak256("HUMAN_SPONSOR_ROLE");
    bytes32 public constant PROPOSAL_VALIDATOR_ROLE = keccak256("PROPOSAL_VALIDATOR_ROLE");

    enum AIProposalType {
        OPERATIONAL,        // Day-to-day operational proposals
        RESEARCH,          // Research and development proposals
        COMMUNITY,         // Community engagement proposals
        TECHNICAL,         // Technical improvements
        GOVERNANCE,        // Governance process improvements
        EDUCATIONAL,       // Educational content and training
        INTEGRATION        // System integration proposals
    }

    enum ProposalValidationStatus {
        PENDING,           // Awaiting validation
        VALIDATED,         // Passed validation
        REJECTED,          // Failed validation
        REQUIRES_SPONSOR,  // Needs human sponsor
        EXPIRED            // Validation period expired
    }

    enum AIReputation {
        NOVICE,           // 0-25 reputation points
        CONTRIBUTOR,      // 26-75 reputation points
        EXPERT,           // 76-150 reputation points
        MASTER,           // 151-300 reputation points
        ARCHITECT         // 300+ reputation points
    }

    struct AIProposal {
        uint256 proposalId;
        address aiAgent;
        AIProposalType proposalType;
        string title;
        string description;
        string technicalSpecification;
        string expectedOutcome;
        uint256 estimatedCost;
        uint256 estimatedDuration; // in seconds

        address humanSponsor;      // Required for financial proposals
        bool requiresHumanSponsor;

        ProposalValidationStatus validationStatus;
        uint256 submittedAt;
        uint256 validationDeadline;

        // Learning metrics
        uint256 communitySupport;  // Community feedback score
        uint256 technicalScore;    // Technical feasibility score
        uint256 riskAssessment;    // Risk level (1-10)

        bool executed;
        bool successful;           // Whether execution was successful
        uint256 actualCost;
        uint256 actualDuration;
    }

    struct AIAgentProfile {
        address agentAddress;
        uint256 reputationPoints;
        AIReputation reputationLevel;
        uint256 totalProposalsSubmitted;
        uint256 successfulProposals;
        uint256 failedProposals;
        mapping(AIProposalType => uint256) proposalsByType;
        mapping(AIProposalType => uint256) successRateByType; // Percentage
        uint256 totalStakeEarned;
        uint256 totalStakeLost;
        uint256 lastProposalTime;
        bool active;
        string specialization;     // Agent's area of expertise
    }

    struct ProposalLearningData {
        uint256 proposalId;
        uint256 initialCommunitySupport;
        uint256 finalCommunitySupport;
        uint256 votingParticipation;
        uint256 executionEfficiency; // Actual vs estimated metrics
        string lessonsLearned;
        mapping(string => uint256) keyMetrics;
    }

    struct ValidationCriteria {
        uint256 minTechnicalScore;    // Minimum technical feasibility
        uint256 maxRiskLevel;         // Maximum acceptable risk
        uint256 minCommunitySupport;  // Minimum community backing
        bool requiresHumanSponsorForFinancial;
        uint256 validationPeriod;     // Time for validation (seconds)
        uint256 maxProposalCost;      // Maximum cost AI can propose alone
    }

    struct ProposalTemplate {
        AIProposalType proposalType;
        string templateName;
        string descriptionTemplate;
        string technicalTemplate;
        uint256 defaultDuration;
        uint256 estimatedCostRange; // Typical cost range
        bool requiresSponsor;
        uint256 riskLevel;
        string[] requiredFields;
    }

    // Storage
    mapping(uint256 => AIProposal) public aiProposals;
    mapping(address => AIAgentProfile) public agentProfiles;
    mapping(uint256 => ProposalLearningData) public learningData;
    mapping(uint256 => ProposalTemplate) public proposalTemplates;
    mapping(AIProposalType => ValidationCriteria) public validationCriteria;
    mapping(address => mapping(uint256 => bool)) public agentVotedOnProposal;
    mapping(address => uint256[]) public agentProposals; // Agent => proposal IDs
    mapping(AIProposalType => uint256[]) public proposalsByType;

    uint256 public proposalCount;
    uint256 public templateCount;
    uint256 public totalAIProposals;
    uint256 public successfulAIProposals;

    // Configuration
    uint256 public constant MAX_REPUTATION_POINTS = 1000;
    uint256 public constant PROPOSAL_VALIDATION_PERIOD = 7 days;
    uint256 public constant MAX_ACTIVE_PROPOSALS_PER_AGENT = 3;
    uint256 public constant MIN_COOLDOWN_PERIOD = 1 hours;
    uint256 public constant BASE_REPUTATION_REWARD = 10;
    uint256 public constant REPUTATION_PENALTY = 5;

    // Integration contracts
    KnowledgeHierarchyDAIO public knowledgeHierarchy;
    TriumvirateGovernance public triumvirateGovernance;
    TreasuryFeeCollector public feeCollector;

    // Events
    event AIProposalSubmitted(
        uint256 indexed proposalId,
        address indexed aiAgent,
        AIProposalType proposalType,
        string title,
        bool requiresSponsor
    );

    event ProposalValidated(
        uint256 indexed proposalId,
        ProposalValidationStatus status,
        uint256 technicalScore,
        uint256 riskLevel
    );

    event HumanSponsorAssigned(
        uint256 indexed proposalId,
        address indexed sponsor,
        address indexed aiAgent
    );

    event ProposalExecutionCompleted(
        uint256 indexed proposalId,
        bool successful,
        uint256 actualCost,
        uint256 actualDuration
    );

    event AIReputationUpdated(
        address indexed aiAgent,
        uint256 oldReputation,
        uint256 newReputation,
        AIReputation newLevel
    );

    event ProposalTemplateCreated(
        uint256 indexed templateId,
        AIProposalType proposalType,
        string templateName
    );

    event LearningDataRecorded(
        uint256 indexed proposalId,
        uint256 executionEfficiency,
        string lessonsLearned
    );

    modifier onlyAIAgent() {
        require(hasRole(AI_AGENT_ROLE, msg.sender), "Not an AI agent");
        require(agentProfiles[msg.sender].active, "AI agent not active");
        _;
    }

    modifier onlyHumanSponsor() {
        require(hasRole(HUMAN_SPONSOR_ROLE, msg.sender), "Not a human sponsor");
        _;
    }

    modifier validProposal(uint256 proposalId) {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal ID");
        require(aiProposals[proposalId].proposalId > 0, "Proposal doesn't exist");
        _;
    }

    constructor(
        address _knowledgeHierarchy,
        address _triumvirateGovernance,
        address _feeCollector
    ) {
        require(_knowledgeHierarchy != address(0), "Invalid knowledge hierarchy");
        require(_triumvirateGovernance != address(0), "Invalid triumvirate governance");
        require(_feeCollector != address(0), "Invalid fee collector");

        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
        triumvirateGovernance = TriumvirateGovernance(_triumvirateGovernance);
        feeCollector = TreasuryFeeCollector(payable(_feeCollector));

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PROPOSAL_VALIDATOR_ROLE, msg.sender);
        _grantRole(HUMAN_SPONSOR_ROLE, msg.sender);

        _initializeValidationCriteria();
        _createDefaultTemplates();
    }

    /**
     * @notice Submit AI proposal with validation
     * @param proposalType Type of AI proposal
     * @param title Proposal title
     * @param description Detailed description
     * @param technicalSpec Technical specification
     * @param expectedOutcome Expected outcome description
     * @param estimatedCost Estimated cost in wei
     * @param estimatedDuration Estimated duration in seconds
     */
    function submitAIProposal(
        AIProposalType proposalType,
        string memory title,
        string memory description,
        string memory technicalSpec,
        string memory expectedOutcome,
        uint256 estimatedCost,
        uint256 estimatedDuration
    ) external payable onlyAIAgent nonReentrant returns (uint256 proposalId) {
        require(bytes(title).length > 0, "Title required");
        require(bytes(description).length > 0, "Description required");

        AIAgentProfile storage agent = agentProfiles[msg.sender];
        require(
            block.timestamp - agent.lastProposalTime >= MIN_COOLDOWN_PERIOD,
            "Cooldown period not met"
        );

        // Check proposal limits
        uint256 activeProposals = _getActiveProposalCount(msg.sender);
        require(activeProposals < MAX_ACTIVE_PROPOSALS_PER_AGENT, "Too many active proposals");

        // Validate against criteria
        ValidationCriteria memory criteria = validationCriteria[proposalType];
        bool requiresSponsor = estimatedCost > criteria.maxProposalCost ||
                              criteria.requiresHumanSponsorForFinancial;

        // Collect AI proposal fee
        uint256 proposalFee = feeCollector.calculateFee(TreasuryFeeCollector.FeeType.AI_PROPOSAL, 0);
        require(msg.value >= proposalFee, "Insufficient fee");

        feeCollector.collectTypedFee{value: proposalFee}(
            TreasuryFeeCollector.FeeType.AI_PROPOSAL,
            "ai_proposal",
            proposalCount + 1
        );

        proposalCount++;
        totalAIProposals++;

        aiProposals[proposalCount] = AIProposal({
            proposalId: proposalCount,
            aiAgent: msg.sender,
            proposalType: proposalType,
            title: title,
            description: description,
            technicalSpecification: technicalSpec,
            expectedOutcome: expectedOutcome,
            estimatedCost: estimatedCost,
            estimatedDuration: estimatedDuration,
            humanSponsor: address(0),
            requiresHumanSponsor: requiresSponsor,
            validationStatus: ProposalValidationStatus.PENDING,
            submittedAt: block.timestamp,
            validationDeadline: block.timestamp + criteria.validationPeriod,
            communitySupport: 0,
            technicalScore: 0,
            riskAssessment: 0,
            executed: false,
            successful: false,
            actualCost: 0,
            actualDuration: 0
        });

        // Update agent profile
        agent.totalProposalsSubmitted++;
        agent.proposalsByType[proposalType]++;
        agent.lastProposalTime = block.timestamp;

        // Track by agent and type
        agentProposals[msg.sender].push(proposalCount);
        proposalsByType[proposalType].push(proposalCount);

        emit AIProposalSubmitted(proposalCount, msg.sender, proposalType, title, requiresSponsor);

        return proposalCount;
    }

    /**
     * @notice Validate AI proposal
     * @param proposalId Proposal ID
     * @param technicalScore Technical feasibility score (0-100)
     * @param riskLevel Risk assessment (1-10)
     * @param communityFeedback Community feedback score (0-100)
     */
    function validateProposal(
        uint256 proposalId,
        uint256 technicalScore,
        uint256 riskLevel,
        uint256 communityFeedback
    ) external validProposal(proposalId) onlyRole(PROPOSAL_VALIDATOR_ROLE) {
        require(technicalScore <= 100, "Invalid technical score");
        require(riskLevel >= 1 && riskLevel <= 10, "Invalid risk level");
        require(communityFeedback <= 100, "Invalid community feedback");

        AIProposal storage proposal = aiProposals[proposalId];
        require(proposal.validationStatus == ProposalValidationStatus.PENDING, "Already validated");
        require(block.timestamp <= proposal.validationDeadline, "Validation expired");

        proposal.technicalScore = technicalScore;
        proposal.riskAssessment = riskLevel;
        proposal.communitySupport = communityFeedback;

        // Apply validation criteria
        ValidationCriteria memory criteria = validationCriteria[proposal.proposalType];

        if (technicalScore < criteria.minTechnicalScore ||
            riskLevel > criteria.maxRiskLevel ||
            communityFeedback < criteria.minCommunitySupport) {
            proposal.validationStatus = ProposalValidationStatus.REJECTED;
            _updateAgentReputation(proposal.aiAgent, false, 0); // Penalty for rejection
        } else if (proposal.requiresHumanSponsor) {
            proposal.validationStatus = ProposalValidationStatus.REQUIRES_SPONSOR;
        } else {
            proposal.validationStatus = ProposalValidationStatus.VALIDATED;
            _updateAgentReputation(proposal.aiAgent, true, BASE_REPUTATION_REWARD);
        }

        emit ProposalValidated(proposalId, proposal.validationStatus, technicalScore, riskLevel);
    }

    /**
     * @notice Assign human sponsor to AI proposal
     * @param proposalId Proposal ID
     */
    function sponsorProposal(uint256 proposalId) external validProposal(proposalId) onlyHumanSponsor {
        AIProposal storage proposal = aiProposals[proposalId];
        require(proposal.validationStatus == ProposalValidationStatus.REQUIRES_SPONSOR, "Doesn't need sponsor");
        require(proposal.humanSponsor == address(0), "Already has sponsor");

        proposal.humanSponsor = msg.sender;
        proposal.validationStatus = ProposalValidationStatus.VALIDATED;

        _updateAgentReputation(proposal.aiAgent, true, BASE_REPUTATION_REWARD);

        emit HumanSponsorAssigned(proposalId, msg.sender, proposal.aiAgent);
    }

    /**
     * @notice Record proposal execution results for learning
     * @param proposalId Proposal ID
     * @param successful Whether execution was successful
     * @param actualCost Actual execution cost
     * @param actualDuration Actual execution duration
     * @param lessonsLearned Key lessons learned
     */
    function recordExecutionResults(
        uint256 proposalId,
        bool successful,
        uint256 actualCost,
        uint256 actualDuration,
        string memory lessonsLearned
    ) external validProposal(proposalId) onlyRole(PROPOSAL_VALIDATOR_ROLE) {
        AIProposal storage proposal = aiProposals[proposalId];
        require(!proposal.executed, "Already recorded");

        proposal.executed = true;
        proposal.successful = successful;
        proposal.actualCost = actualCost;
        proposal.actualDuration = actualDuration;

        // Calculate execution efficiency
        uint256 costEfficiency = proposal.estimatedCost > 0 ?
            (proposal.estimatedCost * 100) / (actualCost == 0 ? 1 : actualCost) : 100;
        uint256 timeEfficiency = proposal.estimatedDuration > 0 ?
            (proposal.estimatedDuration * 100) / (actualDuration == 0 ? 1 : actualDuration) : 100;
        uint256 executionEfficiency = (costEfficiency + timeEfficiency) / 2;

        // Store learning data
        ProposalLearningData storage data = learningData[proposalId];
        data.proposalId = proposalId;
        data.initialCommunitySupport = proposal.communitySupport;
        data.finalCommunitySupport = proposal.communitySupport; // Would be updated by community
        data.votingParticipation = 0; // Would be calculated from voting data
        data.executionEfficiency = executionEfficiency;
        data.lessonsLearned = lessonsLearned;

        // Update agent statistics
        AIAgentProfile storage agent = agentProfiles[proposal.aiAgent];
        if (successful) {
            agent.successfulProposals++;
            successfulAIProposals++;
            _updateAgentReputation(proposal.aiAgent, true, BASE_REPUTATION_REWARD * 2);
        } else {
            agent.failedProposals++;
            _updateAgentReputation(proposal.aiAgent, false, REPUTATION_PENALTY);
        }

        // Update success rate by type
        uint256 totalOfType = agent.proposalsByType[proposal.proposalType];
        uint256 successfulOfType = 0; // Would need to track this separately
        if (totalOfType > 0) {
            agent.successRateByType[proposal.proposalType] = (successfulOfType * 100) / totalOfType;
        }

        emit ProposalExecutionCompleted(proposalId, successful, actualCost, actualDuration);
        emit LearningDataRecorded(proposalId, executionEfficiency, lessonsLearned);
    }

    /**
     * @notice Register new AI agent
     * @param aiAgent Agent address
     * @param specialization Agent's area of expertise
     */
    function registerAIAgent(
        address aiAgent,
        string memory specialization
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(aiAgent != address(0), "Invalid agent address");
        require(!agentProfiles[aiAgent].active, "Agent already registered");

        AIAgentProfile storage profile = agentProfiles[aiAgent];
        profile.agentAddress = aiAgent;
        profile.reputationPoints = 0;
        profile.reputationLevel = AIReputation.NOVICE;
        profile.totalProposalsSubmitted = 0;
        profile.successfulProposals = 0;
        profile.failedProposals = 0;
        profile.totalStakeEarned = 0;
        profile.totalStakeLost = 0;
        profile.lastProposalTime = 0;
        profile.active = true;
        profile.specialization = specialization;

        _grantRole(AI_AGENT_ROLE, aiAgent);
    }

    /**
     * @notice Create proposal template
     * @param proposalType Type of proposal
     * @param templateName Template name
     * @param descriptionTemplate Description template
     * @param technicalTemplate Technical template
     * @param defaultDuration Default duration estimate
     * @param estimatedCostRange Typical cost range
     * @param requiresSponsor Whether template requires sponsor
     * @param riskLevel Default risk level
     */
    function createProposalTemplate(
        AIProposalType proposalType,
        string memory templateName,
        string memory descriptionTemplate,
        string memory technicalTemplate,
        uint256 defaultDuration,
        uint256 estimatedCostRange,
        bool requiresSponsor,
        uint256 riskLevel
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bytes(templateName).length > 0, "Template name required");
        require(riskLevel >= 1 && riskLevel <= 10, "Invalid risk level");

        templateCount++;

        proposalTemplates[templateCount] = ProposalTemplate({
            proposalType: proposalType,
            templateName: templateName,
            descriptionTemplate: descriptionTemplate,
            technicalTemplate: technicalTemplate,
            defaultDuration: defaultDuration,
            estimatedCostRange: estimatedCostRange,
            requiresSponsor: requiresSponsor,
            riskLevel: riskLevel,
            requiredFields: new string[](0) // Would be populated with required fields
        });

        emit ProposalTemplateCreated(templateCount, proposalType, templateName);
    }

    /**
     * @notice Get AI proposal details
     * @param proposalId Proposal ID
     * @return aiAgent AI agent address
     * @return proposalType Type of proposal
     * @return title Proposal title
     * @return estimatedCost Estimated cost
     * @return estimatedDuration Estimated duration
     * @return humanSponsor Human sponsor address
     * @return validationStatus Validation status
     * @return technicalScore Technical score
     * @return riskAssessment Risk assessment
     * @return executed Whether executed
     * @return successful Whether successful
     */
    function getAIProposal(uint256 proposalId) external view validProposal(proposalId) returns (
        address aiAgent,
        AIProposalType proposalType,
        string memory title,
        uint256 estimatedCost,
        uint256 estimatedDuration,
        address humanSponsor,
        ProposalValidationStatus validationStatus,
        uint256 technicalScore,
        uint256 riskAssessment,
        bool executed,
        bool successful
    ) {
        AIProposal storage proposal = aiProposals[proposalId];
        return (
            proposal.aiAgent,
            proposal.proposalType,
            proposal.title,
            proposal.estimatedCost,
            proposal.estimatedDuration,
            proposal.humanSponsor,
            proposal.validationStatus,
            proposal.technicalScore,
            proposal.riskAssessment,
            proposal.executed,
            proposal.successful
        );
    }

    /**
     * @notice Get AI agent profile
     * @param aiAgent Agent address
     * @return reputationPoints Agent reputation points
     * @return reputationLevel Agent reputation level
     * @return totalProposalsSubmitted Total proposals submitted
     * @return successfulProposals Successful proposals count
     * @return failedProposals Failed proposals count
     * @return active Whether agent is active
     * @return specialization Agent specialization
     */
    function getAIAgentProfile(address aiAgent) external view returns (
        uint256 reputationPoints,
        AIReputation reputationLevel,
        uint256 totalProposalsSubmitted,
        uint256 successfulProposals,
        uint256 failedProposals,
        bool active,
        string memory specialization
    ) {
        AIAgentProfile storage agent = agentProfiles[aiAgent];
        return (
            agent.reputationPoints,
            agent.reputationLevel,
            agent.totalProposalsSubmitted,
            agent.successfulProposals,
            agent.failedProposals,
            agent.active,
            agent.specialization
        );
    }

    /**
     * @notice Get proposals by AI agent
     * @param aiAgent Agent address
     * @return Array of proposal IDs
     */
    function getProposalsByAgent(address aiAgent) external view returns (uint256[] memory) {
        return agentProposals[aiAgent];
    }

    /**
     * @notice Get proposals by type
     * @param proposalType Proposal type
     * @return Array of proposal IDs
     */
    function getProposalsByType(AIProposalType proposalType) external view returns (uint256[] memory) {
        return proposalsByType[proposalType];
    }

    /**
     * @notice Get learning data for proposal
     * @param proposalId Proposal ID
     * @return initialCommunitySupport Initial community support
     * @return finalCommunitySupport Final community support
     * @return votingParticipation Voting participation rate
     * @return executionEfficiency Execution efficiency score
     * @return lessonsLearned Lessons learned text
     */
    function getLearningData(uint256 proposalId) external view returns (
        uint256 initialCommunitySupport,
        uint256 finalCommunitySupport,
        uint256 votingParticipation,
        uint256 executionEfficiency,
        string memory lessonsLearned
    ) {
        ProposalLearningData storage data = learningData[proposalId];
        return (
            data.initialCommunitySupport,
            data.finalCommunitySupport,
            data.votingParticipation,
            data.executionEfficiency,
            data.lessonsLearned
        );
    }

    /**
     * @notice Initialize validation criteria for all proposal types
     */
    function _initializeValidationCriteria() internal {
        // Operational proposals: low barrier, medium oversight
        validationCriteria[AIProposalType.OPERATIONAL] = ValidationCriteria({
            minTechnicalScore: 50,
            maxRiskLevel: 5,
            minCommunitySupport: 30,
            requiresHumanSponsorForFinancial: true,
            validationPeriod: PROPOSAL_VALIDATION_PERIOD,
            maxProposalCost: 1 ether
        });

        // Research proposals: high technical bar, flexible execution
        validationCriteria[AIProposalType.RESEARCH] = ValidationCriteria({
            minTechnicalScore: 70,
            maxRiskLevel: 7,
            minCommunitySupport: 40,
            requiresHumanSponsorForFinancial: true,
            validationPeriod: PROPOSAL_VALIDATION_PERIOD,
            maxProposalCost: 5 ether
        });

        // Community proposals: high community support needed
        validationCriteria[AIProposalType.COMMUNITY] = ValidationCriteria({
            minTechnicalScore: 40,
            maxRiskLevel: 3,
            minCommunitySupport: 60,
            requiresHumanSponsorForFinancial: false,
            validationPeriod: PROPOSAL_VALIDATION_PERIOD,
            maxProposalCost: 0.5 ether
        });

        // Technical proposals: highest technical standards
        validationCriteria[AIProposalType.TECHNICAL] = ValidationCriteria({
            minTechnicalScore: 80,
            maxRiskLevel: 6,
            minCommunitySupport: 50,
            requiresHumanSponsorForFinancial: true,
            validationPeriod: PROPOSAL_VALIDATION_PERIOD * 2, // Longer validation
            maxProposalCost: 10 ether
        });

        // Governance proposals: strict oversight
        validationCriteria[AIProposalType.GOVERNANCE] = ValidationCriteria({
            minTechnicalScore: 60,
            maxRiskLevel: 4,
            minCommunitySupport: 70,
            requiresHumanSponsorForFinancial: true,
            validationPeriod: PROPOSAL_VALIDATION_PERIOD * 2,
            maxProposalCost: 0.1 ether // Very limited financial scope
        });
    }

    /**
     * @notice Create default proposal templates
     */
    function _createDefaultTemplates() internal {
        // Would create default templates for each proposal type
        templateCount = 7; // Assume 7 default templates created
    }

    /**
     * @notice Update agent reputation based on proposal outcome
     * @param aiAgent Agent address
     * @param positive Whether this is positive or negative reputation change
     * @param points Points to add or subtract
     */
    function _updateAgentReputation(address aiAgent, bool positive, uint256 points) internal {
        AIAgentProfile storage agent = agentProfiles[aiAgent];
        uint256 oldReputation = agent.reputationPoints;

        if (positive) {
            agent.reputationPoints += points;
            if (agent.reputationPoints > MAX_REPUTATION_POINTS) {
                agent.reputationPoints = MAX_REPUTATION_POINTS;
            }
        } else {
            if (agent.reputationPoints >= points) {
                agent.reputationPoints -= points;
            } else {
                agent.reputationPoints = 0;
            }
        }

        // Update reputation level
        AIReputation newLevel;
        if (agent.reputationPoints <= 25) {
            newLevel = AIReputation.NOVICE;
        } else if (agent.reputationPoints <= 75) {
            newLevel = AIReputation.CONTRIBUTOR;
        } else if (agent.reputationPoints <= 150) {
            newLevel = AIReputation.EXPERT;
        } else if (agent.reputationPoints <= 300) {
            newLevel = AIReputation.MASTER;
        } else {
            newLevel = AIReputation.ARCHITECT;
        }

        agent.reputationLevel = newLevel;

        emit AIReputationUpdated(aiAgent, oldReputation, agent.reputationPoints, newLevel);
    }

    /**
     * @notice Get number of active proposals for agent
     * @param aiAgent Agent address
     * @return count Number of active proposals
     */
    function _getActiveProposalCount(address aiAgent) internal view returns (uint256 count) {
        uint256[] memory proposals = agentProposals[aiAgent];
        for (uint i = 0; i < proposals.length; i++) {
            AIProposal storage proposal = aiProposals[proposals[i]];
            if (!proposal.executed &&
                proposal.validationStatus != ProposalValidationStatus.REJECTED &&
                proposal.validationStatus != ProposalValidationStatus.EXPIRED) {
                count++;
            }
        }
    }
}