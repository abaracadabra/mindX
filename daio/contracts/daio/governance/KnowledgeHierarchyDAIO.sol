// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../constitution/DAIO_Constitution.sol";

/**
 * @title KnowledgeHierarchyDAIO
 * @notice Production governance contract with knowledge-weighted AI voting
 * @dev Implements 66.67% human voting (Development, Marketing, Community) and 33.33% AI voting
 * @dev Migrated from DAIO4 with OpenZeppelin v5 compatibility
 */
contract KnowledgeHierarchyDAIO is ReentrancyGuard, Ownable {
    enum SubComponent { Development, Marketing, Community }
    enum Domain { AI, Blockchain, Finance, Healthcare, General }

    struct Agent {
        uint256 knowledgeLevel;  // 0-100, determines voting weight
        Domain domain;
        bool active;
        uint256 lastActiveTime;
        address idNFTTokenId;     // Optional: link to IDNFT
    }

    struct Proposal {
        uint256 id;
        bool executed;
        string description;
        uint256 voteCountDev;
        uint256 voteCountMarketing;
        uint256 voteCountCommunity;
        uint256 voteCountAI;      // Aggregated AI agent vote (knowledge-weighted)
        uint256 startBlock;
        uint256 endBlock;
        ProposalStatus status;
    }

    enum ProposalStatus {
        Pending,
        Active,
        Succeeded,
        Defeated,
        Executed,
        Cancelled
    }

    // Storage
    mapping(address => Agent) public agents;
    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;  // proposalId => voter => voted
    mapping(uint256 => mapping(SubComponent => mapping(address => bool))) public subComponentVotes;
    
    uint256 public proposalCount;
    uint256 public totalAgentVotes;  // Total knowledge-weighted voting power
    uint256 public constant MAX_KNOWLEDGE_LEVEL = 100;
    uint256 public timeout = 365 days;
    uint256 public votingPeriod = 45818;  // ~1 week in blocks (assuming 13s block time)
    
    // Integrated contracts
    TimelockController public timelock;
    DAIO_Constitution public constitution;

    // Events
    event AgentUpdated(
        address indexed agentAddress,
        uint256 knowledgeLevel,
        Domain domain,
        bool active
    );
    event ProposalCreated(uint256 indexed proposalId, string description);
    event ProposalExecuted(uint256 indexed proposalId);
    event AIVoteAggregated(uint256 indexed proposalId, uint256 totalVotes);
    event HumanVoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        SubComponent subComponent,
        bool support
    );
    event AgentVoteCast(
        uint256 indexed proposalId,
        address indexed agent,
        bool support,
        uint256 votingWeight
    );

    modifier onlyGovernance() {
        require(
            timelock.hasRole(timelock.EXECUTOR_ROLE(), msg.sender),
            "Caller is not governance"
        );
        _;
    }

    modifier onlyConstitution() {
        require(msg.sender == address(constitution), "Only constitution");
        _;
    }

    constructor(
        TimelockController _timelock,
        address _constitution
    ) Ownable(msg.sender) {
        require(address(_timelock) != address(0), "Invalid timelock");
        require(_constitution != address(0), "Invalid constitution");
        timelock = _timelock;
        constitution = DAIO_Constitution(_constitution);
    }

    /**
     * @notice Add or update agent with knowledge level
     * @param _agentAddress Agent address
     * @param _knowledgeLevel Knowledge level (0-100)
     * @param _domain Agent domain
     * @param _active Active status
     */
    function addOrUpdateAgent(
        address _agentAddress,
        uint256 _knowledgeLevel,
        Domain _domain,
        bool _active
    ) external onlyGovernance {
        require(_knowledgeLevel <= MAX_KNOWLEDGE_LEVEL, "Knowledge level exceeds maximum");
        require(_agentAddress != address(0), "Invalid agent address");

        Agent storage agent = agents[_agentAddress];
        uint256 oldKnowledge = agent.knowledgeLevel;
        
        agent.knowledgeLevel = _knowledgeLevel;
        agent.domain = _domain;
        agent.active = _active;
        agent.lastActiveTime = block.timestamp;

        // Update total agent votes
        totalAgentVotes = totalAgentVotes - oldKnowledge + _knowledgeLevel;

        emit AgentUpdated(_agentAddress, _knowledgeLevel, _domain, _active);
    }

    /**
     * @notice Create a governance proposal
     * @param description Proposal description
     * @return proposalId The created proposal ID
     */
    function createProposal(
        string memory description
    ) public onlyGovernance returns (uint256) {
        proposalCount++;
        proposals[proposalCount] = Proposal({
            id: proposalCount,
            executed: false,
            description: description,
            voteCountDev: 0,
            voteCountMarketing: 0,
            voteCountCommunity: 0,
            voteCountAI: 0,
            startBlock: block.number,
            endBlock: block.number + votingPeriod,
            status: ProposalStatus.Active
        });

        emit ProposalCreated(proposalCount, description);
        return proposalCount;
    }

    /**
     * @notice Human voting within subcomponents
     * @param proposalId Proposal ID
     * @param subComponent Subcomponent (Development, Marketing, Community)
     * @param support True for yes, false for no
     */
    function voteOnProposal(
        uint256 proposalId,
        SubComponent subComponent,
        bool support
    ) external nonReentrant {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.id > 0, "Proposal doesn't exist");
        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.number < proposal.endBlock, "Voting ended");
        require(
            !subComponentVotes[proposalId][subComponent][msg.sender],
            "Already voted in this subcomponent"
        );

        subComponentVotes[proposalId][subComponent][msg.sender] = true;

        if (subComponent == SubComponent.Development) {
            proposal.voteCountDev += support ? 1 : 0;
        } else if (subComponent == SubComponent.Marketing) {
            proposal.voteCountMarketing += support ? 1 : 0;
        } else if (subComponent == SubComponent.Community) {
            proposal.voteCountCommunity += support ? 1 : 0;
        }

        emit HumanVoteCast(proposalId, msg.sender, subComponent, support);

        // Check if proposal should be finalized
        _checkProposalStatus(proposalId);
    }

    /**
     * @notice AI agent voting (knowledge-weighted)
     * @param proposalId Proposal ID
     * @param support True for yes, false for no
     */
    function agentVote(
        uint256 proposalId,
        bool support
    ) external nonReentrant {
        Agent storage agent = agents[msg.sender];
        require(agent.active, "Agent must be active to vote");
        require(agent.knowledgeLevel > 0, "Agent has no voting power");

        Proposal storage proposal = proposals[proposalId];
        require(proposal.id > 0, "Proposal doesn't exist");
        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.number < proposal.endBlock, "Voting ended");
        require(!hasVoted[proposalId][msg.sender], "Already voted");

        hasVoted[proposalId][msg.sender] = true;

        if (support) {
            proposal.voteCountAI += agent.knowledgeLevel;
        }

        emit AgentVoteCast(proposalId, msg.sender, support, agent.knowledgeLevel);
        emit AIVoteAggregated(proposalId, proposal.voteCountAI);

        // Check if proposal should be finalized
        _checkProposalStatus(proposalId);
    }

    /**
     * @notice Aggregate votes and determine if proposal succeeds
     * @param proposalId Proposal ID
     * @return success Whether proposal succeeds
     */
    function aggregateVotes(uint256 proposalId) public view returns (bool) {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.id > 0, "Proposal doesn't exist");

        // Human votes: 66.67% weight (2/3)
        uint256 totalHumanVotes = proposal.voteCountDev + 
                                  proposal.voteCountMarketing + 
                                  proposal.voteCountCommunity;
        
        // AI votes: 33.33% weight (1/3)
        uint256 totalAIVotes = proposal.voteCountAI;

        // Calculate weighted totals
        // Human: 2/3 weight, AI: 1/3 weight
        uint256 weightedHuman = (totalHumanVotes * 2) / 3;
        uint256 weightedAI = totalAIVotes;  // Already represents 1/3

        // Proposal succeeds if weighted total >= 2/3 of combined
        uint256 totalWeighted = weightedHuman + weightedAI;
        uint256 required = (totalHumanVotes + totalAIVotes) * 2 / 3;

        return totalWeighted >= required && totalHumanVotes > 0;
    }

    /**
     * @notice Execute a successful proposal
     * @param proposalId Proposal ID
     */
    function executeProposal(uint256 proposalId) external onlyGovernance {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.id > 0, "Proposal doesn't exist");
        require(!proposal.executed, "Proposal already executed");
        require(block.number >= proposal.endBlock, "Voting not ended");
        require(aggregateVotes(proposalId), "Proposal did not pass");

        proposal.executed = true;
        proposal.status = ProposalStatus.Executed;

        emit ProposalExecuted(proposalId);
    }

    /**
     * @notice Check and update proposal status
     * @param proposalId Proposal ID
     */
    function _checkProposalStatus(uint256 proposalId) internal {
        Proposal storage proposal = proposals[proposalId];
        
        if (block.number >= proposal.endBlock) {
            if (aggregateVotes(proposalId)) {
                proposal.status = ProposalStatus.Succeeded;
            } else {
                proposal.status = ProposalStatus.Defeated;
            }
        }
    }

    /**
     * @notice Update voting period
     * @param _votingPeriod New voting period in blocks
     */
    function setVotingPeriod(uint256 _votingPeriod) external onlyOwner {
        require(_votingPeriod > 0, "Invalid voting period");
        votingPeriod = _votingPeriod;
    }

    /**
     * @notice Get proposal details
     * @param proposalId Proposal ID
     * @return Proposal struct
     */
    function getProposal(uint256 proposalId) external view returns (Proposal memory) {
        return proposals[proposalId];
    }

    /**
     * @notice Get agent details
     * @param agentAddress Agent address
     * @return Agent struct
     */
    function getAgent(address agentAddress) external view returns (Agent memory) {
        return agents[agentAddress];
    }

    /**
     * @notice Deactivate inactive agents (batch operation)
     * @param agentAddresses Array of agent addresses to check
     */
    function deactivateInactiveAgents(address[] memory agentAddresses) external onlyGovernance {
        for (uint i = 0; i < agentAddresses.length; i++) {
            Agent storage agent = agents[agentAddresses[i]];
            if (agent.active && 
                block.timestamp - agent.lastActiveTime > timeout) {
                totalAgentVotes -= agent.knowledgeLevel;
                agent.active = false;
                emit AgentUpdated(agentAddresses[i], agent.knowledgeLevel, agent.domain, false);
            }
        }
    }
}
