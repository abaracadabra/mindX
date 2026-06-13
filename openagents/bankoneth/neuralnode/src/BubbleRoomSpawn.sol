// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./BubbleRoomV4.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

/// @title BubbleRoomSpawn - Inter-room interaction and spawn protocol
/// @notice Enables BubbleRooms to spawn emergences and interact across room boundaries
/// @dev DeltaVerse naming: Origin (source room) -> Emergence (spawned room), Lineage (the chain)
contract BubbleRoomSpawn is IERC721Receiver {
    BubbleRoomV4 public bubbleRoom;

    struct SpawnLink {
        uint256 originRoomId;
        uint256 emergenceRoomId;
        string seedMutation;
        uint256 timestamp;
        address spawner;
    }

    struct SwarmConsensus {
        uint256 roomId;
        uint256 forCount;
        uint256 againstCount;
        mapping(address => bool) hasVoted;
        bool resolved;
        string proposal;
    }

    // Origin room => emergence room IDs (the Lineage Tree)
    mapping(uint256 => uint256[]) public lineageTree;
    // Emergence room => its origin room
    mapping(uint256 => uint256) public originOf;
    // Room pair hash => interaction log CIDs
    mapping(bytes32 => string[]) public interactionLogs;
    // Spawn links by emergence room ID
    mapping(uint256 => SpawnLink) public spawnLinks;
    // Consensus proposals
    uint256 public nextProposalId = 1;
    mapping(uint256 => SwarmConsensus) public proposals;

    event RoomSpawned(uint256 indexed originId, uint256 indexed emergenceId, string seedMutation, address spawner);
    event RoomsLinked(uint256 indexed roomA, uint256 indexed roomB, string interactionCID);
    event SwarmVote(uint256 indexed proposalId, uint256 indexed roomId, address voter, bool inFavor);
    event ConsensusReached(uint256 indexed proposalId, uint256 indexed roomId, bool outcome);

    constructor(address bubbleRoomAddress) {
        bubbleRoom = BubbleRoomV4(bubbleRoomAddress);
    }

    /// @notice Spawn an emergence BubbleRoom from an origin room
    /// @dev The emergence inherits and mutates the origin's AI seed
    function spawnFromRoom(
        uint256 originRoomId,
        string memory metadataURI,
        string memory theme,
        string memory originEvent,
        address[] memory participants,
        BubbleRoomV4.Role[] memory roles,
        bool isPrivate,
        uint8 roomType,
        string memory seedMutation,
        string memory tone,
        bool evolves
    ) external returns (uint256) {
        // Verify spawner is participant of origin room
        require(_isParticipant(originRoomId, msg.sender), "Not participant of origin room");

        // Get origin AI seed and compose emergence seed
        (string memory originSeed, , ) = bubbleRoom.getRoomAI(originRoomId);
        string memory emergenceSeed = string(abi.encodePacked(originSeed, " >> ", seedMutation));

        // Mint emergence room via BubbleRoomV4
        uint256 emergenceId = bubbleRoom.mintRoom(
            metadataURI,
            theme,
            originEvent,
            participants,
            roles,
            isPrivate,
            false, // isStable
            false, // isSoulbound
            BubbleRoomV4.RoomType(roomType),
            0,     // unlockTime
            "",    // storageCID
            false, // isEncryptedStorage
            emergenceSeed,
            tone,
            evolves
        );

        // Transfer minted room from this contract to the spawner
        bubbleRoom.transferFrom(address(this), msg.sender, emergenceId);

        // Record spawn lineage
        lineageTree[originRoomId].push(emergenceId);
        originOf[emergenceId] = originRoomId;
        spawnLinks[emergenceId] = SpawnLink({
            originRoomId: originRoomId,
            emergenceRoomId: emergenceId,
            seedMutation: seedMutation,
            timestamp: block.timestamp,
            spawner: msg.sender
        });

        emit RoomSpawned(originRoomId, emergenceId, seedMutation, msg.sender);
        return emergenceId;
    }

    /// @notice Record an interaction between two BubbleRooms
    /// @dev Creates a bidirectional link with IPFS-stored interaction data
    function recordInteraction(
        uint256 roomA,
        uint256 roomB,
        string memory interactionCID
    ) external {
        require(_isParticipant(roomA, msg.sender), "Not participant of room A");
        require(_isParticipant(roomB, msg.sender), "Not participant of room B");

        bytes32 pairHash = _pairHash(roomA, roomB);
        interactionLogs[pairHash].push(interactionCID);

        emit RoomsLinked(roomA, roomB, interactionCID);
    }

    /// @notice Create a swarm consensus proposal within a room
    function proposeToSwarm(uint256 roomId, string memory proposal) external returns (uint256) {
        require(_isParticipant(roomId, msg.sender), "Not participant");

        uint256 proposalId = nextProposalId++;
        SwarmConsensus storage s = proposals[proposalId];
        s.roomId = roomId;
        s.proposal = proposal;

        return proposalId;
    }

    /// @notice Vote on a swarm consensus proposal
    /// @dev Individual spawn opinion measured against collective for wisdom accrual
    function voteOnProposal(uint256 proposalId, bool inFavor) external {
        SwarmConsensus storage s = proposals[proposalId];
        require(!s.resolved, "Already resolved");
        require(!s.hasVoted[msg.sender], "Already voted");
        require(_isParticipant(s.roomId, msg.sender), "Not participant");

        s.hasVoted[msg.sender] = true;
        if (inFavor) {
            s.forCount++;
        } else {
            s.againstCount++;
        }

        emit SwarmVote(proposalId, s.roomId, msg.sender, inFavor);

        // Auto-resolve when all participants have voted
        address[] memory participants = bubbleRoom.getRoomParticipants(s.roomId);
        if (s.forCount + s.againstCount >= participants.length) {
            s.resolved = true;
            emit ConsensusReached(proposalId, s.roomId, s.forCount > s.againstCount);
        }
    }

    /// @notice Get all emergences spawned from a room (the lineage tree)
    function getLineageTree(uint256 roomId) external view returns (uint256[] memory) {
        return lineageTree[roomId];
    }

    /// @notice Get interaction history between two rooms
    function getInteractionHistory(uint256 roomA, uint256 roomB) external view returns (string[] memory) {
        return interactionLogs[_pairHash(roomA, roomB)];
    }

    function _isParticipant(uint256 roomId, address addr) internal view returns (bool) {
        address[] memory participants = bubbleRoom.getRoomParticipants(roomId);
        for (uint256 i = 0; i < participants.length; i++) {
            if (participants[i] == addr) return true;
        }
        return false;
    }

    function _pairHash(uint256 a, uint256 b) internal pure returns (bytes32) {
        return a < b
            ? keccak256(abi.encodePacked(a, b))
            : keccak256(abi.encodePacked(b, a));
    }

    /// @notice ERC721Receiver implementation so this contract can receive minted rooms
    function onERC721Received(address, address, uint256, bytes calldata) external pure override returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }
}
