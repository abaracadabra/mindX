// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./KnowledgeHierarchyDAIO.sol";
import "../settings/DAIO_ConfigurationEngine.sol";

/**
 * @title TriumvirateGovernance
 * @notice Enhanced triumvirate governance with Dev/Com/Mark 2/3 consensus and AI integration
 * @dev Extends KnowledgeHierarchyDAIO with enhanced AI proposal capabilities and economic incentives
 */
contract TriumvirateGovernance is AccessControl, ReentrancyGuard {

    bytes32 public constant AI_PROPOSER_ROLE = keccak256("AI_PROPOSER_ROLE");
    bytes32 public constant HUMAN_VOTER_ROLE = keccak256("HUMAN_VOTER_ROLE");
    bytes32 public constant DOMAIN_MODERATOR_ROLE = keccak256("DOMAIN_MODERATOR_ROLE");

    // Enhanced triumvirate domains
    enum TriumvirateDomain {
        DEVELOPMENT,    // Technical development and architecture
        COMMUNITY,      // Community engagement and governance
        MARKETING       // Marketing and partnerships
    }

    // Proposal types with different consensus requirements
    enum ProposalType {
        OPERATIONAL,    // Day-to-day operations
        STRATEGIC,      // Strategic direction changes
        CONSTITUTIONAL, // Constitutional parameter changes
        ECONOMIC,       // Treasury and economic decisions
        EMERGENCY,      // Emergency actions
        AI_INITIATED    // AI-initiated proposals
    }

    // Voting weights within each domain
    struct DomainVotingStructure {
        uint256 humanVotingWeight;    // 66.67% (2/3)
        uint256 aiVotingWeight;       // 33.33% (1/3)
        uint256 totalHumanVoters;     // Number of registered human voters
        uint256 requiredConsensus;    // Required consensus percentage (default 67%)
    }

    struct EnhancedProposal {
        uint256 id;
        string title;
        string description;
        ProposalType proposalType;
        address proposer;
        bool isAIProposal;            // Whether proposed by AI
        uint256 createdAt;
        uint256 votingEndsAt;
        uint256 executionDelay;       // Delay before execution

        // Triumvirate voting results
        mapping(TriumvirateDomain => DomainVoteResult) domainResults;
        uint256 domainsApproved;      // Number of domains that approved
        uint256 requiredDomains;      // Required domains for approval (default 2/3)

        bool executed;
        bool cancelled;
        ProposalStatus status;

        // Economic integration
        uint256 stakingRequirement;   // Required stake for this proposal
        uint256 totalStaked;          // Total amount staked
        address[] stakeholders;       // Addresses that staked
        mapping(address => uint256) stakes; // Individual stakes
    }

    struct DomainVoteResult {
        uint256 humanVotesFor;
        uint256 humanVotesAgainst;
        uint256 humanVotersParticipated;
        uint256 aiVotesFor;
        uint256 aiVotesAgainst;
        uint256 aiVotingWeight;       // Total AI voting weight in this domain
        bool domainApproved;          // Whether this domain approved
        uint256 finalizedAt;
    }

    struct AIProposalLimits {
        uint256 maxProposalsPerDay;
        uint256 maxStakeAmount;       // Max stake AI can require
        bool canProposeEconomic;      // Whether AI can propose economic decisions
        bool canProposeConstitutional; // Whether AI can propose constitutional changes
        uint256 cooldownPeriod;       // Cooldown between AI proposals
    }

    struct DomainConfiguration {
        uint256 humanVotingWeight;    // Percentage weight for humans (default 67%)
        uint256 aiVotingWeight;       // Percentage weight for AI (default 33%)
        uint256 requiredConsensus;    // Required consensus within domain (default 67%)
        address[] humanVoters;        // Registered human voters in domain
        mapping(address => bool) isHumanVoter; // Human voter registry
        uint256 maxVoters;            // Maximum voters per domain
        uint256 totalHumanVoters;     // Total number of human voters
    }

    // Storage
    mapping(uint256 => EnhancedProposal) public proposals;
    mapping(TriumvirateDomain => DomainConfiguration) public domainConfigs;
    mapping(uint256 => mapping(TriumvirateDomain => mapping(address => bool))) public hasVotedInDomain;
    mapping(uint256 => mapping(address => bool)) public hasVotedOverall;
    mapping(address => uint256) public lastAIProposalTime; // AI proposal cooldown tracking
    mapping(address => uint256) public dailyAIProposalCount; // Daily AI proposal count
    mapping(uint256 => mapping(address => uint256)) public proposalDay; // Track proposal days

    uint256 public proposalCount;
    uint256 public requiredDomainsForApproval = 2; // 2 out of 3 domains (67%)

    // Integration contracts
    KnowledgeHierarchyDAIO public knowledgeHierarchy;
    DAIO_ConfigurationEngine public configEngine;

    AIProposalLimits public aiLimits;

    // Events
    event EnhancedProposalCreated(
        uint256 indexed proposalId,
        string title,
        ProposalType proposalType,
        address indexed proposer,
        bool isAIProposal,
        uint256 stakingRequirement
    );

    event DomainVoteCast(
        uint256 indexed proposalId,
        TriumvirateDomain indexed domain,
        address indexed voter,
        bool isAI,
        bool support,
        uint256 votingWeight
    );

    event DomainResultFinalized(
        uint256 indexed proposalId,
        TriumvirateDomain indexed domain,
        bool approved,
        uint256 humanVotesFor,
        uint256 aiVotesFor
    );

    event ProposalApproved(
        uint256 indexed proposalId,
        uint256 domainsApproved,
        uint256 requiredDomains
    );

    event ProposalExecuted(
        uint256 indexed proposalId,
        address indexed executor
    );

    event AIProposalLimitsUpdated(
        uint256 maxProposalsPerDay,
        uint256 maxStakeAmount,
        bool canProposeEconomic
    );

    event DomainConfigurationUpdated(
        TriumvirateDomain indexed domain,
        uint256 humanWeight,
        uint256 aiWeight,
        uint256 requiredConsensus
    );

    enum ProposalStatus {
        PENDING,
        ACTIVE,
        SUCCEEDED,
        DEFEATED,
        EXECUTED,
        CANCELLED,
        EXPIRED
    }

    modifier onlyAIProposer() {
        require(hasRole(AI_PROPOSER_ROLE, msg.sender), "Not authorized AI proposer");
        _;
    }

    modifier onlyHumanVoter(TriumvirateDomain domain) {
        require(domainConfigs[domain].isHumanVoter[msg.sender], "Not registered human voter");
        _;
    }

    modifier validProposal(uint256 proposalId) {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal ID");
        require(proposals[proposalId].id > 0, "Proposal doesn't exist");
        _;
    }

    constructor(
        address _knowledgeHierarchy,
        address _configEngine
    ) {
        require(_knowledgeHierarchy != address(0), "Invalid knowledge hierarchy");
        require(_configEngine != address(0), "Invalid config engine");

        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
        configEngine = DAIO_ConfigurationEngine(_configEngine);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(AI_PROPOSER_ROLE, msg.sender);
        _grantRole(HUMAN_VOTER_ROLE, msg.sender);

        _initializeTriumvirate();
        _initializeAILimits();
    }

    /**
     * @notice Create enhanced proposal with triumvirate voting
     * @param title Proposal title
     * @param description Detailed description
     * @param proposalType Type of proposal
     * @param stakingRequirement Required stake amount
     * @param executionDelay Delay before execution (in seconds)
     */
    function createEnhancedProposal(
        string memory title,
        string memory description,
        ProposalType proposalType,
        uint256 stakingRequirement,
        uint256 executionDelay
    ) external payable returns (uint256 proposalId) {
        require(bytes(title).length > 0, "Title required");
        require(msg.value >= stakingRequirement, "Insufficient stake");

        bool isAI = hasRole(AI_PROPOSER_ROLE, msg.sender);

        if (isAI) {
            require(_validateAIProposal(proposalType, stakingRequirement), "AI proposal limits exceeded");
        }

        proposalCount++;
        uint256 votingPeriod = configEngine.getParameter("proposal_period") * 13; // Convert blocks to seconds

        EnhancedProposal storage proposal = proposals[proposalCount];
        proposal.id = proposalCount;
        proposal.title = title;
        proposal.description = description;
        proposal.proposalType = proposalType;
        proposal.proposer = msg.sender;
        proposal.isAIProposal = isAI;
        proposal.createdAt = block.timestamp;
        proposal.votingEndsAt = block.timestamp + votingPeriod;
        proposal.executionDelay = executionDelay;
        proposal.stakingRequirement = stakingRequirement;
        proposal.totalStaked = msg.value;
        proposal.requiredDomains = requiredDomainsForApproval;
        proposal.status = ProposalStatus.ACTIVE;

        if (msg.value > 0) {
            proposal.stakeholders.push(msg.sender);
            proposal.stakes[msg.sender] = msg.value;
        }

        if (isAI) {
            _trackAIProposal(msg.sender);
        }

        emit EnhancedProposalCreated(
            proposalCount,
            title,
            proposalType,
            msg.sender,
            isAI,
            stakingRequirement
        );

        return proposalCount;
    }

    /**
     * @notice Vote on proposal within a specific domain
     * @param proposalId Proposal ID
     * @param domain Triumvirate domain
     * @param support True for support, false for opposition
     */
    function voteInDomain(
        uint256 proposalId,
        TriumvirateDomain domain,
        bool support
    ) external validProposal(proposalId) nonReentrant {
        EnhancedProposal storage proposal = proposals[proposalId];
        require(proposal.status == ProposalStatus.ACTIVE, "Proposal not active");
        require(block.timestamp < proposal.votingEndsAt, "Voting ended");
        require(!hasVotedInDomain[proposalId][domain][msg.sender], "Already voted in domain");

        bool isAI = hasRole(AI_PROPOSER_ROLE, msg.sender);
        bool isHuman = domainConfigs[domain].isHumanVoter[msg.sender];

        require(isAI || isHuman, "Not authorized to vote in this domain");

        hasVotedInDomain[proposalId][domain][msg.sender] = true;

        DomainVoteResult storage domainResult = proposal.domainResults[domain];

        if (isHuman) {
            domainResult.humanVotersParticipated++;
            if (support) {
                domainResult.humanVotesFor++;
            } else {
                domainResult.humanVotesAgainst++;
            }
        } else if (isAI) {
            // Get AI voting weight from knowledge hierarchy
            // For now, use a simplified weight - would integrate with KnowledgeHierarchyDAIO
            uint256 aiWeight = 10; // Simplified weight for AI agents

            domainResult.aiVotingWeight += aiWeight;

            if (support) {
                domainResult.aiVotesFor += aiWeight;
            } else {
                domainResult.aiVotesAgainst += aiWeight;
            }
        }

        emit DomainVoteCast(proposalId, domain, msg.sender, isAI, support, isAI ? 10 : 1);

        _checkDomainResult(proposalId, domain);
        _checkOverallProposalStatus(proposalId);
    }

    /**
     * @notice Add stake to existing proposal
     * @param proposalId Proposal ID
     */
    function addStakeToProposal(uint256 proposalId) external payable validProposal(proposalId) {
        require(msg.value > 0, "Must send ETH to stake");

        EnhancedProposal storage proposal = proposals[proposalId];
        require(proposal.status == ProposalStatus.ACTIVE, "Proposal not active");

        proposal.totalStaked += msg.value;

        if (proposal.stakes[msg.sender] == 0) {
            proposal.stakeholders.push(msg.sender);
        }
        proposal.stakes[msg.sender] += msg.value;
    }

    /**
     * @notice Execute approved proposal
     * @param proposalId Proposal ID
     */
    function executeProposal(uint256 proposalId) external validProposal(proposalId) nonReentrant {
        EnhancedProposal storage proposal = proposals[proposalId];
        require(proposal.status == ProposalStatus.SUCCEEDED, "Proposal not approved");
        require(!proposal.executed, "Already executed");
        require(
            block.timestamp >= proposal.votingEndsAt + proposal.executionDelay,
            "Execution delay not passed"
        );

        proposal.executed = true;
        proposal.status = ProposalStatus.EXECUTED;

        // Execute proposal logic would go here
        // Integration with existing DAIO execution mechanisms

        emit ProposalExecuted(proposalId, msg.sender);
    }

    /**
     * @notice Register human voter in domain
     * @param domain Triumvirate domain
     * @param voter Voter address
     */
    function registerHumanVoter(
        TriumvirateDomain domain,
        address voter
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(voter != address(0), "Invalid voter");
        require(!domainConfigs[domain].isHumanVoter[voter], "Already registered");
        require(domainConfigs[domain].humanVoters.length < domainConfigs[domain].maxVoters, "Max voters reached");

        domainConfigs[domain].isHumanVoter[voter] = true;
        domainConfigs[domain].humanVoters.push(voter);
        domainConfigs[domain].totalHumanVoters++;

        _grantRole(HUMAN_VOTER_ROLE, voter);
    }

    /**
     * @notice Update AI proposal limits
     * @param maxProposalsPerDay Maximum proposals per day
     * @param maxStakeAmount Maximum stake amount
     * @param canProposeEconomic Whether AI can propose economic decisions
     * @param canProposeConstitutional Whether AI can propose constitutional changes
     */
    function updateAILimits(
        uint256 maxProposalsPerDay,
        uint256 maxStakeAmount,
        bool canProposeEconomic,
        bool canProposeConstitutional
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        aiLimits.maxProposalsPerDay = maxProposalsPerDay;
        aiLimits.maxStakeAmount = maxStakeAmount;
        aiLimits.canProposeEconomic = canProposeEconomic;
        aiLimits.canProposeConstitutional = canProposeConstitutional;

        emit AIProposalLimitsUpdated(maxProposalsPerDay, maxStakeAmount, canProposeEconomic);
    }

    /**
     * @notice Update domain configuration
     * @param domain Triumvirate domain
     * @param humanWeight Human voting weight percentage
     * @param aiWeight AI voting weight percentage
     * @param requiredConsensus Required consensus percentage
     */
    function updateDomainConfiguration(
        TriumvirateDomain domain,
        uint256 humanWeight,
        uint256 aiWeight,
        uint256 requiredConsensus
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(humanWeight + aiWeight == 100, "Weights must sum to 100");
        require(requiredConsensus >= 50 && requiredConsensus <= 100, "Invalid consensus requirement");

        domainConfigs[domain].humanVotingWeight = humanWeight;
        domainConfigs[domain].aiVotingWeight = aiWeight;
        domainConfigs[domain].requiredConsensus = requiredConsensus;

        emit DomainConfigurationUpdated(domain, humanWeight, aiWeight, requiredConsensus);
    }

    /**
     * @notice Get proposal details
     * @param proposalId Proposal ID
     * @return id Proposal ID
     * @return title Proposal title
     * @return description Proposal description
     * @return proposalType Type of proposal
     * @return proposer Proposer address
     * @return isAIProposal Whether proposed by AI
     * @return createdAt Creation timestamp
     * @return votingEndsAt Voting end timestamp
     * @return domainsApproved Number of domains approved
     * @return requiredDomains Required domains for approval
     * @return executed Whether executed
     * @return status Proposal status
     * @return totalStaked Total staked amount
     */
    function getProposal(uint256 proposalId) external view validProposal(proposalId) returns (
        uint256 id,
        string memory title,
        string memory description,
        ProposalType proposalType,
        address proposer,
        bool isAIProposal,
        uint256 createdAt,
        uint256 votingEndsAt,
        uint256 domainsApproved,
        uint256 requiredDomains,
        bool executed,
        ProposalStatus status,
        uint256 totalStaked
    ) {
        EnhancedProposal storage proposal = proposals[proposalId];
        return (
            proposal.id,
            proposal.title,
            proposal.description,
            proposal.proposalType,
            proposal.proposer,
            proposal.isAIProposal,
            proposal.createdAt,
            proposal.votingEndsAt,
            proposal.domainsApproved,
            proposal.requiredDomains,
            proposal.executed,
            proposal.status,
            proposal.totalStaked
        );
    }

    /**
     * @notice Get domain vote result
     * @param proposalId Proposal ID
     * @param domain Triumvirate domain
     * @return Domain vote result
     */
    function getDomainResult(uint256 proposalId, TriumvirateDomain domain) external view validProposal(proposalId) returns (DomainVoteResult memory) {
        return proposals[proposalId].domainResults[domain];
    }

    /**
     * @notice Initialize triumvirate structure
     */
    function _initializeTriumvirate() internal {
        // Initialize each domain with 2/3 human, 1/3 AI voting structure
        for (uint i = 0; i < 3; i++) {
            TriumvirateDomain domain = TriumvirateDomain(i);
            domainConfigs[domain].humanVotingWeight = 67; // 67%
            domainConfigs[domain].aiVotingWeight = 33;    // 33%
            domainConfigs[domain].requiredConsensus = 67; // 67%
            domainConfigs[domain].maxVoters = 10;         // Max 10 voters per domain
        }
    }

    /**
     * @notice Initialize AI proposal limits
     */
    function _initializeAILimits() internal {
        aiLimits.maxProposalsPerDay = 5;
        aiLimits.maxStakeAmount = 10 ether;
        aiLimits.canProposeEconomic = false;      // Initially restricted
        aiLimits.canProposeConstitutional = false; // Initially restricted
        aiLimits.cooldownPeriod = 1 hours;
    }

    /**
     * @notice Validate AI proposal against limits
     * @param proposalType Type of proposal
     * @param stakingRequirement Required stake
     * @return valid Whether proposal is valid
     */
    function _validateAIProposal(
        ProposalType proposalType,
        uint256 stakingRequirement
    ) internal view returns (bool) {
        if (block.timestamp - lastAIProposalTime[msg.sender] < aiLimits.cooldownPeriod) {
            return false;
        }

        if (dailyAIProposalCount[msg.sender] >= aiLimits.maxProposalsPerDay) {
            return false;
        }

        if (stakingRequirement > aiLimits.maxStakeAmount) {
            return false;
        }

        if (proposalType == ProposalType.ECONOMIC && !aiLimits.canProposeEconomic) {
            return false;
        }

        if (proposalType == ProposalType.CONSTITUTIONAL && !aiLimits.canProposeConstitutional) {
            return false;
        }

        return true;
    }

    /**
     * @notice Track AI proposal for rate limiting
     * @param aiProposer AI proposer address
     */
    function _trackAIProposal(address aiProposer) internal {
        lastAIProposalTime[aiProposer] = block.timestamp;

        uint256 currentDay = block.timestamp / 86400; // 24 hours in seconds
        if (proposalDay[dailyAIProposalCount[aiProposer]][aiProposer] != currentDay) {
            dailyAIProposalCount[aiProposer] = 1;
        } else {
            dailyAIProposalCount[aiProposer]++;
        }
        proposalDay[dailyAIProposalCount[aiProposer]][aiProposer] = currentDay;
    }

    /**
     * @notice Check domain voting result and finalize if needed
     * @param proposalId Proposal ID
     * @param domain Triumvirate domain
     */
    function _checkDomainResult(uint256 proposalId, TriumvirateDomain domain) internal {
        DomainVoteResult storage result = proposals[proposalId].domainResults[domain];

        if (result.finalizedAt == 0) {
            // Check if domain has reached consensus
            uint256 totalHumanVotes = result.humanVotesFor + result.humanVotesAgainst;
            uint256 totalAIVotes = result.aiVotesFor + result.aiVotesAgainst;

            // Calculate weighted votes
            uint256 humanWeight = domainConfigs[domain].humanVotingWeight;
            uint256 aiWeight = domainConfigs[domain].aiVotingWeight;

            uint256 weightedForVotes = (result.humanVotesFor * humanWeight) + (result.aiVotesFor * aiWeight);
            uint256 totalWeightedVotes = (totalHumanVotes * humanWeight) + (totalAIVotes * aiWeight);

            uint256 requiredConsensus = domainConfigs[domain].requiredConsensus;

            if (totalWeightedVotes > 0 && weightedForVotes * 100 >= totalWeightedVotes * requiredConsensus) {
                result.domainApproved = true;
                result.finalizedAt = block.timestamp;
                proposals[proposalId].domainsApproved++;

                emit DomainResultFinalized(proposalId, domain, true, result.humanVotesFor, result.aiVotesFor);
            }
        }
    }

    /**
     * @notice Check overall proposal status
     * @param proposalId Proposal ID
     */
    function _checkOverallProposalStatus(uint256 proposalId) internal {
        EnhancedProposal storage proposal = proposals[proposalId];

        if (proposal.domainsApproved >= proposal.requiredDomains) {
            proposal.status = ProposalStatus.SUCCEEDED;
            emit ProposalApproved(proposalId, proposal.domainsApproved, proposal.requiredDomains);
        } else if (block.timestamp >= proposal.votingEndsAt) {
            proposal.status = ProposalStatus.DEFEATED;
        }
    }
}