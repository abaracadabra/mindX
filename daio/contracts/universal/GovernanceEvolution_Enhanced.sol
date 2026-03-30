// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./UniversalDAIO.sol";
import "../daio/governance/ExecutiveGovernance.sol";
import "../daio/constitution/DAIO_Constitution_Enhanced.sol";
import "../daio/treasury/Treasury.sol";

/**
 * @title GovernanceEvolution_Enhanced
 * @notice Enhanced governance evolution system with CEO + Seven Soldiers integration
 * @dev Manages automated governance stage transitions with executive oversight and constitutional compliance
 *
 * Features:
 * - CEO + Seven Soldiers executive approval for evolution
 * - Constitutional compliance validation during evolution
 * - Production-ready monitoring and alerting
 * - Treasury value and member count trigger validation
 * - Corporate governance patterns for Fortune 500 deployment
 * - Emergency evolution procedures with constitutional safeguards
 * - Cross-chain evolution coordination
 * - AI integration with governance oversight
 *
 * Evolution Stages:
 * 1. DICTATOR → MARRIAGE (Single CEO to CEO + Partner)
 * 2. MARRIAGE → TRIUMVIRATE (CEO + Partner to CEO + Seven Soldiers)
 * 3. TRIUMVIRATE → FEDERATION (Executive team to multi-chain governance)
 * 4. FEDERATION → AUTONOMOUS (Human oversight to AI-driven governance)
 *
 * @author DAIO Development Team
 */
