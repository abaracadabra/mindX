// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "./UniversalDAIO.sol";
import "./VotingAssetManager.sol";

/**
 * @title ProposalWillEngine
 * @notice Universal proposal/will system supporting any voting mechanism and cross-chain execution
 * @dev Handles intent-based proposals with AI assistance, complex voting formulas, and multi-chain coordination
 */
contract ProposalWillEngine is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant PROPOSAL_ADMIN_ROLE = keccak256("PROPOSAL_ADMIN_ROLE");
    bytes32 public constant PROPOSAL_MODERATOR_ROLE = keccak256("PROPOSAL_MODERATOR_ROLE");
    bytes32 public constant AI_VALIDATOR_ROLE = keccak256("AI_VALIDATOR_ROLE");
    bytes32 public constant CROSS_CHAIN_EXECUTOR_ROLE = keccak256("CROSS_CHAIN_EXECUTOR_ROLE");

    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    UniversalDAIO public immutable universalDAIO;
    VotingAssetManager public immutable votingAssetManager;

    // Proposal lifecycle states
    enum ProposalState {
        DRAFT,              // Being created/edited
        PENDING,            // Submitted, waiting for voting period
        ACTIVE,             // Voting is active
        QUEUED,             // Passed, queued for execution
        EXECUTED,           // Successfully executed
        CANCELLED,          // Cancelled before execution
        DEFEATED,           // Failed to meet threshold
        EXPIRED,            // Expired without execution
        EMERGENCY_PAUSED    // Emergency pause state
    }

    // Proposal types with different execution characteristics
    enum ProposalType {
        GOVERNANCE,         // Governance parameter changes
        TREASURY,           // Treasury allocation/spending
        EMERGENCY,          // Emergency actions
        CONSTITUTIONAL,     // Constitutional amendments
        OPERATIONAL,        // Operational changes
        INTEGRATION,        // External integrations
        UPGRADE,            // System upgrades
        CROSS_CHAIN,        // Cross-chain operations
        AI_DECISION,        // AI-assisted decisions
        CUSTOM              // Custom proposal types
    }

    // Voting mechanisms supported
    enum VotingMechanism {
        SIMPLE_MAJORITY,    // >50% approval
        SUPER_MAJORITY,     // Configurable supermajority (e.g., 67%)
        UNANIMITY,          // 100% approval
        QUADRATIC,          // Quadratic voting
        RANKED_CHOICE,      // Ranked choice voting
        APPROVAL,           // Approval voting (multiple choices)
        CONVICTION,         // Conviction voting (time-weighted)
        FUTARCHY,           // Prediction market based
        LIQUID_DEMOCRACY,   // Delegative democracy
        HOLOGRAPHIC,        // Holographic consensus
        AI_ASSISTED,        // AI-mediated consensus
        CUSTOM              // Custom voting mechanism
    }

    // Comprehensive proposal structure
    struct UniversalProposal {
        uint256 proposalId;             // Unique proposal identifier
        uint256 configId;               // DAIO configuration ID
        ProposalType proposalType;      // Type of proposal
        ProposalState state;            // Current state
        VotingMechanism votingMechanism; // Voting mechanism used

        // Human-readable content
        string title;                   // Proposal title
        string description;             // Detailed description
        string will;                    // Human-readable intent
        string rationale;               // Justification/reasoning
        string[] tags;                  // Categorization tags

        // Technical execution details
        bytes executionData;            // Technical execution payload
        address[] targetContracts;      // Contracts to call
        uint256[] values;               // ETH values per call
        bytes[] calldatas;              // Call data per contract
        string[] signatures;            // Function signatures

        // Proposer information
        address proposer;               // Address that created proposal
        uint256 proposalTime;           // Creation timestamp
        uint256 proposalBlock;          // Creation block number
        bytes32 proposalHash;           // Content hash for integrity

        // Voting configuration
        uint256 votingStart;            // Voting start time
        uint256 votingEnd;              // Voting end time
        uint256 votingDelay;            // Delay before voting starts
        uint256 votingPeriod;           // Duration of voting
        uint256 quorumThreshold;        // Required participation %
        uint256 approvalThreshold;      // Required approval %
        uint256 minimumVotingPower;     // Minimum power to propose
        address[] votingAssets;         // Assets that can vote
        mapping(address => uint256) assetWeights; // Weight per asset

        // Cross-chain execution
        uint256[] targetChains;         // Chains for execution
        mapping(uint256 => bytes) chainExecutionData; // Execution data per chain
        mapping(uint256 => bool) chainExecuted;       // Execution status per chain
        uint256 crossChainDelay;        // Cross-chain coordination delay

        // AI assistance
        bool aiAssisted;                // AI validation enabled
        address aiValidator;            // AI validator address
        bytes32 aiRecommendation;       // AI recommendation hash
        uint256 aiConfidenceScore;      // AI confidence (0-100)
        string aiAnalysis;              // AI analysis summary

        // Evolution integration
        UniversalDAIO.GovernanceStage requiredStage; // Minimum stage to execute
        bool triggersEvolution;         // Execution triggers evolution
        UniversalDAIO.GovernanceStage evolutionTarget; // Target evolution stage

        // Execution tracking
        uint256 executionETA;           // Estimated execution time
        uint256 executedAt;             // Actual execution time
        bytes executionResult;          // Execution result data
        bool executionSuccess;          // Execution success status
        string executionError;          // Error message if failed
    }

    // Voting record for proposals
    struct ProposalVote {
        mapping(address => VoteChoice) votes;           // Individual votes
        mapping(address => uint256) votingPower;       // Power used per voter
        mapping(address => uint256) voteTime;          // Vote timestamp
        mapping(address => bytes32) voteHash;          // Vote content hash
        uint256 totalVotingPower;                      // Total power eligible
        uint256 participationPower;                    // Actual participation power
        uint256 approvalPower;                         // Total approval power
        uint256 rejectionPower;                        // Total rejection power
        uint256 abstentionPower;                       // Total abstention power
        uint256 totalVotes;                           // Total number of votes
        bool quorumReached;                           // Quorum status
        bool thresholdMet;                            // Approval threshold status
    }

    // Vote choice with support for complex voting
    struct VoteChoice {
        bool hasVoted;                  // Whether address has voted
        uint8 choice;                   // Vote choice (0=against, 1=for, 2=abstain)
        uint256 power;                  // Voting power used
        uint256[] rankedChoices;        // For ranked choice voting
        mapping(uint256 => uint256) choiceWeights; // Weight per choice
        string reason;                  // Vote reasoning
        bytes signature;                // Vote signature for verification
        uint256 timestamp;              // Vote timestamp
        address delegate;               // If voting through delegation
        bool isAI;                      // Vote cast by AI
    }

    // Proposal execution queue
    struct ExecutionQueue {
        uint256[] queuedProposals;      // Proposals awaiting execution
        mapping(uint256 => uint256) executionTime; // Scheduled execution time
        mapping(uint256 => uint256) queuePosition; // Position in queue
        uint256 totalQueued;            // Total proposals in queue
        uint256 processingDelay;        // Base delay for processing
    }

    // Cross-chain coordination
    struct CrossChainExecution {
        uint256 proposalId;             // Source proposal ID
        uint256 sourceChain;            // Chain where proposal originated
        uint256[] targetChains;         // Target chains for execution
        mapping(uint256 => bool) chainConfirmation; // Confirmation per chain
        mapping(uint256 => bytes) chainResult;      // Result per chain
        uint256 requiredConfirmations;  // Required confirmations
        uint256 confirmationCount;      // Current confirmations
        uint256 coordinationDeadline;   // Deadline for coordination
        bool coordinationSuccess;       // All chains coordinated
        address coordinator;            // Cross-chain coordinator
    }

    // AI assistance integration
    struct AIAssistance {
        bool enabled;                   // AI assistance enabled
        address[] validators;           // AI validator addresses
        mapping(address => uint256) validatorWeights; // Weight per validator
        mapping(address => bool) validatorActive;     // Validator status
        uint256 minimumConfidence;      // Minimum confidence threshold
        uint256 consensusThreshold;     // AI consensus threshold
        bool humanOverride;             // Humans can override AI
        uint256 aiVotingWeight;         // Weight of AI votes
    }

    // Storage
    mapping(uint256 => mapping(uint256 => UniversalProposal)) public proposals;
    mapping(uint256 => mapping(uint256 => ProposalVote)) public proposalVotes;
    mapping(uint256 => ExecutionQueue) public executionQueues;
    mapping(bytes32 => CrossChainExecution) public crossChainExecutions;
    mapping(uint256 => AIAssistance) public aiAssistance;

    // Proposal tracking
    mapping(uint256 => uint256) public proposalCount;  // Proposals per config
    mapping(uint256 => uint256[]) public configProposals; // Proposal IDs per config
    mapping(address => uint256[]) public userProposals; // Proposals by user
    mapping(bytes32 => uint256) public proposalHashToId; // Hash to ID mapping

    // Proposal templates
    mapping(string => ProposalTemplate) public proposalTemplates;
    string[] public templateNames;

    // Proposal template structure
    struct ProposalTemplate {
        string name;                    // Template name
        ProposalType proposalType;      // Default proposal type
        VotingMechanism votingMechanism; // Default voting mechanism
        uint256 votingPeriod;           // Default voting period
        uint256 quorumThreshold;        // Default quorum
        uint256 approvalThreshold;      // Default approval threshold
        bool requiresAI;                // Requires AI validation
        uint256[] defaultChains;        // Default target chains
        bool active;                    // Template is active
    }

    // Global settings
    uint256 public defaultVotingDelay = 1 days;
    uint256 public defaultVotingPeriod = 7 days;
    uint256 public defaultQuorumThreshold = 10; // 10%
    uint256 public defaultApprovalThreshold = 51; // 51%
    uint256 public maxProposalsPerUser = 5;
    uint256 public proposalLifetime = 30 days;
    uint256 public executionDelay = 24 hours;
    bool public globalProposalPause = false;

    // Statistics
    uint256 public totalProposals;
    uint256 public totalExecutedProposals;
    uint256 public totalCrossChainExecutions;
    mapping(ProposalType => uint256) public proposalTypeStats;
    mapping(VotingMechanism => uint256) public votingMechanismStats;

    // Events
    event ProposalCreated(
        uint256 indexed configId,
        uint256 indexed proposalId,
        address indexed proposer,
        ProposalType proposalType,
        string title
    );

    event ProposalStateChanged(
        uint256 indexed configId,
        uint256 indexed proposalId,
        ProposalState oldState,
        ProposalState newState
    );

    event VoteCast(
        uint256 indexed configId,
        uint256 indexed proposalId,
        address indexed voter,
        uint8 choice,
        uint256 votingPower,
        string reason
    );

    event ProposalExecuted(
        uint256 indexed configId,
        uint256 indexed proposalId,
        bool success,
        bytes returnData
    );

    event CrossChainExecutionInitiated(
        bytes32 indexed executionId,
        uint256 indexed proposalId,
        uint256[] targetChains,
        address coordinator
    );

    event AIRecommendationReceived(
        uint256 indexed configId,
        uint256 indexed proposalId,
        address indexed aiValidator,
        bytes32 recommendation,
        uint256 confidenceScore
    );

    event ProposalTemplateCreated(
        string indexed templateName,
        ProposalType proposalType,
        VotingMechanism votingMechanism
    );

    event QuorumReached(
        uint256 indexed configId,
        uint256 indexed proposalId,
        uint256 participationPower,
        uint256 totalPower
    );

    event ThresholdMet(
        uint256 indexed configId,
        uint256 indexed proposalId,
        uint256 approvalPower,
        uint256 totalPower
    );

    modifier onlyProposalAdmin() {
        require(hasRole(PROPOSAL_ADMIN_ROLE, msg.sender), "Not proposal admin");
        _;
    }

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier proposalExists(uint256 configId, uint256 proposalId) {
        require(proposals[configId][proposalId].proposalTime > 0, "Proposal does not exist");
        _;
    }

    modifier notGloballyPaused() {
        require(!globalProposalPause, "Proposal system globally paused");
        _;
    }

    constructor(address _universalDAIO, address _votingAssetManager) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO address");
        require(_votingAssetManager != address(0), "Invalid VotingAssetManager address");

        universalDAIO = UniversalDAIO(_universalDAIO);
        votingAssetManager = VotingAssetManager(_votingAssetManager);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PROPOSAL_ADMIN_ROLE, msg.sender);
        _grantRole(PROPOSAL_MODERATOR_ROLE, msg.sender);
        _grantRole(AI_VALIDATOR_ROLE, msg.sender);
        _grantRole(CROSS_CHAIN_EXECUTOR_ROLE, msg.sender);

        _initializeDefaultTemplates();
    }

    /**
     * @notice Create universal proposal with intent-based description
     * @param configId Configuration ID
     * @param proposalType Type of proposal
     * @param votingMechanism Voting mechanism to use
     * @param title Proposal title
     * @param description Detailed description
     * @param will Human-readable intent
     * @param executionData Technical execution data
     * @param targetChains Target chains for execution
     * @return proposalId Created proposal ID
     */
    function createProposal(
        uint256 configId,
        ProposalType proposalType,
        VotingMechanism votingMechanism,
        string memory title,
        string memory description,
        string memory will,
        bytes memory executionData,
        uint256[] memory targetChains
    ) external validConfig(configId) notGloballyPaused nonReentrant returns (uint256 proposalId) {
        require(!paused(), "Proposal system paused");
        require(bytes(title).length > 0, "Title required");
        require(bytes(description).length > 0, "Description required");
        require(bytes(will).length > 0, "Will/intent required");

        // Check if user can create proposals
        require(_canCreateProposal(configId, msg.sender), "Cannot create proposal");

        // Check user proposal limits
        require(userProposals[msg.sender].length < maxProposalsPerUser, "Max proposals exceeded");

        proposalCount[configId]++;
        proposalId = proposalCount[configId];

        UniversalProposal storage proposal = proposals[configId][proposalId];
        proposal.proposalId = proposalId;
        proposal.configId = configId;
        proposal.proposalType = proposalType;
        proposal.state = ProposalState.DRAFT;
        proposal.votingMechanism = votingMechanism;

        // Content
        proposal.title = title;
        proposal.description = description;
        proposal.will = will;
        proposal.executionData = executionData;

        // Proposer information
        proposal.proposer = msg.sender;
        proposal.proposalTime = block.timestamp;
        proposal.proposalBlock = block.number;
        proposal.proposalHash = keccak256(abi.encode(title, description, will, executionData));

        // Voting configuration - use defaults or config-specific settings
        proposal.votingDelay = defaultVotingDelay;
        proposal.votingPeriod = defaultVotingPeriod;
        proposal.quorumThreshold = defaultQuorumThreshold;
        proposal.approvalThreshold = defaultApprovalThreshold;

        // Cross-chain configuration
        if (targetChains.length > 0) {
            proposal.targetChains = targetChains;
            proposal.crossChainDelay = 6 hours; // Default cross-chain delay
        }

        // Set voting assets
        address[] memory assets = votingAssetManager.getVotingAssets(configId);
        proposal.votingAssets = assets;

        // Set required governance stage
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);
        proposal.requiredStage = config.currentStage;

        // AI assistance configuration
        proposal.aiAssisted = aiAssistance[configId].enabled;
        if (proposal.aiAssisted) {
            proposal.aiValidator = aiAssistance[configId].validators.length > 0 ?
                                  aiAssistance[configId].validators[0] : address(0);
        }

        // Update tracking
        configProposals[configId].push(proposalId);
        userProposals[msg.sender].push(proposalId);
        proposalHashToId[proposal.proposalHash] = proposalId;

        totalProposals++;
        proposalTypeStats[proposalType]++;

        emit ProposalCreated(configId, proposalId, msg.sender, proposalType, title);

        return proposalId;
    }

    /**
     * @notice Submit proposal for voting
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     */
    function submitProposal(
        uint256 configId,
        uint256 proposalId
    ) external validConfig(configId) proposalExists(configId, proposalId) {
        UniversalProposal storage proposal = proposals[configId][proposalId];
        require(proposal.state == ProposalState.DRAFT, "Proposal not in draft state");
        require(proposal.proposer == msg.sender, "Not proposal author");

        // Validate proposal content and execution data
        require(_validateProposal(configId, proposalId), "Proposal validation failed");

        // Set voting times
        proposal.votingStart = block.timestamp + proposal.votingDelay;
        proposal.votingEnd = proposal.votingStart + proposal.votingPeriod;
        proposal.state = ProposalState.PENDING;

        // Calculate total voting power for quorum
        _calculateTotalVotingPower(configId, proposalId);

        // Request AI validation if enabled
        if (proposal.aiAssisted && proposal.aiValidator != address(0)) {
            _requestAIValidation(configId, proposalId);
        }

        emit ProposalStateChanged(configId, proposalId, ProposalState.DRAFT, ProposalState.PENDING);
    }

    /**
     * @notice Cast vote on proposal
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     * @param choice Vote choice (0=against, 1=for, 2=abstain)
     * @param reason Vote reasoning
     * @param rankedChoices Ranked choices (for ranked choice voting)
     */
    function castVote(
        uint256 configId,
        uint256 proposalId,
        uint8 choice,
        string memory reason,
        uint256[] memory rankedChoices
    ) external validConfig(configId) proposalExists(configId, proposalId) nonReentrant {
        require(!paused(), "Proposal system paused");
        require(choice <= 2, "Invalid choice");

        UniversalProposal storage proposal = proposals[configId][proposalId];
        require(proposal.state == ProposalState.ACTIVE, "Voting not active");
        require(block.timestamp >= proposal.votingStart && block.timestamp <= proposal.votingEnd, "Not in voting period");

        ProposalVote storage vote = proposalVotes[configId][proposalId];
        require(!vote.votes[msg.sender].hasVoted, "Already voted");

        // Calculate voting power
        uint256 votingPower = votingAssetManager.calculateVotingPower(configId, msg.sender);
        require(votingPower > 0, "No voting power");

        // Record vote
        VoteChoice storage voteChoice = vote.votes[msg.sender];
        voteChoice.hasVoted = true;
        voteChoice.choice = choice;
        voteChoice.power = votingPower;
        voteChoice.reason = reason;
        voteChoice.timestamp = block.timestamp;

        // Handle ranked choices for complex voting
        if (proposal.votingMechanism == VotingMechanism.RANKED_CHOICE && rankedChoices.length > 0) {
            voteChoice.rankedChoices = rankedChoices;
        }

        // Update vote tallies
        vote.votingPower[msg.sender] = votingPower;
        vote.voteTime[msg.sender] = block.timestamp;
        vote.participationPower += votingPower;
        vote.totalVotes++;

        if (choice == 0) {
            vote.rejectionPower += votingPower;
        } else if (choice == 1) {
            vote.approvalPower += votingPower;
        } else {
            vote.abstentionPower += votingPower;
        }

        // Check quorum and threshold
        _checkQuorumAndThreshold(configId, proposalId);

        emit VoteCast(configId, proposalId, msg.sender, choice, votingPower, reason);
    }

    /**
     * @notice Execute proposal after voting concludes
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     */
    function executeProposal(
        uint256 configId,
        uint256 proposalId
    ) external validConfig(configId) proposalExists(configId, proposalId) nonReentrant {
        UniversalProposal storage proposal = proposals[configId][proposalId];
        require(proposal.state == ProposalState.QUEUED, "Proposal not queued for execution");
        require(block.timestamp >= proposal.executionETA, "Execution not yet available");

        // Validate governance stage requirement
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);
        require(uint256(config.currentStage) >= uint256(proposal.requiredStage), "Insufficient governance stage");

        proposal.state = ProposalState.EXECUTED;
        proposal.executedAt = block.timestamp;

        bool success = true;
        bytes memory returnData;

        try {
            // Execute proposal
            if (proposal.targetContracts.length > 0) {
                (success, returnData) = _executeProposalCalls(configId, proposalId);
            } else {
                (success, returnData) = _executeProposalData(configId, proposalId);
            }

            proposal.executionSuccess = success;
            proposal.executionResult = returnData;

            if (!success && returnData.length > 0) {
                proposal.executionError = string(returnData);
            }

        } catch Error(string memory error) {
            success = false;
            proposal.executionSuccess = false;
            proposal.executionError = error;
        }

        // Handle cross-chain execution
        if (proposal.targetChains.length > 0) {
            _initiateCrossChainExecution(configId, proposalId);
        }

        // Trigger evolution if required
        if (proposal.triggersEvolution && success) {
            universalDAIO.evolveGovernance(configId, false);
        }

        totalExecutedProposals++;

        emit ProposalExecuted(configId, proposalId, success, returnData);
    }

    /**
     * @notice Provide AI recommendation for proposal
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     * @param recommendation AI recommendation hash
     * @param confidenceScore Confidence score (0-100)
     * @param analysis AI analysis summary
     */
    function provideAIRecommendation(
        uint256 configId,
        uint256 proposalId,
        bytes32 recommendation,
        uint256 confidenceScore,
        string memory analysis
    ) external validConfig(configId) proposalExists(configId, proposalId) {
        require(hasRole(AI_VALIDATOR_ROLE, msg.sender), "Not AI validator");
        require(confidenceScore <= 100, "Invalid confidence score");

        UniversalProposal storage proposal = proposals[configId][proposalId];
        require(proposal.aiAssisted, "AI assistance not enabled");
        require(proposal.aiValidator == msg.sender || proposal.aiValidator == address(0), "Not authorized AI validator");

        proposal.aiRecommendation = recommendation;
        proposal.aiConfidenceScore = confidenceScore;
        proposal.aiAnalysis = analysis;

        emit AIRecommendationReceived(configId, proposalId, msg.sender, recommendation, confidenceScore);
    }

    /**
     * @notice Create proposal template
     * @param name Template name
     * @param proposalType Default proposal type
     * @param votingMechanism Default voting mechanism
     * @param votingPeriod Default voting period
     * @param quorumThreshold Default quorum threshold
     * @param approvalThreshold Default approval threshold
     */
    function createProposalTemplate(
        string memory name,
        ProposalType proposalType,
        VotingMechanism votingMechanism,
        uint256 votingPeriod,
        uint256 quorumThreshold,
        uint256 approvalThreshold
    ) external onlyProposalAdmin {
        require(bytes(name).length > 0, "Template name required");
        require(!proposalTemplates[name].active, "Template already exists");
        require(votingPeriod > 0 && votingPeriod <= 30 days, "Invalid voting period");
        require(quorumThreshold <= 100 && approvalThreshold <= 100, "Invalid thresholds");

        ProposalTemplate storage template = proposalTemplates[name];
        template.name = name;
        template.proposalType = proposalType;
        template.votingMechanism = votingMechanism;
        template.votingPeriod = votingPeriod;
        template.quorumThreshold = quorumThreshold;
        template.approvalThreshold = approvalThreshold;
        template.active = true;

        templateNames.push(name);

        emit ProposalTemplateCreated(name, proposalType, votingMechanism);
    }

    /**
     * @notice Configure AI assistance for configuration
     * @param configId Configuration ID
     * @param enabled Whether AI assistance is enabled
     * @param validators AI validator addresses
     * @param minimumConfidence Minimum confidence threshold
     * @param aiVotingWeight Weight of AI votes
     */
    function configureAIAssistance(
        uint256 configId,
        bool enabled,
        address[] memory validators,
        uint256 minimumConfidence,
        uint256 aiVotingWeight
    ) external validConfig(configId) onlyProposalAdmin {
        require(minimumConfidence <= 100, "Invalid confidence threshold");
        require(aiVotingWeight <= 49, "AI voting weight too high"); // Max 49% to maintain human control

        AIAssistance storage ai = aiAssistance[configId];
        ai.enabled = enabled;
        ai.validators = validators;
        ai.minimumConfidence = minimumConfidence;
        ai.aiVotingWeight = aiVotingWeight;
        ai.consensusThreshold = 67; // Default 2/3 consensus
        ai.humanOverride = true;

        // Set validator weights
        uint256 weightPerValidator = validators.length > 0 ? 100 / validators.length : 0;
        for (uint i = 0; i < validators.length; i++) {
            ai.validatorWeights[validators[i]] = weightPerValidator;
            ai.validatorActive[validators[i]] = true;
        }
    }

    /**
     * @notice Get proposal details
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     * @return title Proposal title
     * @return description Proposal description
     * @return proposer Proposer address
     * @return state Current state
     * @return votingStart Voting start time
     * @return votingEnd Voting end time
     */
    function getProposal(uint256 configId, uint256 proposalId) external view validConfig(configId) returns (
        string memory title,
        string memory description,
        address proposer,
        ProposalState state,
        uint256 votingStart,
        uint256 votingEnd
    ) {
        UniversalProposal storage proposal = proposals[configId][proposalId];
        return (
            proposal.title,
            proposal.description,
            proposal.proposer,
            proposal.state,
            proposal.votingStart,
            proposal.votingEnd
        );
    }

    /**
     * @notice Get proposal voting results
     * @param configId Configuration ID
     * @param proposalId Proposal ID
     * @return approvalPower Total approval voting power
     * @return rejectionPower Total rejection voting power
     * @return abstentionPower Total abstention voting power
     * @return participationPower Total participation power
     * @return quorumReached Whether quorum was reached
     * @return thresholdMet Whether approval threshold was met
     */
    function getProposalVotes(uint256 configId, uint256 proposalId) external view validConfig(configId) returns (
        uint256 approvalPower,
        uint256 rejectionPower,
        uint256 abstentionPower,
        uint256 participationPower,
        bool quorumReached,
        bool thresholdMet
    ) {
        ProposalVote storage vote = proposalVotes[configId][proposalId];
        return (
            vote.approvalPower,
            vote.rejectionPower,
            vote.abstentionPower,
            vote.participationPower,
            vote.quorumReached,
            vote.thresholdMet
        );
    }

    /**
     * @notice Update global proposal settings
     */
    function updateGlobalSettings(
        uint256 _defaultVotingDelay,
        uint256 _defaultVotingPeriod,
        uint256 _defaultQuorumThreshold,
        uint256 _defaultApprovalThreshold,
        uint256 _maxProposalsPerUser,
        uint256 _proposalLifetime,
        uint256 _executionDelay
    ) external onlyProposalAdmin {
        defaultVotingDelay = _defaultVotingDelay;
        defaultVotingPeriod = _defaultVotingPeriod;
        defaultQuorumThreshold = _defaultQuorumThreshold;
        defaultApprovalThreshold = _defaultApprovalThreshold;
        maxProposalsPerUser = _maxProposalsPerUser;
        proposalLifetime = _proposalLifetime;
        executionDelay = _executionDelay;
    }

    /**
     * @notice Set global proposal pause
     * @param paused Whether proposals are globally paused
     */
    function setGlobalProposalPause(bool paused) external onlyProposalAdmin {
        globalProposalPause = paused;
    }

    /**
     * @notice Pause proposal system
     */
    function pauseProposalSystem() external onlyProposalAdmin {
        _pause();
    }

    /**
     * @notice Unpause proposal system
     */
    function unpauseProposalSystem() external onlyProposalAdmin {
        _unpause();
    }

    // Internal Functions

    /**
     * @notice Check if user can create proposal
     */
    function _canCreateProposal(uint256 configId, address user) internal view returns (bool) {
        uint256 votingPower = votingAssetManager.getTotalVotingPower(configId, user);
        return votingPower >= 1 ether; // Minimum 1 ETH equivalent voting power
    }

    /**
     * @notice Validate proposal before submission
     */
    function _validateProposal(uint256 configId, uint256 proposalId) internal view returns (bool) {
        UniversalProposal storage proposal = proposals[configId][proposalId];

        // Check basic requirements
        if (bytes(proposal.title).length == 0 || bytes(proposal.will).length == 0) {
            return false;
        }

        // Check execution data validity
        if (proposal.executionData.length == 0 && proposal.targetContracts.length == 0) {
            return false; // Must have some execution method
        }

        return true;
    }

    /**
     * @notice Calculate total voting power for proposal
     */
    function _calculateTotalVotingPower(uint256 configId, uint256 proposalId) internal {
        ProposalVote storage vote = proposalVotes[configId][proposalId];

        // Calculate total eligible voting power
        uint256 totalPower = 0;
        address[] memory assets = votingAssetManager.getVotingAssets(configId);

        // Simplified calculation - would iterate through all eligible voters
        vote.totalVotingPower = 1000000 ether; // Placeholder total
    }

    /**
     * @notice Request AI validation for proposal
     */
    function _requestAIValidation(uint256 configId, uint256 proposalId) internal {
        // Implementation would integrate with AI validation service
        // This is a placeholder for AI integration
    }

    /**
     * @notice Check quorum and threshold status
     */
    function _checkQuorumAndThreshold(uint256 configId, uint256 proposalId) internal {
        UniversalProposal storage proposal = proposals[configId][proposalId];
        ProposalVote storage vote = proposalVotes[configId][proposalId];

        // Check quorum
        uint256 quorumRequired = (vote.totalVotingPower * proposal.quorumThreshold) / 100;
        if (!vote.quorumReached && vote.participationPower >= quorumRequired) {
            vote.quorumReached = true;
            emit QuorumReached(configId, proposalId, vote.participationPower, vote.totalVotingPower);
        }

        // Check approval threshold
        if (vote.quorumReached) {
            uint256 approvalRequired = (vote.participationPower * proposal.approvalThreshold) / 100;
            if (!vote.thresholdMet && vote.approvalPower >= approvalRequired) {
                vote.thresholdMet = true;
                emit ThresholdMet(configId, proposalId, vote.approvalPower, vote.participationPower);
            }
        }

        // Update proposal state if voting ended
        if (block.timestamp > proposal.votingEnd) {
            _finalizeVoting(configId, proposalId);
        }
    }

    /**
     * @notice Finalize voting and update proposal state
     */
    function _finalizeVoting(uint256 configId, uint256 proposalId) internal {
        UniversalProposal storage proposal = proposals[configId][proposalId];
        ProposalVote storage vote = proposalVotes[configId][proposalId];

        ProposalState newState;

        if (!vote.quorumReached) {
            newState = ProposalState.DEFEATED;
        } else if (!vote.thresholdMet) {
            newState = ProposalState.DEFEATED;
        } else {
            newState = ProposalState.QUEUED;
            proposal.executionETA = block.timestamp + executionDelay;
        }

        ProposalState oldState = proposal.state;
        proposal.state = newState;

        emit ProposalStateChanged(configId, proposalId, oldState, newState);
    }

    /**
     * @notice Execute proposal calls
     */
    function _executeProposalCalls(uint256 configId, uint256 proposalId) internal returns (bool success, bytes memory returnData) {
        UniversalProposal storage proposal = proposals[configId][proposalId];

        success = true;
        bytes memory allReturnData;

        for (uint i = 0; i < proposal.targetContracts.length; i++) {
            address target = proposal.targetContracts[i];
            uint256 value = i < proposal.values.length ? proposal.values[i] : 0;
            bytes memory calldata_ = i < proposal.calldatas.length ? proposal.calldatas[i] : "";

            (bool callSuccess, bytes memory callReturnData) = target.call{value: value}(calldata_);

            if (!callSuccess) {
                success = false;
                return (false, callReturnData);
            }

            allReturnData = abi.encodePacked(allReturnData, callReturnData);
        }

        return (success, allReturnData);
    }

    /**
     * @notice Execute proposal data
     */
    function _executeProposalData(uint256 configId, uint256 proposalId) internal returns (bool success, bytes memory returnData) {
        // Implementation would handle direct execution data
        return (true, "Proposal executed");
    }

    /**
     * @notice Initiate cross-chain execution
     */
    function _initiateCrossChainExecution(uint256 configId, uint256 proposalId) internal {
        UniversalProposal storage proposal = proposals[configId][proposalId];

        bytes32 executionId = keccak256(abi.encode(configId, proposalId, block.timestamp));

        CrossChainExecution storage execution = crossChainExecutions[executionId];
        execution.proposalId = proposalId;
        execution.sourceChain = block.chainid;
        execution.targetChains = proposal.targetChains;
        execution.requiredConfirmations = proposal.targetChains.length;
        execution.coordinationDeadline = block.timestamp + 24 hours;
        execution.coordinator = msg.sender;

        totalCrossChainExecutions++;

        emit CrossChainExecutionInitiated(executionId, proposalId, proposal.targetChains, msg.sender);
    }

    /**
     * @notice Initialize default proposal templates
     */
    function _initializeDefaultTemplates() internal {
        // Treasury proposal template
        templateNames.push("Treasury");
        proposalTemplates["Treasury"].name = "Treasury";
        proposalTemplates["Treasury"].proposalType = ProposalType.TREASURY;
        proposalTemplates["Treasury"].votingMechanism = VotingMechanism.SUPER_MAJORITY;
        proposalTemplates["Treasury"].votingPeriod = 7 days;
        proposalTemplates["Treasury"].quorumThreshold = 20;
        proposalTemplates["Treasury"].approvalThreshold = 67;
        proposalTemplates["Treasury"].active = true;

        // Emergency proposal template
        templateNames.push("Emergency");
        proposalTemplates["Emergency"].name = "Emergency";
        proposalTemplates["Emergency"].proposalType = ProposalType.EMERGENCY;
        proposalTemplates["Emergency"].votingMechanism = VotingMechanism.SUPER_MAJORITY;
        proposalTemplates["Emergency"].votingPeriod = 1 days;
        proposalTemplates["Emergency"].quorumThreshold = 15;
        proposalTemplates["Emergency"].approvalThreshold = 75;
        proposalTemplates["Emergency"].active = true;
    }
}