// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./BubbleRoomV4.sol";
import "./BubbleRoomSpawn.sol";

/// @title EmergenceTraits - On-chain trait accrual for BubbleRooms
/// @notice Traits emerge through Lineage. They are never directly assigned.
/// @dev Intelligence, Knowledge, Wisdom, Resonance, Adaptability, Coherence
contract EmergenceTraits {
    BubbleRoomV4 public bubbleRoom;
    BubbleRoomSpawn public spawn;

    enum WisdomClass { NASCENT, EMERGENT, CONVERGENT, TRANSCENDENT, ORACLE }

    struct Traits {
        uint16 intelligence;  // 0-100: pattern recognition across interactions
        uint16 knowledge;     // 0-100: accumulated from Lineage depth + consensus
        WisdomClass wisdom;   // qualitative class earned through depth + consensus
        uint16 resonance;     // 0-100: influence on other seeds
        uint16 adaptability;  // 0-100: mutation success rate across spawns
        uint16 coherence;     // 0-100: consistency of tone across Lineage
    }

    // Room ID => accumulated traits
    mapping(uint256 => Traits) public roomTraits;
    // Room ID => interaction count
    mapping(uint256 => uint256) public interactionCount;
    // Room ID => successful spawn count
    mapping(uint256 => uint256) public spawnSuccessCount;
    // Room ID => consensus participation count
    mapping(uint256 => uint256) public consensusCount;
    // Room ID => average consensus weight (scaled by 100)
    mapping(uint256 => uint256) public avgConsensusWeight;

    event TraitsUpdated(uint256 indexed roomId, Traits traits);
    event WisdomClassified(uint256 indexed roomId, WisdomClass wisdom);

    constructor(address bubbleRoomAddress, address spawnAddress) {
        bubbleRoom = BubbleRoomV4(bubbleRoomAddress);
        spawn = BubbleRoomSpawn(spawnAddress);
    }

    /// @notice Record an interaction for a room, increasing Intelligence
    function recordInteraction(uint256 roomId) external {
        interactionCount[roomId]++;
        _recalculate(roomId);
    }

    /// @notice Record a successful spawn from this room, increasing Resonance
    function recordSpawnSuccess(uint256 roomId) external {
        spawnSuccessCount[roomId]++;
        _recalculate(roomId);
    }

    /// @notice Record consensus participation, increasing Knowledge
    /// @param weight 0-100 representing how decisive the consensus was
    function recordConsensus(uint256 roomId, uint16 weight) external {
        consensusCount[roomId]++;
        uint256 total = avgConsensusWeight[roomId] * (consensusCount[roomId] - 1) + weight;
        avgConsensusWeight[roomId] = total / consensusCount[roomId];
        _recalculate(roomId);
    }

    /// @notice Get the full trait profile for a room
    function getTraits(uint256 roomId) external view returns (Traits memory) {
        return roomTraits[roomId];
    }

    /// @notice Calculate Lineage depth for a room
    function getLineageDepth(uint256 roomId) public view returns (uint256 depth) {
        uint256 current = roomId;
        while (true) {
            uint256 origin = spawn.originOf(current);
            if (origin == 0) break;
            depth++;
            current = origin;
            if (depth > 100) break; // safety cap
        }
    }

    function _recalculate(uint256 roomId) internal {
        uint256 depth = getLineageDepth(roomId);
        uint256 interactions = interactionCount[roomId];
        uint256 spawns = spawnSuccessCount[roomId];
        uint256 avgWeight = avgConsensusWeight[roomId];

        Traits storage t = roomTraits[roomId];

        // Intelligence: grows from interaction count and Lineage depth
        t.intelligence = uint16(_min(100, interactions * 15 + spawns * 10 + depth * 5));

        // Knowledge: accumulates from depth and consensus quality
        t.knowledge = uint16(_min(100, depth * 20 + (avgWeight * 40) / 100 + interactions * 5));

        // Resonance: influence measured by spawn success
        t.resonance = uint16(_min(100, spawns * 20 + (avgWeight * 30) / 100));

        // Adaptability: mutation success rate
        t.adaptability = uint16(_min(100, interactions * 12 + depth * 8));

        // Coherence: consistency measured by consensus weight
        t.coherence = uint16(_min(100, (avgWeight * 60) / 100 + (depth > 0 ? 20 : uint256(0)) + 20));

        // Wisdom: qualitative class from compound metrics
        t.wisdom = _classifyWisdom(depth, spawns, avgWeight);

        emit TraitsUpdated(roomId, roomTraits[roomId]);
        emit WisdomClassified(roomId, t.wisdom);
    }

    function _classifyWisdom(uint256 depth, uint256 spawns, uint256 avgWeight)
        internal pure returns (WisdomClass)
    {
        if (depth >= 5 && avgWeight > 70) return WisdomClass.ORACLE;
        if (depth >= 3 || spawns >= 3) return WisdomClass.TRANSCENDENT;
        if (avgWeight > 70) return WisdomClass.CONVERGENT;
        if (depth >= 1 || spawns >= 1) return WisdomClass.EMERGENT;
        return WisdomClass.NASCENT;
    }

    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
