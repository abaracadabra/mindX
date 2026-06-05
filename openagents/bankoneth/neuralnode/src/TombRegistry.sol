// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./BubbleRoomV4.sol";
import "./DeltaGenesisSBT.sol";
import "./EmergenceTraits.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title TombRegistry - Programmable encrypted volumes with oracle consent
/// @notice Tombs are LUKS-style encrypted volumes stored in BubbleRooms.
///         Opening requires consent from one or more oracles (time, identity, swarm, condition).
///         Tradeability is programmable — tombs can transition based on oracle conditions.
/// @dev Inspired by dyne.org/tomb — key separation, encrypted volumes, file permissions
contract TombRegistry is Ownable {
    BubbleRoomV4 public bubbleRoom;
    DeltaGenesisSBT public genesisSBT;
    EmergenceTraits public traits;

    enum VaultState { SEALED, UNLOCKED, EXPIRED, REVOKED }
    enum ConsentType { TIME, IDENTITY, SWARM, CONDITION, PROGRAMMABLE }

    /// @notice Vault classification determines tradeability and naming
    /// TOMB: Non-tradeable, soulbound to room — permanent encrypted archive
    /// CHEST: Tradeable between rooms — portable encrypted container
    /// SAFETYDEPOSITBOX: Conditional trade — requires oracle consent to move
    /// TREASURE: Discoverable — can be found by participants meeting conditions
    /// SECRET: Hidden — existence concealed until conditions reveal it
    /// CUSTOM: User-defined classification with custom name
    enum VaultClass { TOMB, CHEST, SAFETYDEPOSITBOX, TREASURE, SECRET, CUSTOM }

    struct ConsentOracle {
        ConsentType oracleType;
        // TIME: unlockTimestamp stored in timeParam
        uint256 timeParam;
        // IDENTITY: required address or SBT holder
        address identityParam;
        // SWARM: proposal ID from SwarmGovernance
        uint256 swarmProposalId;
        // CONDITION: trait type and minimum threshold
        uint16 traitThreshold;
        uint8 traitType; // 0=intelligence, 1=knowledge, 2=resonance, 3=adaptability, 4=coherence
        // State
        bool satisfied;
    }

    struct Vault {
        uint256 roomId;           // BubbleRoom this vault lives in
        string storageCID;        // IPFS CID of encrypted volume
        string keyCID;            // IPFS CID of key file (separate location per Tomb principle)
        uint256 keyRoomId;        // Room where the key is stored (0 = off-chain)
        VaultState state;
        VaultClass vaultClass;
        string customName;        // Custom name for CUSTOM class, or override for any class
        address creator;
        uint256 created;
        uint256 lastAccessed;
        bool exists;
    }

    uint256 public nextTombId = 1;
    mapping(uint256 => Vault) public vaults;
    // Tomb ID => consent oracles (ALL must be satisfied to unlock)
    mapping(uint256 => ConsentOracle[]) public tombOracles;
    // Room ID => tomb IDs stored in that room
    mapping(uint256 => uint256[]) public roomTombs;

    event VaultCreated(uint256 indexed vaultId, uint256 indexed roomId, VaultClass vaultClass, string customName, address creator);
    event OracleAdded(uint256 indexed vaultId, ConsentType oracleType);
    event ConsentGranted(uint256 indexed vaultId, uint256 oracleIndex, ConsentType oracleType);
    event VaultUnlocked(uint256 indexed vaultId, address unlocker);
    event VaultSealed(uint256 indexed vaultId);
    event VaultRevoked(uint256 indexed vaultId, address revoker);
    event VaultClassChanged(uint256 indexed vaultId, VaultClass oldClass, VaultClass newClass);
    event VaultTransferred(uint256 indexed vaultId, uint256 indexed fromRoom, uint256 indexed toRoom);

    constructor(address bubbleRoomAddr, address sbtAddr, address traitsAddr) Ownable(msg.sender) {
        bubbleRoom = BubbleRoomV4(bubbleRoomAddr);
        genesisSBT = DeltaGenesisSBT(sbtAddr);
        traits = EmergenceTraits(traitsAddr);
    }

    /// @notice Create a new vault in a BubbleRoom
    /// @param roomId Room to store the vault in
    /// @param storageCID IPFS CID of encrypted volume
    /// @param keyCID IPFS CID of key file (stored separately per Tomb principle)
    /// @param keyRoomId Room where key is stored (0 = off-chain/self-custody)
    /// @param vaultClass Classification: TOMB (soulbound), CHEST (tradeable), SAFETYDEPOSITBOX (conditional), TREASURE (discoverable), SECRET (hidden), CUSTOM
    /// @param customName Custom name for the vault (required for CUSTOM class, optional for others)
    function createVault(
        uint256 roomId,
        string memory storageCID,
        string memory keyCID,
        uint256 keyRoomId,
        VaultClass vaultClass,
        string memory customName
    ) external returns (uint256) {
        require(_isParticipant(roomId, msg.sender), "Not participant of room");
        if (vaultClass == VaultClass.CUSTOM) {
            require(bytes(customName).length > 0, "Custom class requires a name");
        }

        uint256 vaultId = nextTombId++;
        vaults[vaultId] = Vault({
            roomId: roomId,
            storageCID: storageCID,
            keyCID: keyCID,
            keyRoomId: keyRoomId,
            state: VaultState.SEALED,
            vaultClass: vaultClass,
            customName: customName,
            creator: msg.sender,
            created: block.timestamp,
            lastAccessed: 0,
            exists: true
        });

        roomTombs[roomId].push(vaultId);

        emit VaultCreated(vaultId, roomId, vaultClass, customName, msg.sender);
        return vaultId;
    }

    // ========================
    // ORACLE MANAGEMENT
    // ========================

    /// @notice Add a time oracle — tomb unlocks after timestamp
    function addTimeOracle(uint256 tombId, uint256 unlockTimestamp) external {
        require(vaults[tombId].exists, "Vault does not exist");
        require(vaults[tombId].creator == msg.sender, "Not vault creator");

        tombOracles[tombId].push(ConsentOracle({
            oracleType: ConsentType.TIME,
            timeParam: unlockTimestamp,
            identityParam: address(0),
            swarmProposalId: 0,
            traitThreshold: 0,
            traitType: 0,
            satisfied: false
        }));

        emit OracleAdded(tombId, ConsentType.TIME);
    }

    /// @notice Add an identity oracle — requires consent from specific address or SBT holder
    function addIdentityOracle(uint256 tombId, address requiredIdentity) external {
        require(vaults[tombId].exists, "Vault does not exist");
        require(vaults[tombId].creator == msg.sender, "Not vault creator");

        tombOracles[tombId].push(ConsentOracle({
            oracleType: ConsentType.IDENTITY,
            timeParam: 0,
            identityParam: requiredIdentity,
            swarmProposalId: 0,
            traitThreshold: 0,
            traitType: 0,
            satisfied: false
        }));

        emit OracleAdded(tombId, ConsentType.IDENTITY);
    }

    /// @notice Add a swarm oracle — requires governance proposal to pass
    function addSwarmOracle(uint256 tombId, uint256 proposalId) external {
        require(vaults[tombId].exists, "Vault does not exist");
        require(vaults[tombId].creator == msg.sender, "Not vault creator");

        tombOracles[tombId].push(ConsentOracle({
            oracleType: ConsentType.SWARM,
            timeParam: 0,
            identityParam: address(0),
            swarmProposalId: proposalId,
            traitThreshold: 0,
            traitType: 0,
            satisfied: false
        }));

        emit OracleAdded(tombId, ConsentType.SWARM);
    }

    /// @notice Add a condition oracle — requires room traits to meet threshold
    /// @param traitType 0=intelligence, 1=knowledge, 2=resonance, 3=adaptability, 4=coherence
    function addConditionOracle(uint256 tombId, uint8 traitType, uint16 threshold) external {
        require(vaults[tombId].exists, "Vault does not exist");
        require(vaults[tombId].creator == msg.sender, "Not vault creator");
        require(traitType <= 4, "Invalid trait type");

        tombOracles[tombId].push(ConsentOracle({
            oracleType: ConsentType.CONDITION,
            timeParam: 0,
            identityParam: address(0),
            swarmProposalId: 0,
            traitThreshold: threshold,
            traitType: traitType,
            satisfied: false
        }));

        emit OracleAdded(tombId, ConsentType.CONDITION);
    }

    // ========================
    // CONSENT EVALUATION
    // ========================

    /// @notice Evaluate all oracles for a vault — call before attempting unlock
    function evaluateConsent(uint256 tombId) external {
        require(vaults[tombId].exists, "Vault does not exist");
        Vault storage t = vaults[tombId];
        ConsentOracle[] storage oracles = tombOracles[tombId];

        for (uint256 i = 0; i < oracles.length; i++) {
            if (oracles[i].satisfied) continue;

            if (oracles[i].oracleType == ConsentType.TIME) {
                if (block.timestamp >= oracles[i].timeParam) {
                    oracles[i].satisfied = true;
                    emit ConsentGranted(tombId, i, ConsentType.TIME);
                }
            } else if (oracles[i].oracleType == ConsentType.IDENTITY) {
                // Identity consent: caller must be the required identity or hold SBT
                if (msg.sender == oracles[i].identityParam ||
                    genesisSBT.hasClaimed(msg.sender)) {
                    oracles[i].satisfied = true;
                    emit ConsentGranted(tombId, i, ConsentType.IDENTITY);
                }
            } else if (oracles[i].oracleType == ConsentType.CONDITION) {
                // Check room's emergence traits against threshold
                EmergenceTraits.Traits memory roomTraits = traits.getTraits(t.roomId);
                uint16 traitValue = _getTraitValue(roomTraits, oracles[i].traitType);
                if (traitValue >= oracles[i].traitThreshold) {
                    oracles[i].satisfied = true;
                    emit ConsentGranted(tombId, i, ConsentType.CONDITION);
                }
            }
            // SWARM consent is evaluated externally via SwarmGovernance
        }
    }

    /// @notice Grant swarm consent — called after governance proposal resolves
    function grantSwarmConsent(uint256 tombId, uint256 oracleIndex) external {
        require(vaults[tombId].exists, "Vault does not exist");
        ConsentOracle[] storage oracles = tombOracles[tombId];
        require(oracleIndex < oracles.length, "Invalid oracle index");
        require(oracles[oracleIndex].oracleType == ConsentType.SWARM, "Not swarm oracle");

        oracles[oracleIndex].satisfied = true;
        emit ConsentGranted(tombId, oracleIndex, ConsentType.SWARM);
    }

    // ========================
    // TOMB OPERATIONS
    // ========================

    /// @notice Attempt to unlock a vault — all oracles must be satisfied
    function unlock(uint256 tombId) external {
        Vault storage t = vaults[tombId];
        require(t.exists, "Vault does not exist");
        require(t.state == VaultState.SEALED, "Vault not sealed");
        require(_isParticipant(t.roomId, msg.sender), "Not participant of room");

        // Check all oracles satisfied
        ConsentOracle[] storage oracles = tombOracles[tombId];
        for (uint256 i = 0; i < oracles.length; i++) {
            require(oracles[i].satisfied, "Oracle consent not met");
        }

        t.state = VaultState.UNLOCKED;
        t.lastAccessed = block.timestamp;

        emit VaultUnlocked(tombId, msg.sender);
    }

    /// @notice Re-seal an unlocked vault
    function seal(uint256 tombId) external {
        Vault storage t = vaults[tombId];
        require(t.exists, "Vault does not exist");
        require(t.state == VaultState.UNLOCKED, "Vault not unlocked");
        require(t.creator == msg.sender || _isParticipant(t.roomId, msg.sender), "Not authorized");

        t.state = VaultState.SEALED;
        // Reset oracle consent — must be re-evaluated next time
        ConsentOracle[] storage oracles = tombOracles[tombId];
        for (uint256 i = 0; i < oracles.length; i++) {
            oracles[i].satisfied = false;
        }

        emit VaultSealed(tombId);
    }

    /// @notice Revoke a vault — permanently inaccessible
    function revoke(uint256 tombId) external {
        Vault storage t = vaults[tombId];
        require(t.exists, "Vault does not exist");
        require(t.creator == msg.sender, "Not vault creator");

        t.state = VaultState.REVOKED;
        emit VaultRevoked(tombId, msg.sender);
    }

    // ========================
    // TRADE & TRANSFER
    // ========================

    /// @notice Transfer a vault to a different room
    /// TOMB class cannot be transferred (soulbound to room)
    /// CHEST class transfers freely
    /// SAFETYDEPOSITBOX requires all oracle consent
    /// TREASURE can be claimed by discoverer
    /// SECRET transfers only after reveal
    function transferVault(uint256 tombId, uint256 toRoomId) external {
        Vault storage t = vaults[tombId];
        require(t.exists, "Vault does not exist");
        require(t.state != VaultState.REVOKED, "Vault revoked");
        require(t.vaultClass != VaultClass.TOMB, "Tomb class is soulbound to room");
        require(_isParticipant(t.roomId, msg.sender), "Not participant of source room");
        require(_isParticipant(toRoomId, msg.sender), "Not participant of target room");

        if (t.vaultClass == VaultClass.SAFETYDEPOSITBOX) {
            ConsentOracle[] storage oracles = tombOracles[tombId];
            for (uint256 i = 0; i < oracles.length; i++) {
                require(oracles[i].satisfied, "SafetyDepositBox: oracle consent not met");
            }
        }

        if (t.vaultClass == VaultClass.SECRET) {
            // SECRET vaults can only be transferred once unlocked (revealed)
            require(t.state == VaultState.UNLOCKED, "Secret not yet revealed");
        }

        uint256 fromRoom = t.roomId;
        t.roomId = toRoomId;
        roomTombs[toRoomId].push(tombId);

        emit VaultTransferred(tombId, fromRoom, toRoomId);
    }

    /// @notice Reclassify a vault (creator only)
    function reclassify(uint256 tombId, VaultClass newClass, string memory newName) external {
        Vault storage t = vaults[tombId];
        require(t.exists, "Vault does not exist");
        require(t.creator == msg.sender, "Not vault creator");
        if (newClass == VaultClass.CUSTOM) {
            require(bytes(newName).length > 0, "Custom class requires a name");
        }

        VaultClass old = t.vaultClass;
        t.vaultClass = newClass;
        if (bytes(newName).length > 0) {
            t.customName = newName;
        }

        emit VaultClassChanged(tombId, old, newClass);
    }

    // ========================
    // VIEW FUNCTIONS
    // ========================

    /// @notice Get all tombs in a room
    function getRoomTombs(uint256 roomId) external view returns (uint256[] memory) {
        return roomTombs[roomId];
    }

    /// @notice Get oracle count for a tomb
    function getOracleCount(uint256 tombId) external view returns (uint256) {
        return tombOracles[tombId].length;
    }

    /// @notice Check if all oracles are satisfied
    function allConsentMet(uint256 tombId) external view returns (bool) {
        ConsentOracle[] storage oracles = tombOracles[tombId];
        for (uint256 i = 0; i < oracles.length; i++) {
            if (!oracles[i].satisfied) return false;
        }
        return true;
    }

    /// @notice Get a specific oracle
    function getOracle(uint256 tombId, uint256 index) external view returns (
        ConsentType oracleType, uint256 timeParam, address identityParam,
        uint256 swarmProposalId, uint16 traitThreshold, uint8 traitType, bool satisfied
    ) {
        ConsentOracle storage o = tombOracles[tombId][index];
        return (o.oracleType, o.timeParam, o.identityParam, o.swarmProposalId, o.traitThreshold, o.traitType, o.satisfied);
    }

    // ========================
    // INTERNAL
    // ========================

    function _isParticipant(uint256 roomId, address addr) internal view returns (bool) {
        address[] memory participants = bubbleRoom.getRoomParticipants(roomId);
        for (uint256 i = 0; i < participants.length; i++) {
            if (participants[i] == addr) return true;
        }
        return false;
    }

    function _getTraitValue(EmergenceTraits.Traits memory t, uint8 traitType) internal pure returns (uint16) {
        if (traitType == 0) return t.intelligence;
        if (traitType == 1) return t.knowledge;
        if (traitType == 2) return t.resonance;
        if (traitType == 3) return t.adaptability;
        if (traitType == 4) return t.coherence;
        return 0;
    }
}
