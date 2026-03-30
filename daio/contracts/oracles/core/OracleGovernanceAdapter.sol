// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./OracleRegistry.sol";
import "./PriceFeedAggregator.sol";
import "./VolatilityOracle.sol";
import "./EmergencyCircuitBreaker.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title OracleGovernanceAdapter
 * @notice TriumvirateGovernance oracle parameter control for DAIO integration
 * @dev Bridges oracle operations with DAIO governance for democratic oracle management
 */
contract OracleGovernanceAdapter is AccessControl, ReentrancyGuard {

    bytes32 public constant GOVERNANCE_EXECUTOR_ROLE = keccak256("GOVERNANCE_EXECUTOR_ROLE");
    bytes32 public constant PROPOSAL_VALIDATOR_ROLE = keccak256("PROPOSAL_VALIDATOR_ROLE");
    bytes32 public constant EMERGENCY_RESPONDER_ROLE = keccak256("EMERGENCY_RESPONDER_ROLE");

    // Proposal types for oracle governance
    enum ProposalType {
        ORACLE_SOURCE_REGISTRATION,
        ORACLE_SOURCE_REMOVAL,
        PRICE_FEED_CONFIGURATION,
        VOLATILITY_CONFIGURATION,
        CIRCUIT_BREAKER_CONFIG,
        EMERGENCY_RESPONSE,
        CONSTITUTIONAL_UPDATE
    }

    // Proposal structure
    struct OracleProposal {
        uint256 id;
        ProposalType proposalType;
        string targetAsset;
        address targetOracle;
        bytes proposalData;
        address proposer;
        uint256 createdAt;
        uint256 executionTime;
        bool executed;
        bool cancelled;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 abstentions;
        mapping(address => bool) hasVoted;
        mapping(address => uint8) voteChoice; // 0=against, 1=for, 2=abstain
    }

    // Governance integration
    struct GovernanceConfig {
        address triumvirateGovernance;   // TriumvirateGovernance contract
        address executiveGovernance;     // ExecutiveGovernance contract
        address daioConstitution;       // DAIO Constitution contract
        uint256 proposalDelay;          // Delay before proposal can be executed
        uint256 votingPeriod;           // Voting period for proposals
        uint256 executionGracePeriod;   // Grace period for execution after voting
        uint256 quorumThreshold;        // Minimum quorum required (BPS)
        uint256 approvalThreshold;      // Approval threshold (BPS)
    }

    // Oracle contract integration
    OracleRegistry public immutable oracleRegistry;
    PriceFeedAggregator public immutable priceFeedAggregator;
    VolatilityOracle public immutable volatilityOracle;
    EmergencyCircuitBreaker public immutable emergencyCircuitBreaker;

    // State variables
    GovernanceConfig public governanceConfig;
    mapping(uint256 => OracleProposal) public proposals;
    mapping(address => uint256) public votingPower;
    mapping(string => uint256) public lastConfigUpdate; // asset -> timestamp

    uint256 public nextProposalId = 1;
    uint256[] public activeProposals;
    uint256[] public executedProposals;

    // Constitutional constraints tracking
    mapping(string => bool) public constitutionallyCompliantAssets;
    mapping(address => uint256) public oracleReputationOverride;

    // Emergency governance state
    bool public emergencyGovernanceActive;
    uint256 public emergencyActivatedAt;
    address public emergencyGovernor;

    // Events
    event ProposalCreated(
        uint256 indexed proposalId,
        ProposalType indexed proposalType,
        string targetAsset,
        address indexed proposer
    );
    event ProposalExecuted(
        uint256 indexed proposalId,
        bool success,
        address indexed executor
    );
    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        uint8 choice,
        uint256 votingPower
    );
    event GovernanceConfigUpdated(
        address triumvirateGovernance,
        uint256 proposalDelay,
        uint256 votingPeriod
    );
    event EmergencyGovernanceActivated(
        address indexed emergencyGovernor,
        string reason
    );
    event ConstitutionalComplianceUpdated(
        string indexed asset,
        bool compliant,
        string reason
    );
    event OracleReputationOverride(
        address indexed oracle,
        uint256 newReputation,
        string reason
    );

    /**
     * @notice Initialize OracleGovernanceAdapter with DAIO governance integration
     * @param _oracleRegistry Oracle registry contract
     * @param _priceFeedAggregator Price feed aggregator contract
     * @param _volatilityOracle Volatility oracle contract
     * @param _emergencyCircuitBreaker Emergency circuit breaker contract
     * @param _triumvirateGovernance TriumvirateGovernance contract
     * @param admin Admin address for role management
     */
    constructor(
        address _oracleRegistry,
        address _priceFeedAggregator,
        address _volatilityOracle,
        address _emergencyCircuitBreaker,
        address _triumvirateGovernance,
        address admin
    ) {
        require(_oracleRegistry != address(0), "Oracle registry cannot be zero address");
        require(_priceFeedAggregator != address(0), "Price aggregator cannot be zero address");
        require(_volatilityOracle != address(0), "Volatility oracle cannot be zero address");
        require(_emergencyCircuitBreaker != address(0), "Circuit breaker cannot be zero address");
        require(admin != address(0), "Admin cannot be zero address");

        oracleRegistry = OracleRegistry(_oracleRegistry);
        priceFeedAggregator = PriceFeedAggregator(_priceFeedAggregator);
        volatilityOracle = VolatilityOracle(_volatilityOracle);
        emergencyCircuitBreaker = EmergencyCircuitBreaker(_emergencyCircuitBreaker);

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNANCE_EXECUTOR_ROLE, admin);
        _grantRole(PROPOSAL_VALIDATOR_ROLE, admin);
        _grantRole(EMERGENCY_RESPONDER_ROLE, admin);

        // Initialize governance configuration
        governanceConfig = GovernanceConfig({
            triumvirateGovernance: _triumvirateGovernance,
            executiveGovernance: address(0), // Set later
            daioConstitution: address(0),    // Set later
            proposalDelay: 86400,            // 24 hours
            votingPeriod: 259200,            // 72 hours (3 days)
            executionGracePeriod: 604800,    // 7 days
            quorumThreshold: 3333,           // 33.33% quorum
            approvalThreshold: 6667          // 66.67% approval (2/3 majority)
        });
    }

    /**
     * @notice Create a new oracle governance proposal
     * @param proposalType Type of proposal
     * @param targetAsset Target asset symbol
     * @param targetOracle Target oracle address
     * @param proposalData Encoded proposal data
     * @return proposalId ID of created proposal
     */
    function createProposal(
        ProposalType proposalType,
        string memory targetAsset,
        address targetOracle,
        bytes memory proposalData
    ) external nonReentrant returns (uint256 proposalId) {
        require(
            hasRole(GOVERNANCE_EXECUTOR_ROLE, msg.sender) ||
            _isTriumvirateGovernance(msg.sender),
            "Unauthorized to create proposals"
        );

        // Validate proposal based on type
        require(_validateProposal(proposalType, targetAsset, targetOracle, proposalData), "Invalid proposal");

        // Check constitutional compliance for asset-related proposals
        if (bytes(targetAsset).length > 0) {
            require(_checkConstitutionalCompliance(targetAsset), "Asset not constitutionally compliant");
        }

        proposalId = nextProposalId++;

        OracleProposal storage proposal = proposals[proposalId];
        proposal.id = proposalId;
        proposal.proposalType = proposalType;
        proposal.targetAsset = targetAsset;
        proposal.targetOracle = targetOracle;
        proposal.proposalData = proposalData;
        proposal.proposer = msg.sender;
        proposal.createdAt = block.timestamp;
        proposal.executionTime = block.timestamp + governanceConfig.proposalDelay + governanceConfig.votingPeriod;
        proposal.executed = false;
        proposal.cancelled = false;

        activeProposals.push(proposalId);

        emit ProposalCreated(proposalId, proposalType, targetAsset, msg.sender);

        return proposalId;
    }

    /**
     * @notice Cast vote on a proposal
     * @param proposalId Proposal ID
     * @param choice Vote choice (0=against, 1=for, 2=abstain)
     */
    function castVote(uint256 proposalId, uint8 choice) external nonReentrant {
        require(choice <= 2, "Invalid vote choice");
        require(proposals[proposalId].id != 0, "Proposal does not exist");
        require(!proposals[proposalId].executed, "Proposal already executed");
        require(!proposals[proposalId].cancelled, "Proposal cancelled");
        require(!proposals[proposalId].hasVoted[msg.sender], "Already voted");

        OracleProposal storage proposal = proposals[proposalId];

        // Check voting period
        require(
            block.timestamp >= proposal.createdAt + governanceConfig.proposalDelay,
            "Voting not started"
        );
        require(
            block.timestamp <= proposal.createdAt + governanceConfig.proposalDelay + governanceConfig.votingPeriod,
            "Voting period ended"
        );

        // Get voting power from TriumvirateGovernance or calculate based on role
        uint256 voterPower = _getVotingPower(msg.sender);
        require(voterPower > 0, "No voting power");

        proposal.hasVoted[msg.sender] = true;
        proposal.voteChoice[msg.sender] = choice;

        if (choice == 0) {
            proposal.votesAgainst += voterPower;
        } else if (choice == 1) {
            proposal.votesFor += voterPower;
        } else {
            proposal.abstentions += voterPower;
        }

        emit VoteCast(proposalId, msg.sender, choice, voterPower);
    }

    /**
     * @notice Execute a proposal after voting period
     * @param proposalId Proposal ID to execute
     */
    function executeProposal(uint256 proposalId) external nonReentrant {
        require(proposals[proposalId].id != 0, "Proposal does not exist");
        require(!proposals[proposalId].executed, "Proposal already executed");
        require(!proposals[proposalId].cancelled, "Proposal cancelled");

        OracleProposal storage proposal = proposals[proposalId];

        // Check execution timing
        require(block.timestamp >= proposal.executionTime, "Execution time not reached");
        require(
            block.timestamp <= proposal.executionTime + governanceConfig.executionGracePeriod,
            "Execution grace period expired"
        );

        // Check quorum and approval
        uint256 totalVotes = proposal.votesFor + proposal.votesAgainst + proposal.abstentions;
        uint256 totalVotingPower = _getTotalVotingPower();

        require(
            (totalVotes * 10000) / totalVotingPower >= governanceConfig.quorumThreshold,
            "Quorum not met"
        );

        require(
            (proposal.votesFor * 10000) / (proposal.votesFor + proposal.votesAgainst) >= governanceConfig.approvalThreshold,
            "Approval threshold not met"
        );

        // Execute the proposal
        bool success = _executeProposalAction(proposal);

        proposal.executed = true;
        _removeFromActiveProposals(proposalId);
        executedProposals.push(proposalId);

        emit ProposalExecuted(proposalId, success, msg.sender);
    }

    /**
     * @notice Emergency execute a proposal (bypass normal governance)
     * @param proposalId Proposal ID
     * @param reason Reason for emergency execution
     */
    function emergencyExecute(
        uint256 proposalId,
        string memory reason
    ) external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        require(emergencyGovernanceActive, "Emergency governance not active");
        require(proposals[proposalId].id != 0, "Proposal does not exist");
        require(!proposals[proposalId].executed, "Proposal already executed");

        OracleProposal storage proposal = proposals[proposalId];

        // Execute the proposal
        bool success = _executeProposalAction(proposal);

        proposal.executed = true;
        _removeFromActiveProposals(proposalId);
        executedProposals.push(proposalId);

        emit ProposalExecuted(proposalId, success, msg.sender);
    }

    /**
     * @notice Activate emergency governance mode
     * @param reason Reason for emergency activation
     */
    function activateEmergencyGovernance(
        string memory reason
    ) external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        require(!emergencyGovernanceActive, "Emergency governance already active");

        emergencyGovernanceActive = true;
        emergencyActivatedAt = block.timestamp;
        emergencyGovernor = msg.sender;

        emit EmergencyGovernanceActivated(msg.sender, reason);
    }

    /**
     * @notice Deactivate emergency governance mode
     */
    function deactivateEmergencyGovernance() external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        require(emergencyGovernanceActive, "Emergency governance not active");
        require(
            msg.sender == emergencyGovernor || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Unauthorized to deactivate"
        );

        emergencyGovernanceActive = false;
        emergencyActivatedAt = 0;
        emergencyGovernor = address(0);
    }

    /**
     * @notice Update governance configuration
     * @param triumvirateGovernance New TriumvirateGovernance address
     * @param proposalDelay New proposal delay
     * @param votingPeriod New voting period
     * @param quorumThreshold New quorum threshold (BPS)
     * @param approvalThreshold New approval threshold (BPS)
     */
    function updateGovernanceConfig(
        address triumvirateGovernance,
        uint256 proposalDelay,
        uint256 votingPeriod,
        uint256 quorumThreshold,
        uint256 approvalThreshold
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(triumvirateGovernance != address(0), "Invalid governance address");
        require(proposalDelay >= 3600, "Proposal delay too short"); // Min 1 hour
        require(votingPeriod >= 86400, "Voting period too short"); // Min 24 hours
        require(quorumThreshold <= 10000, "Invalid quorum threshold");
        require(approvalThreshold > 5000 && approvalThreshold <= 10000, "Invalid approval threshold");

        governanceConfig.triumvirateGovernance = triumvirateGovernance;
        governanceConfig.proposalDelay = proposalDelay;
        governanceConfig.votingPeriod = votingPeriod;
        governanceConfig.quorumThreshold = quorumThreshold;
        governanceConfig.approvalThreshold = approvalThreshold;

        emit GovernanceConfigUpdated(triumvirateGovernance, proposalDelay, votingPeriod);
    }

    /**
     * @notice Set constitutional compliance for an asset
     * @param asset Asset symbol
     * @param compliant Whether asset is compliant
     * @param reason Reason for compliance status
     */
    function setConstitutionalCompliance(
        string memory asset,
        bool compliant,
        string memory reason
    ) external onlyRole(PROPOSAL_VALIDATOR_ROLE) {
        constitutionallyCompliantAssets[asset] = compliant;
        emit ConstitutionalComplianceUpdated(asset, compliant, reason);
    }

    /**
     * @notice Override oracle reputation score
     * @param oracle Oracle address
     * @param reputation New reputation score (0-10000 BPS)
     * @param reason Reason for override
     */
    function overrideOracleReputation(
        address oracle,
        uint256 reputation,
        string memory reason
    ) external onlyRole(GOVERNANCE_EXECUTOR_ROLE) {
        require(reputation <= 10000, "Invalid reputation score");

        oracleReputationOverride[oracle] = reputation;

        emit OracleReputationOverride(oracle, reputation, reason);
    }

    /**
     * @notice Get proposal information
     * @param proposalId Proposal ID
     * @return proposalInfo Proposal information
     */
    function getProposal(uint256 proposalId) external view returns (
        uint256 id,
        ProposalType proposalType,
        string memory targetAsset,
        address targetOracle,
        address proposer,
        uint256 createdAt,
        bool executed,
        uint256 votesFor,
        uint256 votesAgainst,
        uint256 abstentions
    ) {
        OracleProposal storage proposal = proposals[proposalId];
        return (
            proposal.id,
            proposal.proposalType,
            proposal.targetAsset,
            proposal.targetOracle,
            proposal.proposer,
            proposal.createdAt,
            proposal.executed,
            proposal.votesFor,
            proposal.votesAgainst,
            proposal.abstentions
        );
    }

    /**
     * @notice Get active proposals
     * @return proposalIds Array of active proposal IDs
     */
    function getActiveProposals() external view returns (uint256[] memory proposalIds) {
        return activeProposals;
    }

    // Internal functions

    function _validateProposal(
        ProposalType proposalType,
        string memory targetAsset,
        address targetOracle,
        bytes memory proposalData
    ) internal view returns (bool) {
        // Basic validation based on proposal type
        if (proposalType == ProposalType.ORACLE_SOURCE_REGISTRATION) {
            return targetOracle != address(0) && bytes(targetAsset).length > 0;
        } else if (proposalType == ProposalType.ORACLE_SOURCE_REMOVAL) {
            return targetOracle != address(0);
        } else if (proposalType == ProposalType.PRICE_FEED_CONFIGURATION) {
            return bytes(targetAsset).length > 0 && proposalData.length > 0;
        } else if (proposalType == ProposalType.VOLATILITY_CONFIGURATION) {
            return bytes(targetAsset).length > 0 && proposalData.length > 0;
        }

        return proposalData.length > 0;
    }

    function _checkConstitutionalCompliance(string memory asset) internal view returns (bool) {
        // Check if asset is constitutionally compliant
        // This integrates with DAIO constitution constraints
        return constitutionallyCompliantAssets[asset] || bytes(asset).length == 0;
    }

    function _isTriumvirateGovernance(address addr) internal view returns (bool) {
        return addr == governanceConfig.triumvirateGovernance;
    }

    function _getVotingPower(address voter) internal view returns (uint256) {
        // In a real implementation, this would query TriumvirateGovernance
        // For now, return based on roles
        if (hasRole(GOVERNANCE_EXECUTOR_ROLE, voter)) {
            return 10000; // Full voting power for governance executors
        } else if (_isTriumvirateGovernance(voter)) {
            return 10000; // Full voting power for TriumvirateGovernance
        }

        return votingPower[voter]; // Manually set voting power
    }

    function _getTotalVotingPower() internal view returns (uint256) {
        // Simplified total voting power calculation
        // In production, would query all TriumvirateGovernance members
        return 30000; // 3 groups × 10000 voting power each
    }

    function _executeProposalAction(OracleProposal storage proposal) internal returns (bool) {
        try this.executeProposalCall(
            proposal.proposalType,
            proposal.targetAsset,
            proposal.targetOracle,
            proposal.proposalData
        ) {
            lastConfigUpdate[proposal.targetAsset] = block.timestamp;
            return true;
        } catch {
            return false;
        }
    }

    /**
     * @notice Execute proposal call (external to handle try/catch)
     * @param proposalType Type of proposal
     * @param targetAsset Target asset
     * @param targetOracle Target oracle
     * @param proposalData Proposal data
     */
    function executeProposalCall(
        ProposalType proposalType,
        string memory targetAsset,
        address targetOracle,
        bytes memory proposalData
    ) external {
        require(msg.sender == address(this), "Only self-call allowed");

        if (proposalType == ProposalType.ORACLE_SOURCE_REGISTRATION) {
            (string memory name, uint256 weight, uint256 maxDeviation, uint256 heartbeat, bool trusted) =
                abi.decode(proposalData, (string, uint256, uint256, uint256, bool));

            oracleRegistry.registerOracleSource(
                targetAsset,
                targetOracle,
                name,
                weight,
                maxDeviation,
                heartbeat,
                trusted
            );

        } else if (proposalType == ProposalType.ORACLE_SOURCE_REMOVAL) {
            oracleRegistry.updateSourceStatus(targetAsset, targetOracle, false);

        } else if (proposalType == ProposalType.PRICE_FEED_CONFIGURATION) {
            (address[] memory fallbacks, uint256 maxDeviation, uint256 confidence) =
                abi.decode(proposalData, (address[], uint256, uint256));

            priceFeedAggregator.createPriceFeed(
                targetAsset,
                targetOracle,
                fallbacks,
                maxDeviation,
                confidence
            );

        } else if (proposalType == ProposalType.VOLATILITY_CONFIGURATION) {
            (uint256 windowSize, uint256 updateFreq, uint256 highVolThreshold, uint256 extremeVolThreshold) =
                abi.decode(proposalData, (uint256, uint256, uint256, uint256));

            volatilityOracle.configureVolatilityTracking(
                targetAsset,
                windowSize,
                updateFreq,
                highVolThreshold,
                extremeVolThreshold
            );

        } else if (proposalType == ProposalType.CIRCUIT_BREAKER_CONFIG) {
            (uint256 priceThreshold, uint256 volThreshold, uint256 oracleFailureThreshold, uint256 cooldown) =
                abi.decode(proposalData, (uint256, uint256, uint256, uint256));

            emergencyCircuitBreaker.configureCircuitBreaker(
                targetAsset,
                priceThreshold,
                volThreshold,
                oracleFailureThreshold,
                cooldown
            );
        }
    }

    function _removeFromActiveProposals(uint256 proposalId) internal {
        for (uint256 i = 0; i < activeProposals.length; i++) {
            if (activeProposals[i] == proposalId) {
                activeProposals[i] = activeProposals[activeProposals.length - 1];
                activeProposals.pop();
                break;
            }
        }
    }

    /**
     * @notice Set voting power for an address
     * @param voter Voter address
     * @param power Voting power
     */
    function setVotingPower(address voter, uint256 power) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(power <= 10000, "Voting power too high");
        votingPower[voter] = power;
    }
}