contract GovernanceEvolution_Enhanced is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant EVOLUTION_MANAGER_ROLE = keccak256("EVOLUTION_MANAGER_ROLE");
    bytes32 public constant TRIGGER_VALIDATOR_ROLE = keccak256("TRIGGER_VALIDATOR_ROLE");
    bytes32 public constant EMERGENCY_EVOLUTION_ROLE = keccak256("EMERGENCY_EVOLUTION_ROLE");
    bytes32 public constant AI_INTEGRATION_ROLE = keccak256("AI_INTEGRATION_ROLE");

    // =============================================================
    //                         INTERFACES
    // =============================================================

    UniversalDAIO public immutable universalDAIO;
    ExecutiveGovernance public immutable executiveGovernance;
    DAIO_Constitution_Enhanced public immutable constitution;
    Treasury public immutable treasury;

    // =============================================================
    //                         TYPES
    // =============================================================

    enum EvolutionStatus {
        PENDING,        // Evolution criteria not met
        TRIGGERED,      // Criteria met, awaiting execution
        EXECUTIVE_REVIEW, // Under executive review
        IN_PROGRESS,    // Evolution in progress
        COMPLETED,      // Successfully completed
        FAILED,         // Evolution failed
        CANCELLED,      // Cancelled by stakeholders
        EMERGENCY,      // Emergency evolution in progress
        CONSTITUTIONAL_VIOLATION // Blocked due to constitutional constraints
    }

    enum ValidationMethod {
        AUTOMATIC,              // Automatic when triggers met
        EXECUTIVE_APPROVAL,     // Requires CEO + Seven Soldiers approval
        COMMUNITY_VOTE,         // Requires community approval
        CONSTITUTIONAL_REVIEW,  // Requires constitutional compliance review
        HYBRID,                 // Multiple validation methods
        TIME_DELAYED,          // Automatic after time delay
        AI_CONSENSUS           // AI-driven consensus validation
    }

    enum TriggerType {
        TIME_BASED,            // Time elapsed since last evolution
        VALUE_BASED,           // Treasury value reached threshold
        MEMBER_BASED,          // Member count reached threshold
        PROPOSAL_BASED,        // Proposal activity reached threshold
        PERFORMANCE_BASED,     // Governance performance metrics
        CONSTITUTIONAL,        // Constitutional compliance requirement
        EXECUTIVE_INITIATED,   // CEO/Seven Soldiers initiated
        AI_RECOMMENDED,        // AI recommendation based
        CRISIS_RESPONSE        // Emergency crisis response
    }

    // =============================================================
    //                         STRUCTS
    // =============================================================

    struct EnhancedEvolutionTrigger {
        // Basic triggers
        uint256 timeThreshold;                  // Minimum time between evolutions
        uint256 valueThreshold;                 // Treasury value threshold
        uint256 memberThreshold;                // Active member threshold
        uint256 proposalThreshold;              // Proposal count threshold
        uint256 performanceThreshold;           // Governance performance score

        // Validation requirements
        ValidationMethod validationMethod;
        uint256 executiveApprovalThreshold;     // Number of executives required
        uint256 communityVoteThreshold;         // % community approval needed
        uint256 validationDelay;                // Delay before auto-execution
        uint256 stakeholderVetoPeriod;          // Period for stakeholder veto

        // Constitutional requirements
        bool requiresConstitutionalReview;      // Must pass constitutional validation
        bool allowsConstitutionalAmendment;     // Can modify constitution during evolution
        uint256 constitutionalQuorum;           // Quorum for constitutional changes

        // Advanced features
        bool enablesAIIntegration;              // Evolution enables AI participation
        bool requiresMultiChainConsensus;       // Multi-chain coordination required
        bool allowsEmergencyBypass;             // Emergency evolution possible
        uint256 rollbackWindow;                 // Time window for evolution rollback
    }

    struct EvolutionProgress {
        uint256 configId;
        UniversalDAIO.GovernanceStage fromStage;
        UniversalDAIO.GovernanceStage toStage;
        EvolutionStatus status;
        TriggerType triggerType;
        uint256 triggeredAt;
        uint256 completedAt;
        uint256 progressPercentage;
        string[] completedSteps;
        string[] pendingSteps;
        bytes32 evolutionHash;
        address initiatedBy;
        string triggerReason;
    }

    struct ExecutiveEvolutionVote {
        mapping(address => bool) hasVoted;
        mapping(address => bool) voteChoice;
        mapping(address => string) voteReason;
        uint256 approvalVotes;
        uint256 rejectionVotes;
        uint256 votingDeadline;
        bool executed;
        bool passed;
        uint256 requiredApprovals;
    }

    struct ConstitutionalReview {
        bool reviewRequired;
        bool reviewCompleted;
        bool complianceApproved;
        string[] violationReasons;
        uint256 reviewStarted;
        uint256 reviewCompleted;
        address reviewer;
        bytes32 complianceHash;
    }

    struct EvolutionMetrics {
        uint256 totalEvolutions;
        uint256 successfulEvolutions;
        uint256 failedEvolutions;
        uint256 emergencyEvolutions;
        uint256 averageEvolutionDuration;
        uint256 lastEvolutionTimestamp;
        mapping(UniversalDAIO.GovernanceStage => uint256) stageEvolutionCounts;
        mapping(TriggerType => uint256) triggerTypeCounts;
    }

    struct EvolutionStep {
        string stepName;
        string description;
        bytes executionData;
        bool required;
        bool completed;
        uint256 completedAt;
        address completedBy;
        bytes result;
        uint256 estimatedGas;
        bool requiresExecutiveApproval;
        bool requiresConstitutionalValidation;
    }

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Evolution configuration
    mapping(uint256 => EnhancedEvolutionTrigger) public enhancedTriggers;
    mapping(uint256 => EvolutionProgress) public evolutionProgress;
    mapping(uint256 => ExecutiveEvolutionVote) public executiveVotes;
    mapping(uint256 => ConstitutionalReview) public constitutionalReviews;
    mapping(uint256 => EvolutionStep[]) public evolutionSteps;

    // Metrics and monitoring
    EvolutionMetrics public metrics;
    mapping(uint256 => uint256[]) public evolutionHistory;
    mapping(address => uint256[]) public initiatorHistory;

    // Global settings
    uint256 public defaultExecutiveVotingPeriod = 3 days;
    uint256 public defaultCommunityVotingPeriod = 7 days;
    uint256 public emergencyEvolutionDelay = 24 hours;
    uint256 public constitutionalReviewPeriod = 5 days;
    uint256 public evolutionCooldownPeriod = 30 days;
    uint256 public maxEvolutionRetries = 3;

    // Performance tracking
    mapping(uint256 => uint256) public governancePerformanceScores;
    mapping(uint256 => uint256) public lastActivityTimestamp;

    // =============================================================
    //                         EVENTS
    // =============================================================

    event EvolutionTriggered(
        uint256 indexed configId,
        UniversalDAIO.GovernanceStage fromStage,
        UniversalDAIO.GovernanceStage toStage,
        TriggerType triggerType,
        address indexed initiator,
        string reason
    );

    event ExecutiveEvolutionVoteStarted(
        uint256 indexed configId,
        uint256 deadline,
        uint256 requiredApprovals
    );

    event ExecutiveVoteCast(
        uint256 indexed configId,
        address indexed executive,
        bool approval,
        string reason
    );

    event ConstitutionalReviewInitiated(
        uint256 indexed configId,
        address indexed reviewer,
        string[] reviewCriteria
    );

    event ConstitutionalReviewCompleted(
        uint256 indexed configId,
        bool approved,
        string[] findings
    );

    event EvolutionStepExecuted(
        uint256 indexed configId,
        string stepName,
        address indexed executor,
        uint256 gasUsed,
        bytes result
    );

    event EvolutionCompleted(
        uint256 indexed configId,
        UniversalDAIO.GovernanceStage newStage,
        uint256 duration,
        uint256 totalSteps,
        address indexed initiator
    );

    event EvolutionFailed(
        uint256 indexed configId,
        EvolutionStatus finalStatus,
        string reason,
        uint256 failureStep
    );

    event EmergencyEvolutionActivated(
        uint256 indexed configId,
        address indexed initiator,
        string emergencyReason,
        bool bypassedValidation
    );

    event EvolutionRollback(
        uint256 indexed configId,
        UniversalDAIO.GovernanceStage revertedStage,
        string rollbackReason
    );

    event AIIntegrationEnabled(
        uint256 indexed configId,
        address aiAgent,
        uint256 votingWeight
    );

    event CrossChainEvolutionSynced(
        uint256 indexed configId,
        uint256[] chainIds,
        bytes32 syncHash
    );

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address _universalDAIO,
        address _executiveGovernance,
        address _constitution,
        address _treasury
    ) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO");
        require(_executiveGovernance != address(0), "Invalid ExecutiveGovernance");
        require(_constitution != address(0), "Invalid Constitution");
        require(_treasury != address(0), "Invalid Treasury");

        universalDAIO = UniversalDAIO(_universalDAIO);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        constitution = DAIO_Constitution_Enhanced(_constitution);
        treasury = Treasury(_treasury);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(EVOLUTION_MANAGER_ROLE, msg.sender);
        _grantRole(TRIGGER_VALIDATOR_ROLE, msg.sender);
        _grantRole(EMERGENCY_EVOLUTION_ROLE, msg.sender);
        _grantRole(AI_INTEGRATION_ROLE, msg.sender);
    }

    // =============================================================
    //                      MAIN FUNCTIONS
    // =============================================================

    /**
     * @notice Configure enhanced evolution triggers with executive oversight
     */
    function configureEvolutionTriggers(
        uint256 configId,
        EnhancedEvolutionTrigger memory trigger
    ) external validConfig(configId) onlyRole(EVOLUTION_MANAGER_ROLE) {
        require(trigger.timeThreshold > 0 || trigger.valueThreshold > 0, "At least one trigger required");
        require(trigger.executiveApprovalThreshold <= 8, "Invalid executive threshold"); // CEO + 7 Soldiers
        require(trigger.communityVoteThreshold <= 100, "Invalid vote threshold");

        // Validate constitutional requirements
        if (trigger.requiresConstitutionalReview) {
            require(
                constitution.validateEvolutionParameters(
                    configId,
                    abi.encode(trigger)
                ),
                "Constitutional validation failed"
            );
        }

        enhancedTriggers[configId] = trigger;
        _initializeEvolutionSteps(configId);

        emit EvolutionTriggered(configId,
            universalDAIO.getConfiguration(configId).currentStage,
            universalDAIO.getConfiguration(configId).targetStage,
            TriggerType.TIME_BASED, // Default for configuration
            msg.sender,
            "Evolution triggers configured"
        );
    }

    /**
     * @notice Check triggers and initiate evolution with executive approval
     */
    function checkAndTriggerEvolution(
        uint256 configId,
        TriggerType triggerType,
        bytes memory triggerData,
        string memory reason
    ) external validConfig(configId) returns (bool triggered) {
        require(!paused(), "Evolution system paused");

        EvolutionProgress storage progress = evolutionProgress[configId];
        require(progress.status != EvolutionStatus.IN_PROGRESS, "Evolution already in progress");

        // Check cooldown period
        if (evolutionHistory[configId].length > 0) {
            uint256 lastEvolution = evolutionHistory[configId][evolutionHistory[configId].length - 1];
            require(block.timestamp >= lastEvolution + evolutionCooldownPeriod, "Evolution cooldown active");
        }

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);

        // Validate triggers based on type
        bool triggerValid = _validateSpecificTrigger(configId, triggerType, trigger, config, triggerData);
        require(triggerValid, "Evolution triggers not met");

        // Initialize evolution progress
        progress.configId = configId;
        progress.fromStage = config.currentStage;
        progress.toStage = config.targetStage;
        progress.status = EvolutionStatus.TRIGGERED;
        progress.triggerType = triggerType;
        progress.triggeredAt = block.timestamp;
        progress.initiatedBy = msg.sender;
        progress.triggerReason = reason;
        progress.progressPercentage = 0;
        progress.evolutionHash = keccak256(abi.encode(configId, config, block.timestamp));

        metrics.totalEvolutions++;
        metrics.triggerTypeCounts[triggerType]++;

        emit EvolutionTriggered(configId, config.currentStage, config.targetStage, triggerType, msg.sender, reason);

        // Start validation process
        if (trigger.validationMethod == ValidationMethod.EXECUTIVE_APPROVAL) {
            _startExecutiveApproval(configId, trigger);
        } else if (trigger.requiresConstitutionalReview) {
            _startConstitutionalReview(configId);
        } else if (trigger.validationMethod == ValidationMethod.AUTOMATIC) {
            _executeEvolution(configId);
        }

        return true;
    }

    /**
     * @notice CEO or Seven Soldiers can initiate evolution directly
     */
    function initiateExecutiveEvolution(
        uint256 configId,
        string memory executiveReason
    ) external validConfig(configId) {
        require(
            executiveGovernance.hasExecutiveApproval(msg.sender) ||
            executiveGovernance.isCEO(msg.sender),
            "Requires executive authority"
        );

        require(!paused(), "Evolution system paused");

        EvolutionProgress storage progress = evolutionProgress[configId];
        progress.status = EvolutionStatus.EXECUTIVE_REVIEW;
        progress.triggeredAt = block.timestamp;
        progress.initiatedBy = msg.sender;
        progress.triggerReason = executiveReason;
        progress.triggerType = TriggerType.EXECUTIVE_INITIATED;

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];
        _startExecutiveApproval(configId, trigger);

        emit EvolutionTriggered(
            configId,
            progress.fromStage,
            progress.toStage,
            TriggerType.EXECUTIVE_INITIATED,
            msg.sender,
            executiveReason
        );
    }

    /**
     * @notice Cast executive vote on evolution
     */
    function castExecutiveVote(
        uint256 configId,
        bool approval,
        string memory reason
    ) external validConfig(configId) {
        require(
            executiveGovernance.hasExecutiveApproval(msg.sender) ||
            executiveGovernance.isCEO(msg.sender),
            "Not an executive"
        );

        ExecutiveEvolutionVote storage vote = executiveVotes[configId];
        require(block.timestamp <= vote.votingDeadline, "Voting period ended");
        require(!vote.hasVoted[msg.sender], "Already voted");

        vote.hasVoted[msg.sender] = true;
        vote.voteChoice[msg.sender] = approval;
        vote.voteReason[msg.sender] = reason;

        if (approval) {
            vote.approvalVotes++;
        } else {
            vote.rejectionVotes++;
        }

        emit ExecutiveVoteCast(configId, msg.sender, approval, reason);

        // Check if threshold reached
        if (vote.approvalVotes >= vote.requiredApprovals) {
            vote.passed = true;
            evolutionProgress[configId].status = EvolutionStatus.IN_PROGRESS;
            _executeEvolution(configId);
        }
    }

    /**
     * @notice Emergency evolution with CEO override
     */
    function emergencyEvolution(
        uint256 configId,
        string memory emergencyJustification
    ) external validConfig(configId) {
        require(
            executiveGovernance.isCEO(msg.sender) ||
            hasRole(EMERGENCY_EVOLUTION_ROLE, msg.sender),
            "Not authorized for emergency evolution"
        );

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];
        require(trigger.allowsEmergencyBypass, "Emergency evolution disabled");

        // Validate emergency doesn't violate constitutional constraints
        require(
            constitution.validateEmergencyAction(
                msg.sender,
                address(this),
                abi.encodeWithSignature("evolveGovernance(uint256,bool)", configId, true)
            ),
            "Emergency evolution violates constitution"
        );

        EvolutionProgress storage progress = evolutionProgress[configId];
        progress.status = EvolutionStatus.EMERGENCY;
        progress.triggerType = TriggerType.CRISIS_RESPONSE;
        progress.triggeredAt = block.timestamp;
        progress.initiatedBy = msg.sender;
        progress.triggerReason = emergencyJustification;

        metrics.emergencyEvolutions++;

        emit EmergencyEvolutionActivated(configId, msg.sender, emergencyJustification, true);

        // Execute after emergency delay
        if (block.timestamp >= progress.triggeredAt + emergencyEvolutionDelay) {
            _executeEvolution(configId);
        }
    }

    /**
     * @notice Execute evolution after all validations passed
     */
    function executeEvolution(uint256 configId) external validConfig(configId) {
        EvolutionProgress storage progress = evolutionProgress[configId];

        require(
            progress.status == EvolutionStatus.TRIGGERED ||
            progress.status == EvolutionStatus.EXECUTIVE_REVIEW,
            "Evolution not ready for execution"
        );

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];

        // Verify all required validations completed
        if (trigger.validationMethod == ValidationMethod.EXECUTIVE_APPROVAL) {
            require(executiveVotes[configId].passed, "Executive approval not obtained");
        }

        if (trigger.requiresConstitutionalReview) {
            ConstitutionalReview memory review = constitutionalReviews[configId];
            require(review.reviewCompleted && review.complianceApproved, "Constitutional review not approved");
        }

        _executeEvolution(configId);
    }

    /**
     * @notice Rollback recent evolution within rollback window
     */
    function rollbackEvolution(
        uint256 configId,
        string memory rollbackReason
    ) external validConfig(configId) {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can rollback evolution");

        EvolutionProgress memory progress = evolutionProgress[configId];
        require(progress.status == EvolutionStatus.COMPLETED, "Evolution not completed");

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];
        require(
            block.timestamp <= progress.completedAt + trigger.rollbackWindow,
            "Rollback window expired"
        );

        // Perform rollback
        universalDAIO.evolveGovernance(configId, true); // true = rollback

        evolutionProgress[configId].status = EvolutionStatus.CANCELLED;

        emit EvolutionRollback(configId, progress.fromStage, rollbackReason);
    }

    // =============================================================
    //                     INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @notice Validate specific trigger type
     */
    function _validateSpecificTrigger(
        uint256 configId,
        TriggerType triggerType,
        EnhancedEvolutionTrigger memory trigger,
        UniversalDAIO.UniversalConfig memory config,
        bytes memory triggerData
    ) internal view returns (bool valid) {
        if (triggerType == TriggerType.TIME_BASED) {
            uint256 timeElapsed = block.timestamp - config.createdAt;
            return timeElapsed >= trigger.timeThreshold;
        }

        if (triggerType == TriggerType.VALUE_BASED) {
            uint256 treasuryValue = treasury.getTotalValue();
            return treasuryValue >= trigger.valueThreshold;
        }

        if (triggerType == TriggerType.MEMBER_BASED) {
            uint256 memberCount = universalDAIO.getMemberCount(configId);
            return memberCount >= trigger.memberThreshold;
        }

        if (triggerType == TriggerType.PERFORMANCE_BASED) {
            uint256 performanceScore = governancePerformanceScores[configId];
            return performanceScore >= trigger.performanceThreshold;
        }

        if (triggerType == TriggerType.CONSTITUTIONAL) {
            return constitution.requiresEvolution(configId);
        }

        return false;
    }

    /**
     * @notice Start executive approval process
     */
    function _startExecutiveApproval(uint256 configId, EnhancedEvolutionTrigger memory trigger) internal {
        ExecutiveEvolutionVote storage vote = executiveVotes[configId];
        vote.votingDeadline = block.timestamp + defaultExecutiveVotingPeriod;
        vote.executed = false;
        vote.passed = false;
        vote.requiredApprovals = trigger.executiveApprovalThreshold;

        evolutionProgress[configId].status = EvolutionStatus.EXECUTIVE_REVIEW;

        emit ExecutiveEvolutionVoteStarted(configId, vote.votingDeadline, vote.requiredApprovals);
    }

    /**
     * @notice Start constitutional review process
     */
    function _startConstitutionalReview(uint256 configId) internal {
        ConstitutionalReview storage review = constitutionalReviews[configId];
        review.reviewRequired = true;
        review.reviewStarted = block.timestamp;
        review.reviewer = address(constitution);

        string[] memory criteria = new string[](3);
        criteria[0] = "Tithe compliance";
        criteria[1] = "Diversification compliance";
        criteria[2] = "Emergency power constraints";

        emit ConstitutionalReviewInitiated(configId, review.reviewer, criteria);
    }

    /**
     * @notice Execute evolution process
     */
    function _executeEvolution(uint256 configId) internal {
        EvolutionProgress storage progress = evolutionProgress[configId];
        progress.status = EvolutionStatus.IN_PROGRESS;
        progress.progressPercentage = 10;

        uint256 startTime = block.timestamp;

        try {
            // Execute evolution steps
            _executeEvolutionSteps(configId);

            // Perform actual governance evolution
            universalDAIO.evolveGovernance(configId, false);

            // Complete evolution
            progress.status = EvolutionStatus.COMPLETED;
            progress.completedAt = block.timestamp;
            progress.progressPercentage = 100;

            metrics.successfulEvolutions++;
            metrics.lastEvolutionTimestamp = block.timestamp;
            metrics.stageEvolutionCounts[progress.toStage]++;
            evolutionHistory[configId].push(block.timestamp);
            initiatorHistory[progress.initiatedBy].push(configId);

            uint256 duration = block.timestamp - startTime;
            EvolutionStep[] memory steps = evolutionSteps[configId];

            emit EvolutionCompleted(configId, progress.toStage, duration, steps.length, progress.initiatedBy);

        } catch Error(string memory reason) {
            progress.status = EvolutionStatus.FAILED;
            progress.completedAt = block.timestamp;
            metrics.failedEvolutions++;

            emit EvolutionFailed(configId, EvolutionStatus.FAILED, reason, progress.progressPercentage);
        }
    }

    /**
     * @notice Execute individual evolution steps
     */
    function _executeEvolutionSteps(uint256 configId) internal {
        EvolutionStep[] storage steps = evolutionSteps[configId];

        for (uint i = 0; i < steps.length; i++) {
            if (steps[i].required && !steps[i].completed) {
                uint256 gasStart = gasleft();

                // Check executive approval if required
                if (steps[i].requiresExecutiveApproval) {
                    require(executiveVotes[configId].passed, "Step requires executive approval");
                }

                // Check constitutional validation if required
                if (steps[i].requiresConstitutionalValidation) {
                    require(
                        constitution.validateEvolutionStep(configId, steps[i].stepName, steps[i].executionData),
                        "Step violates constitution"
                    );
                }

                // Execute step
                steps[i].completed = true;
                steps[i].completedAt = block.timestamp;
                steps[i].completedBy = msg.sender;

                uint256 gasUsed = gasStart - gasleft();

                emit EvolutionStepExecuted(configId, steps[i].stepName, msg.sender, gasUsed, steps[i].result);

                // Update progress
                evolutionProgress[configId].progressPercentage = ((i + 1) * 80) / steps.length + 10;
            }
        }
    }

    /**
     * @notice Initialize evolution steps for specific stage transitions
     */
    function _initializeEvolutionSteps(uint256 configId) internal {
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);
        delete evolutionSteps[configId];

        if (config.currentStage == UniversalDAIO.GovernanceStage.DICTATOR &&
            config.targetStage == UniversalDAIO.GovernanceStage.MARRIAGE) {
            _addDictatorToMarriageSteps(configId);
        } else if (config.currentStage == UniversalDAIO.GovernanceStage.MARRIAGE &&
                   config.targetStage == UniversalDAIO.GovernanceStage.TRIUMVIRATE) {
            _addMarriageToTriumvirateSteps(configId);
        } else if (config.currentStage == UniversalDAIO.GovernanceStage.TRIUMVIRATE &&
                   config.targetStage == UniversalDAIO.GovernanceStage.FEDERATION) {
            _addTriumvirateToFederationSteps(configId);
        } else if (config.targetStage == UniversalDAIO.GovernanceStage.AUTONOMOUS) {
            _addToAutonomousSteps(configId);
        }
    }

    /**
     * @notice Add steps for Dictator → Marriage evolution
     */
    function _addDictatorToMarriageSteps(uint256 configId) internal {
        evolutionSteps[configId].push(EvolutionStep({
            stepName: "partner_selection",
            description: "Select governance partner with complementary expertise",
            executionData: abi.encode("SELECT_PARTNER"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 100000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "dual_signature_setup",
            description: "Configure dual signature requirements",
            executionData: abi.encode("SETUP_DUAL_SIG"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 150000,
            requiresExecutiveApproval: false,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "voting_weight_configuration",
            description: "Configure voting weights between partners",
            executionData: abi.encode("CONFIGURE_WEIGHTS"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 80000,
            requiresExecutiveApproval: false,
            requiresConstitutionalValidation: true
        }));
    }

    /**
     * @notice Add steps for Marriage → Triumvirate evolution (CEO + Seven Soldiers)
     */
    function _addMarriageToTriumvirateSteps(uint256 configId) internal {
        evolutionSteps[configId].push(EvolutionStep({
            stepName: "ceo_designation",
            description: "Designate Chief Executive Officer role",
            executionData: abi.encode("DESIGNATE_CEO"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 120000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "seven_soldiers_selection",
            description: "Select Seven Soldiers executive team (CISO, CRO, CFO, CPO, COO, CTO, CLO)",
            executionData: abi.encode("SELECT_SEVEN_SOLDIERS"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 300000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "weighted_voting_setup",
            description: "Configure weighted voting system for executives",
            executionData: abi.encode("SETUP_WEIGHTED_VOTING"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 200000,
            requiresExecutiveApproval: false,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "emergency_powers_configuration",
            description: "Configure CEO emergency powers with constitutional limits",
            executionData: abi.encode("CONFIGURE_EMERGENCY_POWERS"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 180000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "ai_integration_preparation",
            description: "Prepare AI integration framework for future governance",
            executionData: abi.encode("PREPARE_AI_INTEGRATION"),
            required: false,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 250000,
            requiresExecutiveApproval: false,
            requiresConstitutionalValidation: false
        }));
    }

    /**
     * @notice Add steps for Triumvirate → Federation evolution
     */
    function _addTriumvirateToFederationSteps(uint256 configId) internal {
        evolutionSteps[configId].push(EvolutionStep({
            stepName: "multi_chain_deployment",
            description: "Deploy governance contracts to multiple chains",
            executionData: abi.encode("DEPLOY_MULTICHAIN"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 500000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "cross_chain_synchronization",
            description: "Setup cross-chain governance synchronization",
            executionData: abi.encode("SYNC_CROSS_CHAIN"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 400000,
            requiresExecutiveApproval: false,
            requiresConstitutionalValidation: true
        }));
    }

    /**
     * @notice Add steps for evolution to Autonomous governance
     */
    function _addToAutonomousSteps(uint256 configId) internal {
        evolutionSteps[configId].push(EvolutionStep({
            stepName: "ai_agent_deployment",
            description: "Deploy AI governance agents with oversight",
            executionData: abi.encode("DEPLOY_AI_AGENTS"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 600000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));

        evolutionSteps[configId].push(EvolutionStep({
            stepName: "human_oversight_configuration",
            description: "Configure human oversight mechanisms for AI decisions",
            executionData: abi.encode("CONFIGURE_HUMAN_OVERSIGHT"),
            required: true,
            completed: false,
            completedAt: 0,
            completedBy: address(0),
            result: "",
            estimatedGas: 300000,
            requiresExecutiveApproval: true,
            requiresConstitutionalValidation: true
        }));
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @notice Get comprehensive evolution status
     */
    function getEvolutionStatus(uint256 configId) external view validConfig(configId) returns (
        EvolutionProgress memory progress,
        ExecutiveEvolutionVote memory executiveVote,
        ConstitutionalReview memory constitutionalReview,
        EvolutionStep[] memory steps
    ) {
        progress = evolutionProgress[configId];

        // Convert executive vote (without mappings)
        ExecutiveEvolutionVote storage vote = executiveVotes[configId];
        executiveVote.approvalVotes = vote.approvalVotes;
        executiveVote.rejectionVotes = vote.rejectionVotes;
        executiveVote.votingDeadline = vote.votingDeadline;
        executiveVote.executed = vote.executed;
        executiveVote.passed = vote.passed;
        executiveVote.requiredApprovals = vote.requiredApprovals;

        constitutionalReview = constitutionalReviews[configId];
        steps = evolutionSteps[configId];
    }

    /**
     * @notice Get evolution metrics and statistics
     */
    function getEvolutionMetrics() external view returns (
        uint256 totalEvolutions,
        uint256 successfulEvolutions,
        uint256 failedEvolutions,
        uint256 emergencyEvolutions,
        uint256 averageEvolutionDuration,
        uint256 lastEvolutionTimestamp
    ) {
        return (
            metrics.totalEvolutions,
            metrics.successfulEvolutions,
            metrics.failedEvolutions,
            metrics.emergencyEvolutions,
            metrics.averageEvolutionDuration,
            metrics.lastEvolutionTimestamp
        );
    }

    // =============================================================
    //                      ADMIN FUNCTIONS
    // =============================================================

    /**
     * @notice Update global evolution settings
     */
    function updateEvolutionSettings(
        uint256 _executiveVotingPeriod,
        uint256 _communityVotingPeriod,
        uint256 _emergencyEvolutionDelay,
        uint256 _constitutionalReviewPeriod,
        uint256 _evolutionCooldownPeriod
    ) external onlyRole(EVOLUTION_MANAGER_ROLE) {
        defaultExecutiveVotingPeriod = _executiveVotingPeriod;
        defaultCommunityVotingPeriod = _communityVotingPeriod;
        emergencyEvolutionDelay = _emergencyEvolutionDelay;
        constitutionalReviewPeriod = _constitutionalReviewPeriod;
        evolutionCooldownPeriod = _evolutionCooldownPeriod;
    }

    /**
     * @notice Enable AI integration for governance
     */
    function enableAIIntegration(
        uint256 configId,
        address aiAgent,
        uint256 votingWeight
    ) external onlyRole(AI_INTEGRATION_ROLE) {
        require(aiAgent != address(0), "Invalid AI agent");
        require(votingWeight > 0 && votingWeight <= 100, "Invalid voting weight");

        EnhancedEvolutionTrigger storage trigger = enhancedTriggers[configId];
        require(trigger.enablesAIIntegration, "AI integration not enabled for this config");

        emit AIIntegrationEnabled(configId, aiAgent, votingWeight);
    }

    /**
     * @notice Pause/unpause evolution system
     */
    function pauseEvolutionSystem() external onlyRole(EVOLUTION_MANAGER_ROLE) {
        _pause();
    }

    function unpauseEvolutionSystem() external onlyRole(EVOLUTION_MANAGER_ROLE) {
        _unpause();
    }

    // =============================================================
    //                       MODIFIERS
    // =============================================================

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }
}