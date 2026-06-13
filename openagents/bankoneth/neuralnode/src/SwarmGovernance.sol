// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./BubbleRoomV4.sol";
import "./EmergenceTraits.sol";

/// @title SwarmGovernance - Consensus and governance within BubbleRooms
/// @notice Measures individual spawn opinion against collective for Wisdom accrual
/// @dev Proposals auto-resolve. Consensus weight feeds into EmergenceTraits.
contract SwarmGovernance {
    BubbleRoomV4 public bubbleRoom;
    EmergenceTraits public traits;

    enum ProposalType {
        SPAWN,       // propose spawning an Emergence
        MUTATE,      // propose mutating the room's Seed
        INTERACT,    // propose Interaction with another room
        GOVERN,      // governance change (roles, access)
        CUSTOM       // free-form proposal
    }

    struct Proposal {
        uint256 roomId;
        ProposalType proposalType;
        string description;
        string metadata;       // IPFS CID or JSON for proposal details
        uint256 forCount;
        uint256 againstCount;
        uint256 deadline;
        bool resolved;
        bool outcome;
        address proposer;
        mapping(address => bool) hasVoted;
        mapping(address => bool) votedFor;
    }

    uint256 public nextProposalId = 1;
    mapping(uint256 => Proposal) public proposals;
    // Room ID => active proposal IDs
    mapping(uint256 => uint256[]) public activeProposals;

    event ProposalCreated(
        uint256 indexed proposalId,
        uint256 indexed roomId,
        ProposalType proposalType,
        string description,
        address proposer,
        uint256 deadline
    );
    event Voted(uint256 indexed proposalId, address voter, bool inFavor);
    event ProposalResolved(uint256 indexed proposalId, bool outcome, uint256 forCount, uint256 againstCount);

    constructor(address bubbleRoomAddress, address traitsAddress) {
        bubbleRoom = BubbleRoomV4(bubbleRoomAddress);
        traits = EmergenceTraits(traitsAddress);
    }

    /// @notice Create a proposal within a room's Swarm
    /// @param votingPeriod Duration in seconds for voting
    function createProposal(
        uint256 roomId,
        ProposalType proposalType,
        string memory description,
        string memory metadata,
        uint256 votingPeriod
    ) external returns (uint256) {
        require(_isParticipant(roomId, msg.sender), "Not participant");
        require(votingPeriod >= 1 hours && votingPeriod <= 30 days, "Invalid voting period");

        uint256 proposalId = nextProposalId++;
        Proposal storage p = proposals[proposalId];
        p.roomId = roomId;
        p.proposalType = proposalType;
        p.description = description;
        p.metadata = metadata;
        p.deadline = block.timestamp + votingPeriod;
        p.proposer = msg.sender;

        activeProposals[roomId].push(proposalId);

        emit ProposalCreated(proposalId, roomId, proposalType, description, msg.sender, p.deadline);
        return proposalId;
    }

    /// @notice Vote on a proposal
    /// @dev Individual opinion measured against collective for Wisdom
    function vote(uint256 proposalId, bool inFavor) external {
        Proposal storage p = proposals[proposalId];
        require(!p.resolved, "Already resolved");
        require(block.timestamp <= p.deadline, "Voting period ended");
        require(!p.hasVoted[msg.sender], "Already voted");
        require(_isParticipant(p.roomId, msg.sender), "Not participant");

        p.hasVoted[msg.sender] = true;
        p.votedFor[msg.sender] = inFavor;

        if (inFavor) {
            p.forCount++;
        } else {
            p.againstCount++;
        }

        emit Voted(proposalId, msg.sender, inFavor);

        // Auto-resolve if all participants have voted
        address[] memory participants = bubbleRoom.getRoomParticipants(p.roomId);
        if (p.forCount + p.againstCount >= participants.length) {
            _resolve(proposalId);
        }
    }

    /// @notice Resolve a proposal after deadline
    function resolve(uint256 proposalId) external {
        Proposal storage p = proposals[proposalId];
        require(!p.resolved, "Already resolved");
        require(block.timestamp > p.deadline, "Voting still active");
        _resolve(proposalId);
    }

    function _resolve(uint256 proposalId) internal {
        Proposal storage p = proposals[proposalId];
        p.resolved = true;
        p.outcome = p.forCount > p.againstCount;

        // Calculate consensus weight (0-100)
        uint256 total = p.forCount + p.againstCount;
        uint16 weight = 0;
        if (total > 0) {
            uint256 majority = p.forCount > p.againstCount ? p.forCount : p.againstCount;
            weight = uint16((majority * 100) / total);
        }

        // Feed consensus into EmergenceTraits
        traits.recordConsensus(p.roomId, weight);

        emit ProposalResolved(proposalId, p.outcome, p.forCount, p.againstCount);
    }

    /// @notice Get active proposals for a room
    function getActiveProposals(uint256 roomId) external view returns (uint256[] memory) {
        return activeProposals[roomId];
    }

    /// @notice Check if a voter voted for a specific proposal
    function getVote(uint256 proposalId, address voter) external view returns (bool voted, bool inFavor) {
        Proposal storage p = proposals[proposalId];
        return (p.hasVoted[voter], p.votedFor[voter]);
    }

    function _isParticipant(uint256 roomId, address addr) internal view returns (bool) {
        address[] memory participants = bubbleRoom.getRoomParticipants(roomId);
        for (uint256 i = 0; i < participants.length; i++) {
            if (participants[i] == addr) return true;
        }
        return false;
    }
}
