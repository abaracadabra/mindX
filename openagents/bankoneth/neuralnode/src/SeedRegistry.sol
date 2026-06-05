// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

/// @title SeedRegistry - On-chain registry for Agent Seeds
/// @notice Stores the generative DNA of every agent and room in DeltaVerse
/// @dev Seeds propagate through Spawn, mutate through Interaction, evolve through Consensus
contract SeedRegistry is Ownable {

    struct Seed {
        string prompt;        // generative DNA text
        string tone;          // emotional signature
        bool evolves;         // can this seed mutate autonomously
        uint256 originSeedId; // 0 = genesis (no origin)
        uint256 spawnCount;   // how many emergences from this seed
        uint256 timestamp;
        address creator;
        bool exists;
    }

    uint256 public nextSeedId = 1;
    mapping(uint256 => Seed) public seeds;
    // Room ID => Seed ID
    mapping(uint256 => uint256) public roomSeed;
    // Seed ID => child seed IDs (Lineage tree)
    mapping(uint256 => uint256[]) public seedLineage;

    event SeedCreated(uint256 indexed seedId, string prompt, string tone, address creator);
    event SeedSpawned(uint256 indexed originSeedId, uint256 indexed emergenceSeedId, string mutation);
    event SeedBound(uint256 indexed roomId, uint256 indexed seedId);
    event SeedMutated(uint256 indexed seedId, string newPrompt, string reason);

    constructor() Ownable(msg.sender) {}

    /// @notice Register a genesis seed (no origin)
    function createGenesisSeed(
        string memory prompt,
        string memory tone,
        bool evolves
    ) external returns (uint256) {
        uint256 seedId = nextSeedId++;
        seeds[seedId] = Seed({
            prompt: prompt,
            tone: tone,
            evolves: evolves,
            originSeedId: 0,
            spawnCount: 0,
            timestamp: block.timestamp,
            creator: msg.sender,
            exists: true
        });

        emit SeedCreated(seedId, prompt, tone, msg.sender);
        return seedId;
    }

    /// @notice Spawn a new seed from an origin, applying a mutation
    /// @param originSeedId The seed to spawn from
    /// @param mutation The semantic shift to apply
    /// @param tone Override tone (empty string inherits from origin)
    function spawnSeed(
        uint256 originSeedId,
        string memory mutation,
        string memory tone
    ) external returns (uint256) {
        Seed storage origin = seeds[originSeedId];
        require(origin.exists, "Origin seed does not exist");

        // Compose emergence prompt: origin >> mutation
        string memory emergencePrompt = string(abi.encodePacked(origin.prompt, " >> ", mutation));
        string memory emergenceTone = bytes(tone).length > 0 ? tone : origin.tone;

        uint256 seedId = nextSeedId++;
        seeds[seedId] = Seed({
            prompt: emergencePrompt,
            tone: emergenceTone,
            evolves: origin.evolves,
            originSeedId: originSeedId,
            spawnCount: 0,
            timestamp: block.timestamp,
            creator: msg.sender,
            exists: true
        });

        // Update origin's spawn count and lineage
        origin.spawnCount++;
        seedLineage[originSeedId].push(seedId);

        emit SeedSpawned(originSeedId, seedId, mutation);
        return seedId;
    }

    /// @notice Bind a seed to a BubbleRoom
    function bindSeedToRoom(uint256 roomId, uint256 seedId) external {
        require(seeds[seedId].exists, "Seed does not exist");
        roomSeed[roomId] = seedId;
        emit SeedBound(roomId, seedId);
    }

    /// @notice Mutate a seed's prompt (only if evolves == true)
    /// @dev Called by agents or governance to evolve a living seed
    function mutateSeed(uint256 seedId, string memory newPrompt, string memory reason) external {
        Seed storage s = seeds[seedId];
        require(s.exists, "Seed does not exist");
        require(s.evolves, "Seed is not mutable");
        require(s.creator == msg.sender || owner() == msg.sender, "Not authorized");

        s.prompt = newPrompt;
        emit SeedMutated(seedId, newPrompt, reason);
    }

    /// @notice Get the Lineage depth of a seed
    function getLineageDepth(uint256 seedId) external view returns (uint256 depth) {
        uint256 current = seedId;
        while (true) {
            uint256 origin = seeds[current].originSeedId;
            if (origin == 0) break;
            depth++;
            current = origin;
            if (depth > 100) break;
        }
    }

    /// @notice Get all emergences from a seed
    function getLineage(uint256 seedId) external view returns (uint256[] memory) {
        return seedLineage[seedId];
    }

    /// @notice Get the full Lineage chain (ancestors) of a seed
    function getAncestors(uint256 seedId) external view returns (uint256[] memory) {
        // First count depth
        uint256 depth;
        uint256 current = seedId;
        while (true) {
            uint256 origin = seeds[current].originSeedId;
            if (origin == 0) break;
            depth++;
            current = origin;
            if (depth > 100) break;
        }

        // Build ancestor array
        uint256[] memory ancestors = new uint256[](depth);
        current = seedId;
        for (uint256 i = 0; i < depth; i++) {
            current = seeds[current].originSeedId;
            ancestors[i] = current;
        }
        return ancestors;
    }
}
