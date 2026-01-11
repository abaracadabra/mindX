// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title KnowledgeHierarchyDAIO
 * @dev Agent registry and governance proposal system for DAIO.
 *
 * Governance Model:
 * - Human Vote: 66.67% (Development, Marketing, Community subcomponents)
 * - AI Vote: 33.33% (Knowledge-weighted agent aggregation)
 * - Execution: 2/3 majority required, timelock delays
 */
contract KnowledgeHierarchyDAIO is AccessControl, ReentrancyGuard, Pausable {
    // Roles
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant AGENT_MANAGER_ROLE = keccak256("AGENT_MANAGER_ROLE");
    bytes32 public constant PROPOSER_ROLE = keccak256("PROPOSER_ROLE");

    // Subcomponent types for human voting
    enum SubComponent {
        Development,
        Marketing,
        Community
    }

    // Domain types for agent specialization
    enum Domain {
        AI,
        Blockchain,
        Finance,
        Healthcare,
        Infrastructure,
        Security,
        Research,
        General
    }

    // Proposal status
    enum ProposalStatus {
        Pending,
        Active,
        Defeated,
        Succeeded,
        Queued,
        Executed,
        Cancelled
    }

    // Agent structure
    struct Agent {
        bytes32 agentId;               // Unique agent identifier
        uint32 knowledgeLevel;         // Knowledge level (0-100)
        Domain domain;                 // Agent domain specialization
        bool active;                   // Active status
        uint40 registeredAt;           // Registration timestamp
        uint40 lastActiveTime;         // Last activity timestamp
        uint256 proposalCount;         // Proposals created
        uint256 voteCount;             // Votes cast
    }

    // Proposal structure
    struct Proposal {
        uint256 id;
        address proposer;
        string description;
        bytes32 actionHash;            // Hash of the action to execute
        address[] targets;             // Target contracts
        uint256[] values;              // ETH values
        bytes[] calldatas;             // Calldata
        uint40 startTime;              // Voting start time
        uint40 endTime;                // Voting end time
        uint256 voteCountDev;          // Development votes
        uint256 voteCountMarketing;    // Marketing votes
        uint256 voteCountCommunity;    // Community votes
        uint256 voteCountAI;           // Aggregated AI agent vote (knowledge-weighted)
        ProposalStatus status;
        bool executed;
    }

    // Voting power for fractionalized NFT holders
    struct VotingPower {
        uint256 power;
        SubComponent subComponent;
        bool hasVoted;
    }

    // Constants
    uint32 public constant MAX_KNOWLEDGE_LEVEL = 100;
    uint256 public constant VOTING_PERIOD = 7 days;
    uint256 public constant QUORUM_THRESHOLD = 6667; // 66.67% in basis points
    uint256 public constant AI_VOTE_WEIGHT = 3333;   // 33.33% in basis points
    uint256 public constant BASIS_POINTS = 10000;

    // State
    TimelockController public timelock;
    uint256 public proposalCount;
    uint256 public totalAgentVotes;
    uint256 public agentTimeout = 365 days;

    mapping(address => Agent) public agents;
    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => mapping(address => VotingPower)) public voterPower;
    mapping(bytes32 => uint256) public agentIdToProposalCount;

    // Agent tracking
    address[] public registeredAgents;
    mapping(Domain => address[]) public agentsByDomain;

    // Events
    event AgentRegistered(
        address indexed agentAddress,
        bytes32 indexed agentId,
        uint32 knowledgeLevel,
        Domain domain
    );

    event AgentUpdated(
        address indexed agentAddress,
        uint32 knowledgeLevel,
        Domain domain,
        bool active
    );

    event AgentDeactivated(
        address indexed agentAddress,
        uint40 timestamp
    );

    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        string description
    );

    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        SubComponent subComponent,
        bool support,
        uint256 weight
    );

    event AIVoteCast(
        uint256 indexed proposalId,
        address indexed agent,
        bool support,
        uint32 knowledgeWeight
    );

    event AIVoteAggregated(
        uint256 indexed proposalId,
        uint256 totalAIVotes
    );

    event ProposalExecuted(
        uint256 indexed proposalId,
        uint40 timestamp
    );

    event ProposalQueued(
        uint256 indexed proposalId,
        uint40 eta
    );

    event ProposalCancelled(
        uint256 indexed proposalId
    );

    // Errors
    error AgentNotActive();
    error AgentAlreadyRegistered();
    error ProposalNotActive();
    error AlreadyVoted();
    error VotingEnded();
    error VotingNotEnded();
    error ProposalAlreadyExecuted();
    error InsufficientKnowledgeLevel();
    error QuorumNotReached();

    constructor(TimelockController _timelock) {
        timelock = _timelock;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, msg.sender);
        _grantRole(AGENT_MANAGER_ROLE, msg.sender);
        _grantRole(PROPOSER_ROLE, msg.sender);
    }

    // ============ Agent Management ============

    /**
     * @dev Registers a new agent
     * @param agentAddress Agent's wallet address
     * @param knowledgeLevel Initial knowledge level (0-100)
     * @param domain Agent's domain specialization
     * @return agentId Unique identifier for the agent
     */
    function registerAgent(
        address agentAddress,
        uint32 knowledgeLevel,
        Domain domain
    ) external onlyRole(AGENT_MANAGER_ROLE) returns (bytes32 agentId) {
        if (agents[agentAddress].registeredAt != 0) revert AgentAlreadyRegistered();
        require(knowledgeLevel <= MAX_KNOWLEDGE_LEVEL, "Knowledge level exceeds max");

        agentId = keccak256(abi.encodePacked(
            agentAddress,
            domain,
            block.timestamp
        ));

        agents[agentAddress] = Agent({
            agentId: agentId,
            knowledgeLevel: knowledgeLevel,
            domain: domain,
            active: true,
            registeredAt: uint40(block.timestamp),
            lastActiveTime: uint40(block.timestamp),
            proposalCount: 0,
            voteCount: 0
        });

        totalAgentVotes += knowledgeLevel;
        registeredAgents.push(agentAddress);
        agentsByDomain[domain].push(agentAddress);

        emit AgentRegistered(agentAddress, agentId, knowledgeLevel, domain);
        return agentId;
    }

    /**
     * @dev Updates an existing agent
     * @param agentAddress Agent's wallet address
     * @param knowledgeLevel New knowledge level
     * @param domain New domain specialization
     * @param active Active status
     */
    function updateAgent(
        address agentAddress,
        uint32 knowledgeLevel,
        Domain domain,
        bool active
    ) external onlyRole(AGENT_MANAGER_ROLE) {
        Agent storage agent = agents[agentAddress];
        require(agent.registeredAt != 0, "Agent not registered");
        require(knowledgeLevel <= MAX_KNOWLEDGE_LEVEL, "Knowledge level exceeds max");

        // Update total votes
        totalAgentVotes = totalAgentVotes - agent.knowledgeLevel + knowledgeLevel;

        agent.knowledgeLevel = knowledgeLevel;
        agent.domain = domain;
        agent.active = active;
        agent.lastActiveTime = uint40(block.timestamp);

        emit AgentUpdated(agentAddress, knowledgeLevel, domain, active);
    }

    /**
     * @dev Deactivates inactive agents
     * @param batchSize Number of agents to check
     */
    function deactivateInactiveAgents(uint256 batchSize) external onlyRole(AGENT_MANAGER_ROLE) {
        uint256 checked = 0;
        uint256 agentCount = registeredAgents.length;

        for (uint256 i = 0; i < agentCount && checked < batchSize; i++) {
            address agentAddress = registeredAgents[i];
            Agent storage agent = agents[agentAddress];

            if (agent.active && block.timestamp > agent.lastActiveTime + agentTimeout) {
                agent.active = false;
                totalAgentVotes -= agent.knowledgeLevel;
                emit AgentDeactivated(agentAddress, uint40(block.timestamp));
            }
            checked++;
        }
    }

    // ============ Proposal Management ============

    /**
     * @dev Creates a new proposal
     * @param description Proposal description
     * @param targets Target contract addresses
     * @param values ETH values for each call
     * @param calldatas Calldata for each call
     * @return proposalId The new proposal ID
     */
    function createProposal(
        string memory description,
        address[] memory targets,
        uint256[] memory values,
        bytes[] memory calldatas
    ) external onlyRole(PROPOSER_ROLE) whenNotPaused returns (uint256 proposalId) {
        require(targets.length == values.length && values.length == calldatas.length, "Length mismatch");
        require(targets.length > 0, "Empty proposal");

        proposalCount++;
        proposalId = proposalCount;

        bytes32 actionHash = keccak256(abi.encode(targets, values, calldatas));

        proposals[proposalId] = Proposal({
            id: proposalId,
            proposer: msg.sender,
            description: description,
            actionHash: actionHash,
            targets: targets,
            values: values,
            calldatas: calldatas,
            startTime: uint40(block.timestamp),
            endTime: uint40(block.timestamp + VOTING_PERIOD),
            voteCountDev: 0,
            voteCountMarketing: 0,
            voteCountCommunity: 0,
            voteCountAI: 0,
            status: ProposalStatus.Active,
            executed: false
        });

        emit ProposalCreated(proposalId, msg.sender, description);
        return proposalId;
    }

    // ============ Human Voting ============

    /**
     * @dev Casts a vote from a human subcomponent member
     * @param proposalId Proposal to vote on
     * @param subComponent Voter's subcomponent
     * @param support Whether to support the proposal
     * @param votingPower Voting power (from fractionalized NFT)
     */
    function voteOnProposal(
        uint256 proposalId,
        SubComponent subComponent,
        bool support,
        uint256 votingPower
    ) external nonReentrant whenNotPaused {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.timestamp < proposal.endTime, "Voting ended");
        require(!hasVoted[proposalId][msg.sender], "Already voted");
        require(votingPower > 0, "No voting power");

        hasVoted[proposalId][msg.sender] = true;
        voterPower[proposalId][msg.sender] = VotingPower({
            power: votingPower,
            subComponent: subComponent,
            hasVoted: true
        });

        if (support) {
            if (subComponent == SubComponent.Development) {
                proposal.voteCountDev += votingPower;
            } else if (subComponent == SubComponent.Marketing) {
                proposal.voteCountMarketing += votingPower;
            } else if (subComponent == SubComponent.Community) {
                proposal.voteCountCommunity += votingPower;
            }
        }

        emit VoteCast(proposalId, msg.sender, subComponent, support, votingPower);
    }

    // ============ AI Agent Voting ============

    /**
     * @dev Casts a vote from an AI agent (knowledge-weighted)
     * @param proposalId Proposal to vote on
     * @param support Whether to support the proposal
     */
    function agentVote(
        uint256 proposalId,
        bool support
    ) external nonReentrant whenNotPaused {
        Agent storage agent = agents[msg.sender];
        Proposal storage proposal = proposals[proposalId];

        if (!agent.active) revert AgentNotActive();
        if (agent.knowledgeLevel == 0) revert InsufficientKnowledgeLevel();
        if (proposal.status != ProposalStatus.Active) revert ProposalNotActive();
        if (block.timestamp >= proposal.endTime) revert VotingEnded();
        if (hasVoted[proposalId][msg.sender]) revert AlreadyVoted();

        hasVoted[proposalId][msg.sender] = true;
        agent.voteCount++;
        agent.lastActiveTime = uint40(block.timestamp);

        if (support) {
            proposal.voteCountAI += agent.knowledgeLevel;
        }

        emit AIVoteCast(proposalId, msg.sender, support, agent.knowledgeLevel);
        emit AIVoteAggregated(proposalId, proposal.voteCountAI);
    }

    // ============ Vote Aggregation ============

    /**
     * @dev Aggregates votes and determines proposal outcome
     * @param proposalId Proposal to aggregate
     * @return passed Whether the proposal passed
     */
    function aggregateVotes(uint256 proposalId) public view returns (bool passed) {
        Proposal storage proposal = proposals[proposalId];

        // Calculate human votes (66.67% weight)
        uint256 humanVotes = proposal.voteCountDev +
                            proposal.voteCountMarketing +
                            proposal.voteCountCommunity;

        // Calculate AI votes (33.33% weight, normalized)
        uint256 aiVotesNormalized = totalAgentVotes > 0 ?
            (proposal.voteCountAI * humanVotes) / totalAgentVotes :
            0;

        // Total weighted votes
        uint256 totalVotes = humanVotes + aiVotesNormalized;

        // Calculate quorum requirement (2/3 of potential votes)
        uint256 requiredVotes = (humanVotes * QUORUM_THRESHOLD) / BASIS_POINTS;

        return totalVotes >= requiredVotes;
    }

    /**
     * @dev Finalizes voting and updates proposal status
     * @param proposalId Proposal to finalize
     */
    function finalizeProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.timestamp >= proposal.endTime, "Voting not ended");

        if (aggregateVotes(proposalId)) {
            proposal.status = ProposalStatus.Succeeded;
        } else {
            proposal.status = ProposalStatus.Defeated;
        }
    }

    // ============ Proposal Execution ============

    /**
     * @dev Queues a successful proposal for execution
     * @param proposalId Proposal to queue
     */
    function queueProposal(uint256 proposalId) external onlyRole(GOVERNANCE_ROLE) {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.status == ProposalStatus.Succeeded, "Proposal not succeeded");

        bytes32 id = timelock.hashOperationBatch(
            proposal.targets,
            proposal.values,
            proposal.calldatas,
            bytes32(0),
            bytes32(proposalId)
        );

        timelock.scheduleBatch(
            proposal.targets,
            proposal.values,
            proposal.calldatas,
            bytes32(0),
            bytes32(proposalId),
            timelock.getMinDelay()
        );

        proposal.status = ProposalStatus.Queued;
        emit ProposalQueued(proposalId, uint40(block.timestamp + timelock.getMinDelay()));
    }

    /**
     * @dev Executes a queued proposal
     * @param proposalId Proposal to execute
     */
    function executeProposal(uint256 proposalId) external onlyRole(GOVERNANCE_ROLE) nonReentrant {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.status == ProposalStatus.Queued, "Proposal not queued");
        require(!proposal.executed, "Already executed");

        timelock.executeBatch(
            proposal.targets,
            proposal.values,
            proposal.calldatas,
            bytes32(0),
            bytes32(proposalId)
        );

        proposal.executed = true;
        proposal.status = ProposalStatus.Executed;

        emit ProposalExecuted(proposalId, uint40(block.timestamp));
    }

    /**
     * @dev Cancels a proposal
     * @param proposalId Proposal to cancel
     */
    function cancelProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];

        require(
            msg.sender == proposal.proposer || hasRole(GOVERNANCE_ROLE, msg.sender),
            "Not authorized"
        );
        require(proposal.status == ProposalStatus.Active || proposal.status == ProposalStatus.Queued, "Cannot cancel");

        if (proposal.status == ProposalStatus.Queued) {
            timelock.cancel(
                timelock.hashOperationBatch(
                    proposal.targets,
                    proposal.values,
                    proposal.calldatas,
                    bytes32(0),
                    bytes32(proposalId)
                )
            );
        }

        proposal.status = ProposalStatus.Cancelled;
        emit ProposalCancelled(proposalId);
    }

    // ============ View Functions ============

    /**
     * @dev Gets agent data
     * @param agentAddress Agent to query
     * @return agent The agent data
     */
    function getAgent(address agentAddress) external view returns (Agent memory agent) {
        return agents[agentAddress];
    }

    /**
     * @dev Gets proposal data
     * @param proposalId Proposal to query
     * @return proposal The proposal data
     */
    function getProposal(uint256 proposalId) external view returns (Proposal memory proposal) {
        return proposals[proposalId];
    }

    /**
     * @dev Gets all agents in a domain
     * @param domain Domain to query
     * @return Array of agent addresses
     */
    function getAgentsByDomain(Domain domain) external view returns (address[] memory) {
        return agentsByDomain[domain];
    }

    /**
     * @dev Gets the total number of registered agents
     * @return count Number of agents
     */
    function getAgentCount() external view returns (uint256 count) {
        return registeredAgents.length;
    }

    /**
     * @dev Gets proposal vote counts
     * @param proposalId Proposal to query
     * @return dev Development votes
     * @return marketing Marketing votes
     * @return community Community votes
     * @return ai AI votes
     */
    function getVoteCounts(uint256 proposalId) external view returns (
        uint256 dev,
        uint256 marketing,
        uint256 community,
        uint256 ai
    ) {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.voteCountDev,
            proposal.voteCountMarketing,
            proposal.voteCountCommunity,
            proposal.voteCountAI
        );
    }

    // ============ Admin Functions ============

    /**
     * @dev Updates the agent timeout period
     * @param newTimeout New timeout in seconds
     */
    function setAgentTimeout(uint256 newTimeout) external onlyRole(GOVERNANCE_ROLE) {
        agentTimeout = newTimeout;
    }

    /**
     * @dev Pauses the contract
     */
    function pause() external onlyRole(GOVERNANCE_ROLE) {
        _pause();
    }

    /**
     * @dev Unpauses the contract
     */
    function unpause() external onlyRole(GOVERNANCE_ROLE) {
        _unpause();
    }
}
