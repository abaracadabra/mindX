// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract BubbleRoomV4 is ERC721URIStorage, Ownable {
    uint256 public nextRoomId = 1;

    enum Role { NONE, MEMBER, AGENT, MODERATOR }
    enum RoomType {
        TEMPORARY, LIVING, EPHEMERAL, ARCHIVAL,
        INCUBATOR, SIGNAL, STORAGE, TIMELOCKED,
        VAULT, DELTA
    }

    struct Room {
        string theme;
        string originEvent;
        uint256 timestamp;
        uint256 unlockTime;
        string storageCID;
        bool isEncryptedStorage;
        bool isPrivate;
        bool isStable;
        bool isSoulbound;
        bool isActive;
        RoomType roomType;
        address owner;
        mapping(address => Role) participantRoles;
        address[] participants;

        // AI-Linked Metadata
        string aiSeed;
        string tone;
        bool evolves;
    }

    mapping(uint256 => Room) private rooms;

    event RoomCreated(uint256 indexed roomId, string theme, RoomType roomType, address creator);
    event ParticipantInvited(uint256 indexed roomId, address invitee, Role role);
    event RoomUnlocked(uint256 indexed roomId);

    modifier onlyRoomOwner(uint256 roomId) {
        require(ownerOf(roomId) == msg.sender, "Not room owner");
        _;
    }

    constructor() ERC721("BubbleRoom", "BROOM") Ownable(msg.sender) {}

    function mintRoom(
        string memory metadataURI,
        string memory theme,
        string memory originEvent,
        address[] memory initialParticipants,
        Role[] memory roles,
        bool isPrivate,
        bool isStable,
        bool isSoulbound,
        RoomType roomType,
        uint256 unlockTime,
        string memory storageCID,
        bool isEncryptedStorage,
        string memory aiSeed,
        string memory tone,
        bool evolves
    ) external returns (uint256) {
        require(initialParticipants.length == roles.length, "Participant/role mismatch");

        uint256 roomId = nextRoomId++;
        _safeMint(msg.sender, roomId);
        _setTokenURI(roomId, metadataURI);

        Room storage r = rooms[roomId];
        r.theme = theme;
        r.originEvent = originEvent;
        r.timestamp = block.timestamp;
        r.isPrivate = isPrivate;
        r.isStable = isStable;
        r.isSoulbound = isSoulbound;
        r.isActive = true;
        r.roomType = roomType;
        r.owner = msg.sender;
        r.unlockTime = unlockTime;
        r.storageCID = storageCID;
        r.isEncryptedStorage = isEncryptedStorage;
        r.aiSeed = aiSeed;
        r.tone = tone;
        r.evolves = evolves;

        for (uint256 i = 0; i < initialParticipants.length; i++) {
            r.participantRoles[initialParticipants[i]] = roles[i];
            r.participants.push(initialParticipants[i]);
            emit ParticipantInvited(roomId, initialParticipants[i], roles[i]);
        }

        emit RoomCreated(roomId, theme, roomType, msg.sender);
        return roomId;
    }

    function getRoomAI(uint256 roomId) external view returns (
        string memory aiSeed, string memory tone, bool evolves
    ) {
        Room storage r = rooms[roomId];
        return (r.aiSeed, r.tone, r.evolves);
    }

    function getRoomParticipants(uint256 roomId) external view returns (address[] memory) {
        return rooms[roomId].participants;
    }
}
