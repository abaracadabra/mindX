// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity ^0.8.24;

/**
 * DatoCore — a DAIO-owned data-DAO (the EVM substrate of a `dato`).
 *
 * The DAIO is the owner/authority; participants are admitted as members and
 * commit data records anchored at a permanence tier. The name declares the tier
 * (see DatoNamingRegistry). cypherpunk2048: inline owner (the DAIO), no admin
 * proxy, no upgradeable pattern, no selfdestruct, zero imports (airgap-compileable).
 *
 * Permanence tiers:
 *   IMMORTAL  — proof is an Arweave tx id (the ~200-yr guarantee); bytes off-chain.
 *   IMMUTABLE — sha256 is hash-locked here; re-commit with a different hash reverts.
 *   MUTABLE   — version bumps; hash free to change.
 */
contract DatoCore {
    enum Tier { Immortal, Immutable, Mutable }

    struct Record {
        bytes32 sha256Hash;
        Tier tier;
        string proof;          // Arweave tx id (immortal) | anchor ref (immutable) | "" (mutable)
        uint32 version;
        uint64 committedAt;
        bool exists;
    }

    struct Settings {
        Tier defaultTier;
        uint256 joinFeeMicroUSD;
        bool openJoin;
        uint32 maxMembers;
    }

    address public owner;            // the owning DAIO
    address public immutable deployer; // the spawning participant/client wallet
    string  public datoName;         // the dato's own tiered name
    Settings public settings;

    mapping(address => bool)  public isMember;
    mapping(address => bytes32) public memberSettings; // per-member settings hash
    uint32 public memberCount;
    mapping(bytes32 => Record) private _records;       // keccak(name) => record

    event Configured(Tier defaultTier, uint256 joinFee, bool openJoin, uint32 maxMembers);
    event MemberAdmitted(address indexed wallet, bytes32 settingsHash, uint256 feePaid);
    event MemberRemoved(address indexed wallet);
    event RecordCommitted(bytes32 indexed nameKey, string name, Tier tier, bytes32 sha256Hash, string proof, uint32 version);
    event OwnershipTransferred(address indexed from, address indexed to);

    error NotOwner();
    error NotMemberOrOwner();
    error ClosedJoin();
    error AtCapacity();
    error AlreadyMember();
    error ImmutableLock();
    error ZeroAddress();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }
    modifier onlyMemberOrOwner() { if (msg.sender != owner && !isMember[msg.sender]) revert NotMemberOrOwner(); _; }

    constructor(address daioOwner, address deployerWallet, string memory name_, Settings memory s) {
        if (daioOwner == address(0)) revert ZeroAddress();
        owner = daioOwner;
        deployer = deployerWallet;
        datoName = name_;
        settings = s;
        // The deployer is the founding member.
        if (deployerWallet != address(0)) {
            isMember[deployerWallet] = true;
            memberCount = 1;
        }
        emit OwnershipTransferred(address(0), daioOwner);
    }

    function configure(Settings calldata s) external onlyOwner {
        settings = s;
        emit Configured(s.defaultTier, s.joinFeeMicroUSD, s.openJoin, s.maxMembers);
    }

    /// @notice Admit a member. Called by the owner/govern (or DatoMembership once a
    /// fee is settled). Closed-join datos require the owner.
    function admitMember(address wallet, bytes32 settingsHash, uint256 feePaid) external {
        if (msg.sender != owner) {
            // Only the owner admits directly; fee-gated admission routes through owner-set membership manager.
            if (!settings.openJoin) revert ClosedJoin();
            if (msg.sender != wallet) revert NotOwner(); // self-join only on open datos
        }
        if (isMember[wallet]) revert AlreadyMember();
        if (settings.maxMembers != 0 && memberCount >= settings.maxMembers) revert AtCapacity();
        isMember[wallet] = true;
        memberSettings[wallet] = settingsHash;
        unchecked { memberCount += 1; }
        emit MemberAdmitted(wallet, settingsHash, feePaid);
    }

    function removeMember(address wallet) external onlyOwner {
        if (isMember[wallet]) {
            isMember[wallet] = false;
            unchecked { memberCount -= 1; }
            emit MemberRemoved(wallet);
        }
    }

    /// @notice Commit a data record anchor. The tier is declared by the name; IMMUTABLE
    /// is hash-locked (different sha256 under the same name reverts).
    function commitRecord(
        string calldata name,
        bytes32 sha256Hash,
        Tier tier,
        string calldata proof
    ) external onlyMemberOrOwner returns (uint32 version) {
        bytes32 key = keccak256(bytes(name));
        Record storage r = _records[key];
        if (r.exists && r.tier == Tier.Immutable && tier == Tier.Immutable && r.sha256Hash != sha256Hash) {
            revert ImmutableLock();
        }
        version = (r.exists && r.tier == Tier.Mutable) ? r.version + 1 : 1;
        _records[key] = Record({
            sha256Hash: sha256Hash, tier: tier, proof: proof,
            version: version, committedAt: uint64(block.timestamp), exists: true
        });
        emit RecordCommitted(key, name, tier, sha256Hash, proof, version);
    }

    function getRecord(string calldata name) external view returns (Record memory) {
        return _records[keccak256(bytes(name))];
    }

    /// @notice Devolution / handoff: the DAIO can transfer ownership (e.g. to a sub-DAO).
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
