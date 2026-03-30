// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./UniversalDAIO.sol";

/**
 * @title GovernanceEvolution
 * @notice Manages automated governance stage transitions for Universal DAIO
 * @dev Handles DictatorDAO → MarriageDAO → TriumvirateDAO progression with configurable triggers
 */
contract GovernanceEvolution is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant EVOLUTION_MANAGER_ROLE = keccak256("EVOLUTION_MANAGER_ROLE");
    bytes32 public constant TRIGGER_VALIDATOR_ROLE = keccak256("TRIGGER_VALIDATOR_ROLE");
    bytes32 public constant EMERGENCY_EVOLUTION_ROLE = keccak256("EMERGENCY_EVOLUTION_ROLE");

    UniversalDAIO public immutable universalDAIO;

    // Evolution state tracking
    enum EvolutionStatus {
        PENDING,        // Evolution criteria not met
        TRIGGERED,      // Criteria met, awaiting execution
        IN_PROGRESS,    // Evolution in progress
        COMPLETED,      // Successfully completed
        FAILED,         // Evolution failed
        CANCELLED,      // Cancelled by stakeholders
        EMERGENCY       // Emergency evolution in progress
    }

    // Evolution validation types
    enum ValidationMethod {
        AUTOMATIC,      // Automatic when triggers met
        COMMUNITY_VOTE, // Requires community approval
        ADMIN_APPROVAL, // Requires admin approval
        HYBRID,         // Both community and admin
        TIME_DELAYED    // Automatic after time delay
    }

    // Evolution progress tracking
    struct EvolutionProgress {
        uint256 configId;
        UniversalDAIO.GovernanceStage fromStage;
        UniversalDAIO.GovernanceStage toStage;
        EvolutionStatus status;
        uint256 triggeredAt;
        uint256 completedAt;
        uint256 progressPercentage;
        string[] completedSteps;
        string[] pendingSteps;
        bytes32 evolutionHash;
    }

    // Enhanced evolution trigger with validation requirements
    struct EnhancedEvolutionTrigger {
        // Basic triggers from UniversalDAIO
        uint256 timeThreshold;
        uint256 valueThreshold;
        uint256 memberThreshold;
        uint256 proposalThreshold;
        uint256 activityThreshold;

        // Enhanced validation requirements
        ValidationMethod validationMethod;
        uint256 communityVoteThreshold;     // % approval needed
        uint256 adminApprovalCount;         // Number of admin approvals
        uint256 validationDelay;            // Delay before auto-execution
        uint256 stakeholderVetoPeriod;      // Period for stakeholders to veto

        // Advanced triggers
        uint256 governanceScoreThreshold;   // Governance participation score
        uint256 economicStabilityThreshold; // Economic health metrics
        uint256 consensusQualityThreshold;  // Quality of consensus decisions
        bool requiresUnanimousConsent;      // All stakeholders must agree
        bool allowsEmergencyBypass;         // Emergency evolution possible
    }

    // Stakeholder voting on evolution
    struct EvolutionVote {
        mapping(address => bool) hasVoted;
        mapping(address => bool) voteChoice; // true = approve, false = reject
        uint256 totalVotes;
        uint256 approvalVotes;
        uint256 rejectionVotes;
        uint256 votingDeadline;
        bool executed;
        bool passed;
    }

    // Evolution step definitions
    struct EvolutionStep {
        string stepName;
        string description;
        bytes executionData;
        bool required;
        bool completed;
        uint256 completedAt;
        address completedBy;
        bytes result;
    }

    // Storage
    mapping(uint256 => EnhancedEvolutionTrigger) public enhancedTriggers;
    mapping(uint256 => EvolutionProgress) public evolutionProgress;
    mapping(uint256 => EvolutionVote) public evolutionVotes;
    mapping(uint256 => EvolutionStep[]) public evolutionSteps;
    mapping(uint256 => mapping(address => bool)) public stakeholderStatus;
    mapping(uint256 => uint256[]) public evolutionHistory; // Track evolution timestamps

    // Global settings
    uint256 public defaultVotingPeriod = 7 days;
    uint256 public emergencyEvolutionDelay = 24 hours;
    uint256 public maxEvolutionRetries = 3;
    uint256 public evolutionCooldownPeriod = 30 days;

    // Statistics
    uint256 public totalEvolutions;
    uint256 public successfulEvolutions;
    uint256 public failedEvolutions;
    mapping(UniversalDAIO.GovernanceStage => uint256) public stageEvolutionCounts;

    // Events
    event EvolutionTriggered(
        uint256 indexed configId,
        UniversalDAIO.GovernanceStage fromStage,
        UniversalDAIO.GovernanceStage toStage,
        string triggerType,
        uint256 triggerValue
    );

    event EvolutionStepCompleted(
        uint256 indexed configId,
        string stepName,
        address completedBy,
        bytes result
    );

    event EvolutionVoteStarted(
        uint256 indexed configId,
        uint256 deadline,
        ValidationMethod method
    );

    event EvolutionVoteCast(
        uint256 indexed configId,
        address indexed voter,
        bool approval,
        string reason
    );

    event EvolutionCompleted(
        uint256 indexed configId,
        UniversalDAIO.GovernanceStage newStage,
        uint256 duration,
        uint256 participationRate
    );

    event EvolutionFailed(
        uint256 indexed configId,
        string reason,
        EvolutionStatus finalStatus
    );

    event EmergencyEvolutionActivated(
        uint256 indexed configId,
        address indexed initiator,
        string reason
    );

    event EvolutionCancelled(
        uint256 indexed configId,
        address indexed canceller,
        string reason
    );

    event StakeholderVeto(
        uint256 indexed configId,
        address indexed stakeholder,
        string reason
    );

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier onlyEvolutionManager() {
        require(hasRole(EVOLUTION_MANAGER_ROLE, msg.sender), "Not evolution manager");
        _;
    }

    modifier evolutionInProgress(uint256 configId) {
        require(
            evolutionProgress[configId].status == EvolutionStatus.IN_PROGRESS ||
            evolutionProgress[configId].status == EvolutionStatus.TRIGGERED,
            "Evolution not in progress"
        );
        _;
    }

    constructor(address _universalDAIO) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO address");
        universalDAIO = UniversalDAIO(_universalDAIO);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(EVOLUTION_MANAGER_ROLE, msg.sender);
        _grantRole(TRIGGER_VALIDATOR_ROLE, msg.sender);
        _grantRole(EMERGENCY_EVOLUTION_ROLE, msg.sender);
    }

    /**
     * @notice Configure enhanced evolution triggers for a DAIO configuration
     * @param configId Universal DAIO configuration ID
     * @param trigger Enhanced evolution trigger configuration
     */
    function configureEvolutionTriggers(
        uint256 configId,
        EnhancedEvolutionTrigger memory trigger
    ) external validConfig(configId) onlyEvolutionManager {
        require(trigger.timeThreshold > 0 || trigger.valueThreshold > 0, "At least one trigger required");
        require(trigger.communityVoteThreshold <= 100, "Invalid vote threshold");

        enhancedTriggers[configId] = trigger;

        // Initialize evolution steps based on current and target stage
        _initializeEvolutionSteps(configId);
    }

    /**
     * @notice Check evolution triggers and initiate evolution if criteria met
     * @param configId Configuration ID to check
     * @param triggerData Additional trigger validation data
     * @return triggered Whether evolution was triggered
     */
    function checkAndTriggerEvolution(
        uint256 configId,
        bytes memory triggerData
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

        // Validate all triggers
        bool allTriggersValid = true;
        string memory triggerType;
        uint256 triggerValue;

        (allTriggersValid, triggerType, triggerValue) = _validateTriggers(configId, trigger, config, triggerData);

        if (!allTriggersValid) {
            return false;
        }

        // Initialize evolution progress
        progress.configId = configId;
        progress.fromStage = config.currentStage;
        progress.toStage = config.targetStage;
        progress.status = EvolutionStatus.TRIGGERED;
        progress.triggeredAt = block.timestamp;
        progress.progressPercentage = 0;
        progress.evolutionHash = keccak256(abi.encode(configId, config.currentStage, config.targetStage, block.timestamp));

        totalEvolutions++;

        emit EvolutionTriggered(configId, config.currentStage, config.targetStage, triggerType, triggerValue);

        // Start validation process based on method
        if (trigger.validationMethod == ValidationMethod.AUTOMATIC) {
            _executeEvolution(configId);
        } else {
            _startEvolutionValidation(configId, trigger);
        }

        return true;
    }

    /**
     * @notice Start community voting on evolution
     * @param configId Configuration ID
     * @param votingPeriod Voting period in seconds
     */
    function startEvolutionVote(
        uint256 configId,
        uint256 votingPeriod
    ) external validConfig(configId) onlyEvolutionManager {
        require(evolutionProgress[configId].status == EvolutionStatus.TRIGGERED, "Evolution not triggered");
        require(votingPeriod > 0 && votingPeriod <= 30 days, "Invalid voting period");

        EvolutionVote storage vote = evolutionVotes[configId];
        vote.votingDeadline = block.timestamp + votingPeriod;
        vote.executed = false;
        vote.passed = false;

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];

        emit EvolutionVoteStarted(configId, vote.votingDeadline, trigger.validationMethod);
    }

    /**
     * @notice Cast vote on evolution proposal
     * @param configId Configuration ID
     * @param approval Vote choice (true = approve, false = reject)
     * @param reason Reason for vote
     */
    function castEvolutionVote(
        uint256 configId,
        bool approval,
        string memory reason
    ) external validConfig(configId) {
        EvolutionVote storage vote = evolutionVotes[configId];
        require(block.timestamp <= vote.votingDeadline, "Voting period ended");
        require(!vote.hasVoted[msg.sender], "Already voted");

        // Validate voting eligibility (simplified - would integrate with actual voting power)
        require(_isEligibleVoter(configId, msg.sender), "Not eligible to vote");

        vote.hasVoted[msg.sender] = true;
        vote.voteChoice[msg.sender] = approval;
        vote.totalVotes++;

        if (approval) {
            vote.approvalVotes++;
        } else {
            vote.rejectionVotes++;
        }

        emit EvolutionVoteCast(configId, msg.sender, approval, reason);

        // Auto-execute if threshold reached early
        _checkVoteCompletion(configId);
    }

    /**
     * @notice Execute evolution after validation
     * @param configId Configuration ID
     */
    function executeEvolution(uint256 configId) external validConfig(configId) {
        require(evolutionProgress[configId].status == EvolutionStatus.TRIGGERED, "Evolution not ready");

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];

        if (trigger.validationMethod != ValidationMethod.AUTOMATIC) {
            require(_isValidationComplete(configId), "Validation not complete");
        }

        _executeEvolution(configId);
    }

    /**
     * @notice Cancel ongoing evolution
     * @param configId Configuration ID
     * @param reason Cancellation reason
     */
    function cancelEvolution(
        uint256 configId,
        string memory reason
    ) external validConfig(configId) {
        EvolutionProgress storage progress = evolutionProgress[configId];
        require(
            progress.status == EvolutionStatus.TRIGGERED ||
            progress.status == EvolutionStatus.IN_PROGRESS,
            "Evolution not cancellable"
        );

        // Check cancellation authority
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);
        require(
            msg.sender == config.admin ||
            hasRole(EVOLUTION_MANAGER_ROLE, msg.sender) ||
            _hasStakeholderVetoPower(configId, msg.sender),
            "Not authorized to cancel"
        );

        progress.status = EvolutionStatus.CANCELLED;
        progress.completedAt = block.timestamp;
        failedEvolutions++;

        emit EvolutionCancelled(configId, msg.sender, reason);
    }

    /**
     * @notice Emergency evolution bypass for critical situations
     * @param configId Configuration ID
     * @param emergency Emergency justification
     */
    function emergencyEvolution(
        uint256 configId,
        string memory emergency
    ) external validConfig(configId) {
        require(hasRole(EMERGENCY_EVOLUTION_ROLE, msg.sender), "Not authorized for emergency evolution");

        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];
        require(trigger.allowsEmergencyBypass, "Emergency evolution disabled");

        EvolutionProgress storage progress = evolutionProgress[configId];
        progress.status = EvolutionStatus.EMERGENCY;
        progress.triggeredAt = block.timestamp;

        emit EmergencyEvolutionActivated(configId, msg.sender, emergency);

        // Execute after emergency delay
        if (block.timestamp >= progress.triggeredAt + emergencyEvolutionDelay) {
            _executeEvolution(configId);
        }
    }

    /**
     * @notice Get evolution progress
     * @param configId Configuration ID
     * @return Evolution progress details
     */
    function getEvolutionProgress(uint256 configId) external view validConfig(configId) returns (EvolutionProgress memory) {
        return evolutionProgress[configId];
    }

    /**
     * @notice Get evolution steps
     * @param configId Configuration ID
     * @return Array of evolution steps
     */
    function getEvolutionSteps(uint256 configId) external view validConfig(configId) returns (EvolutionStep[] memory) {
        return evolutionSteps[configId];
    }

    /**
     * @notice Get evolution statistics
     * @return total Total evolutions
     * @return successful Successful evolutions
     * @return failed Failed evolutions
     * @return stageDistribution Evolution distribution by stage
     */
    function getEvolutionStatistics() external view returns (
        uint256 total,
        uint256 successful,
        uint256 failed,
        uint256[6] memory stageDistribution
    ) {
        total = totalEvolutions;
        successful = successfulEvolutions;
        failed = failedEvolutions;

        stageDistribution[0] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.DICTATOR];
        stageDistribution[1] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.MARRIAGE];
        stageDistribution[2] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.TRIUMVIRATE];
        stageDistribution[3] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.CUSTOM];
        stageDistribution[4] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.FEDERATION];
        stageDistribution[5] = stageEvolutionCounts[UniversalDAIO.GovernanceStage.AUTONOMOUS];
    }

    /**
     * @notice Update global evolution settings
     */
    function updateEvolutionSettings(
        uint256 _defaultVotingPeriod,
        uint256 _emergencyEvolutionDelay,
        uint256 _maxEvolutionRetries,
        uint256 _evolutionCooldownPeriod
    ) external onlyEvolutionManager {
        defaultVotingPeriod = _defaultVotingPeriod;
        emergencyEvolutionDelay = _emergencyEvolutionDelay;
        maxEvolutionRetries = _maxEvolutionRetries;
        evolutionCooldownPeriod = _evolutionCooldownPeriod;
    }

    /**
     * @notice Pause evolution system
     */
    function pauseEvolutionSystem() external onlyEvolutionManager {
        _pause();
    }

    /**
     * @notice Unpause evolution system
     */
    function unpauseEvolutionSystem() external onlyEvolutionManager {
        _unpause();
    }

    // Internal Functions

    /**
     * @notice Validate evolution triggers
     */
    function _validateTriggers(
        uint256 configId,
        EnhancedEvolutionTrigger memory trigger,
        UniversalDAIO.UniversalConfig memory config,
        bytes memory triggerData
    ) internal view returns (bool valid, string memory triggerType, uint256 triggerValue) {
        // Time trigger
        if (trigger.timeThreshold > 0) {
            uint256 timeElapsed = block.timestamp - config.createdAt;
            if (timeElapsed >= trigger.timeThreshold) {
                return (true, "TIME", timeElapsed);
            }
        }

        // Value trigger (simplified - would integrate with treasury)
        if (trigger.valueThreshold > 0) {
            // uint256 treasuryValue = _getTreasuryValue(configId);
            // if (treasuryValue >= trigger.valueThreshold) {
            //     return (true, "VALUE", treasuryValue);
            // }
        }

        // Member trigger (simplified - would integrate with member registry)
        if (trigger.memberThreshold > 0) {
            // uint256 memberCount = _getMemberCount(configId);
            // if (memberCount >= trigger.memberThreshold) {
            //     return (true, "MEMBER", memberCount);
            // }
        }

        // Additional trigger validations would be implemented here

        return (false, "", 0);
    }

    /**
     * @notice Start evolution validation process
     */
    function _startEvolutionValidation(uint256 configId, EnhancedEvolutionTrigger memory trigger) internal {
        if (trigger.validationMethod == ValidationMethod.COMMUNITY_VOTE ||
            trigger.validationMethod == ValidationMethod.HYBRID) {

            EvolutionVote storage vote = evolutionVotes[configId];
            vote.votingDeadline = block.timestamp + defaultVotingPeriod;

            emit EvolutionVoteStarted(configId, vote.votingDeadline, trigger.validationMethod);
        }

        if (trigger.validationMethod == ValidationMethod.TIME_DELAYED) {
            // Set delay before auto-execution
            evolutionProgress[configId].triggeredAt = block.timestamp + trigger.validationDelay;
        }
    }

    /**
     * @notice Execute the evolution process
     */
    function _executeEvolution(uint256 configId) internal {
        EvolutionProgress storage progress = evolutionProgress[configId];
        progress.status = EvolutionStatus.IN_PROGRESS;
        progress.progressPercentage = 10;

        uint256 startTime = block.timestamp;

        try {
            // Execute evolution steps
            _executeEvolutionSteps(configId);

            // Call UniversalDAIO to perform the actual evolution
            universalDAIO.evolveGovernance(configId, false);

            // Complete evolution
            progress.status = EvolutionStatus.COMPLETED;
            progress.completedAt = block.timestamp;
            progress.progressPercentage = 100;

            successfulEvolutions++;
            stageEvolutionCounts[progress.toStage]++;
            evolutionHistory[configId].push(block.timestamp);

            uint256 duration = block.timestamp - startTime;
            uint256 participationRate = _calculateParticipationRate(configId);

            emit EvolutionCompleted(configId, progress.toStage, duration, participationRate);

        } catch Error(string memory reason) {
            progress.status = EvolutionStatus.FAILED;
            progress.completedAt = block.timestamp;
            failedEvolutions++;

            emit EvolutionFailed(configId, reason, EvolutionStatus.FAILED);
        }
    }

    /**
     * @notice Execute individual evolution steps
     */
    function _executeEvolutionSteps(uint256 configId) internal {
        EvolutionStep[] storage steps = evolutionSteps[configId];

        for (uint i = 0; i < steps.length; i++) {
            if (steps[i].required && !steps[i].completed) {
                // Execute step (simplified)
                steps[i].completed = true;
                steps[i].completedAt = block.timestamp;
                steps[i].completedBy = msg.sender;

                emit EvolutionStepCompleted(configId, steps[i].stepName, msg.sender, steps[i].result);

                // Update progress percentage
                evolutionProgress[configId].progressPercentage = ((i + 1) * 80) / steps.length + 10;
            }
        }
    }

    /**
     * @notice Initialize evolution steps for stage transition
     */
    function _initializeEvolutionSteps(uint256 configId) internal {
        UniversalDAIO.UniversalConfig memory config = universalDAIO.getConfiguration(configId);

        // Clear existing steps
        delete evolutionSteps[configId];

        if (config.currentStage == UniversalDAIO.GovernanceStage.DICTATOR &&
            config.targetStage == UniversalDAIO.GovernanceStage.MARRIAGE) {

            evolutionSteps[configId].push(EvolutionStep({
                stepName: "partner_selection",
                description: "Select second governance partner",
                executionData: "",
                required: true,
                completed: false,
                completedAt: 0,
                completedBy: address(0),
                result: ""
            }));

            evolutionSteps[configId].push(EvolutionStep({
                stepName: "weight_configuration",
                description: "Configure voting weights",
                executionData: "",
                required: true,
                completed: false,
                completedAt: 0,
                completedBy: address(0),
                result: ""
            }));

        } else if (config.currentStage == UniversalDAIO.GovernanceStage.MARRIAGE &&
                   config.targetStage == UniversalDAIO.GovernanceStage.TRIUMVIRATE) {

            evolutionSteps[configId].push(EvolutionStep({
                stepName: "triumvirate_selection",
                description: "Select third domain lead",
                executionData: "",
                required: true,
                completed: false,
                completedAt: 0,
                completedBy: address(0),
                result: ""
            }));

            evolutionSteps[configId].push(EvolutionStep({
                stepName: "ai_integration_setup",
                description: "Configure AI voting integration",
                executionData: "",
                required: false,
                completed: false,
                completedAt: 0,
                completedBy: address(0),
                result: ""
            }));
        }
    }

    /**
     * @notice Check if validation is complete
     */
    function _isValidationComplete(uint256 configId) internal view returns (bool) {
        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];

        if (trigger.validationMethod == ValidationMethod.COMMUNITY_VOTE ||
            trigger.validationMethod == ValidationMethod.HYBRID) {

            EvolutionVote memory vote = evolutionVotes[configId];
            return block.timestamp > vote.votingDeadline && vote.passed;
        }

        return true;
    }

    /**
     * @notice Check if vote is complete and update status
     */
    function _checkVoteCompletion(uint256 configId) internal {
        EvolutionVote storage vote = evolutionVotes[configId];
        EnhancedEvolutionTrigger memory trigger = enhancedTriggers[configId];

        if (vote.totalVotes > 0) {
            uint256 approvalPercentage = (vote.approvalVotes * 100) / vote.totalVotes;

            if (approvalPercentage >= trigger.communityVoteThreshold) {
                vote.passed = true;
                if (trigger.validationMethod == ValidationMethod.COMMUNITY_VOTE) {
                    _executeEvolution(configId);
                }
            }
        }
    }

    /**
     * @notice Check if address is eligible to vote
     */
    function _isEligibleVoter(uint256 configId, address voter) internal view returns (bool) {
        // Simplified eligibility check - would integrate with actual voting power calculation
        return voter != address(0);
    }

    /**
     * @notice Check if address has stakeholder veto power
     */
    function _hasStakeholderVetoPower(uint256 configId, address stakeholder) internal view returns (bool) {
        return stakeholderStatus[configId][stakeholder];
    }

    /**
     * @notice Calculate participation rate for evolution
     */
    function _calculateParticipationRate(uint256 configId) internal view returns (uint256) {
        EvolutionVote memory vote = evolutionVotes[configId];

        if (vote.totalVotes > 0) {
            // Simplified calculation - would integrate with actual eligible voter count
            return (vote.totalVotes * 100) / 100; // Placeholder
        }

        return 0;
    }
}