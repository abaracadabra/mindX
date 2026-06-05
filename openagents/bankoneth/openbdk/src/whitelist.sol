// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title  Whitelist — whitelist-as-a-service with expandable databanks
 * @author Professor Codephreak / openBDK
 * @notice A multi-room registry of admitted public keys (wallet addresses). Each
 *         "room" is an independent whitelist keyed by a uint256 roomId; a room's
 *         capacity grows by adding "databanks" — fixed-size capacity grants that
 *         only an authorized GATE, REGISTRY, or HOLDING contract may add.
 *
 * @dev    Gas / storage design ("least gas to hold or access; max addresses per
 *         memory unit"):
 *
 *         - Membership is `mapping(roomId => mapping(address => bool))`. For
 *           ARBITRARY public keys this is the cheapest possible store: admit =
 *           one SSTORE, check = one SLOAD. (A bitmap packs 256 flags per slot but
 *           only helps for sequentially-indexed identities, not arbitrary
 *           addresses — so it is intentionally NOT used here.)
 *
 *         - Per-room metadata is packed into ONE 256-bit slot via the smallest
 *           uints that comfortably bound the domain:
 *             uint64  capacity  — max members (a databank grants DATABANK_CAPACITY;
 *                                 uint64 holds 1.8e19 — unreachable, so it never
 *                                 overflows yet packs 4 fields per slot)
 *             uint64  count     — current members
 *             uint64  databanks — number of databanks added
 *             bool    exists, open
 *           => create/admit touch a single warm slot for the counters.
 *
 *         The OWNER (DEFAULT_ADMIN_ROLE) holds control; this contract custodies no
 *         keys — it stores only the public addresses presented to it.
 */
contract Whitelist is AccessControl {
    // ── roles: the three authorities that may expand a room with a databank ──
    bytes32 public constant GATE_ROLE = keccak256("GATE_ROLE");
    bytes32 public constant REGISTRY_ROLE = keccak256("REGISTRY_ROLE");
    bytes32 public constant HOLDING_ROLE = keccak256("HOLDING_ROLE");
    /// @notice May create rooms and admit/remove members.
    bytes32 public constant CURATOR_ROLE = keccak256("CURATOR_ROLE");

    /// @notice Addresses a single databank adds to a room's capacity.
    uint64 public constant DATABANK_CAPACITY = 65_536;

    /// @dev One slot per room (packed): exists|open|count|capacity|databanks.
    struct Room {
        bool exists;
        bool open; // if true, anyone may self-admit (still capacity-bound)
        uint64 capacity;
        uint64 count;
        uint64 databanks;
    }

    mapping(uint256 => Room) private _rooms;
    // roomId => member => admitted
    mapping(uint256 => mapping(address => bool)) private _member;

    // ── events ──
    event RoomCreated(uint256 indexed roomId, uint64 initialCapacity, bool open);
    event RoomOpenSet(uint256 indexed roomId, bool open);
    event DatabankAdded(uint256 indexed roomId, address indexed authority, uint64 newCapacity, uint64 databanks);
    event Admitted(uint256 indexed roomId, address indexed member);
    event Revoked(uint256 indexed roomId, address indexed member);

    // ── errors ──
    error RoomExists();
    error NoSuchRoom();
    error RoomFull();
    error AlreadyMember();
    error NotMember();
    error NotOpen();
    error NotAuthority();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CURATOR_ROLE, admin);
    }

    // ── room lifecycle ──

    /// @notice Create a room. `initialDatabanks` seeds capacity (admin/curator only).
    function createRoom(uint256 roomId, uint64 initialDatabanks, bool open)
        external onlyRole(CURATOR_ROLE)
    {
        if (_rooms[roomId].exists) revert RoomExists();
        uint64 cap = initialDatabanks * DATABANK_CAPACITY;
        _rooms[roomId] = Room({exists: true, open: open, capacity: cap, count: 0, databanks: initialDatabanks});
        emit RoomCreated(roomId, cap, open);
    }

    function setRoomOpen(uint256 roomId, bool open) external onlyRole(CURATOR_ROLE) {
        if (!_rooms[roomId].exists) revert NoSuchRoom();
        _rooms[roomId].open = open;
        emit RoomOpenSet(roomId, open);
    }

    /**
     * @notice Add a databank to a room, expanding its capacity by DATABANK_CAPACITY.
     * @dev Only an authorized GATE, REGISTRY, or HOLDING may expand a whitelist —
     *      this is the "expand if allowed from gate/registry/holding" rule.
     */
    function addDatabank(uint256 roomId) external {
        if (!(hasRole(GATE_ROLE, msg.sender)
              || hasRole(REGISTRY_ROLE, msg.sender)
              || hasRole(HOLDING_ROLE, msg.sender))) revert NotAuthority();
        Room storage r = _rooms[roomId];
        if (!r.exists) revert NoSuchRoom();
        r.databanks += 1;
        r.capacity += DATABANK_CAPACITY;
        emit DatabankAdded(roomId, msg.sender, r.capacity, r.databanks);
    }

    // ── membership ──

    function admit(uint256 roomId, address member) external onlyRole(CURATOR_ROLE) {
        _admit(roomId, member);
    }

    /// @notice Batch admit — amortizes the warm-slot counter write across many members.
    function admitMany(uint256 roomId, address[] calldata members) external onlyRole(CURATOR_ROLE) {
        Room storage r = _rooms[roomId];
        if (!r.exists) revert NoSuchRoom();
        uint64 added;
        for (uint256 i; i < members.length; ++i) {
            address m = members[i];
            if (!_member[roomId][m]) {
                _member[roomId][m] = true;
                emit Admitted(roomId, m);
                unchecked { ++added; }
            }
        }
        if (r.count + added > r.capacity) revert RoomFull();
        r.count += added;
    }

    /// @notice Self-admit into an open room (capacity-bound).
    function join(uint256 roomId) external {
        Room storage r = _rooms[roomId];
        if (!r.exists) revert NoSuchRoom();
        if (!r.open) revert NotOpen();
        _admit(roomId, msg.sender);
    }

    function revoke(uint256 roomId, address member) external onlyRole(CURATOR_ROLE) {
        Room storage r = _rooms[roomId];
        if (!r.exists) revert NoSuchRoom();
        if (!_member[roomId][member]) revert NotMember();
        _member[roomId][member] = false;
        r.count -= 1;
        emit Revoked(roomId, member);
    }

    function _admit(uint256 roomId, address member) internal {
        Room storage r = _rooms[roomId];
        if (!r.exists) revert NoSuchRoom();
        if (_member[roomId][member]) revert AlreadyMember();
        if (r.count + 1 > r.capacity) revert RoomFull();
        _member[roomId][member] = true;
        r.count += 1;
        emit Admitted(roomId, member);
    }

    // ── views ──

    function isWhitelisted(uint256 roomId, address member) external view returns (bool) {
        return _member[roomId][member];
    }

    function room(uint256 roomId)
        external view
        returns (bool exists, bool open, uint64 capacity, uint64 count, uint64 databanks)
    {
        Room storage r = _rooms[roomId];
        return (r.exists, r.open, r.capacity, r.count, r.databanks);
    }

    function remaining(uint256 roomId) external view returns (uint64) {
        Room storage r = _rooms[roomId];
        return r.capacity > r.count ? r.capacity - r.count : 0;
    }
}
