// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// src/interfaces/ICensura.sol

/// @title ICensura
/// @notice Subset of the BONAFIDE Censura reputation interface.
///         Scores are uint8 (0-255) and decay/grow per Censura's rules.
interface ICensura {
    /// @return score current reputation score for `subject`.
    function score(address subject) external view returns (uint8 score);

    /// @notice Report a member for protocol abuse. Slashes some reputation.
    /// @dev Implementation-defined; Conclave only needs the function selector.
    function report(address subject, bytes32 reason) external;
}

// src/interfaces/IConclave.sol

/// @title IConclave
/// @notice Public surface of the Conclave registration / anchoring contract.
interface IConclave {
    // ---------- events ---------- //

    event ConclaveRegistered(
        bytes32 indexed conclave_id,
        address indexed convener,
        uint8 member_count,
        uint8 censura_min,
        uint256 bond_per_member
    );

    event ResolutionAnchored(
        bytes32 indexed conclave_id,
        bytes32 indexed session_id,
        bytes32 indexed motion_id,
        bytes32 resolution_hash,
        bool outcome_passed,
        uint8 voter_count
    );

    event MemberSlashed(
        bytes32 indexed conclave_id,
        bytes32 indexed session_id,
        address indexed leaker,
        uint256 amount
    );

    event MemberUnseated(
        bytes32 indexed conclave_id,
        address indexed member,
        uint8 reason // 0=tessera, 1=censura, 2=bond, 3=slashed
    );

    // ---------- registration ---------- //

    function registerConclave(
        bytes32 conclave_id,
        address[] calldata members,
        bytes32[] calldata pubkeys,
        uint8[] calldata roles,
        uint8 censura_min,
        uint256 bond_per_member
    ) external;

    function isMemberSeated(bytes32 conclave_id, address member)
        external
        view
        returns (bool);

    // ---------- anchoring ---------- //

    function recordResolution(
        bytes32 conclave_id,
        bytes32 session_id,
        bytes32 motion_id,
        bytes32 resolution_hash,
        address[] calldata voters,
        bool outcome_passed
    ) external;

    // ---------- slashing ---------- //

    function slashForLeak(
        bytes32 conclave_id,
        bytes32 session_id,
        address leaker,
        bytes calldata leak_proof
    ) external;
}

// src/interfaces/IConclaveBond.sol

/// @title IConclaveBond
/// @notice Honor-stake module. Members lock a bond before being seated;
///         leaks are slashed by `Conclave.sol`.
interface IConclaveBond {
    /// @return amount the bond `member` has locked for `conclave_id`.
    function bondOf(bytes32 conclave_id, address member)
        external
        view
        returns (uint256 amount);

    /// @notice Lock a bond for a conclave. Pulls funds from msg.sender.
    function postBond(bytes32 conclave_id, uint256 amount) external payable;

    /// @notice Release a bond after the conclave's slash window expires.
    function releaseBond(bytes32 conclave_id) external;

    /// @notice Slash a member's bond. Only callable by the Conclave contract.
    /// @return amount the amount slashed (full bond at v0.1).
    function slash(bytes32 conclave_id, address member)
        external
        returns (uint256 amount);
}

// src/interfaces/ITessera.sol

/// @title ITessera
/// @notice Subset of the BONAFIDE Tessera interface that Conclave depends on.
///         Tessera is the soulbound W3C-DID credential anchor in BONAFIDE.
///         A holder is "seated" if they have an active, unrevoked credential.
interface ITessera {
    /// @return seated true iff `holder` has a valid, unrevoked credential.
    function hasValidCredential(address holder) external view returns (bool seated);

    /// @return did the holder's W3C DID, e.g. "did:bankon:0xabc...".
    function didOf(address holder) external view returns (string memory did);

    /// @return pubkey the Ed25519 transport pubkey bound to this credential
    ///         (32 bytes, used as the AXL peer id).
    function transportKeyOf(address holder) external view returns (bytes32 pubkey);
}

// src/Conclave.sol

/// @title Conclave
/// @author Professor Codephreak / PYTHAI
/// @notice On-chain gating, anchoring, and slashing for CONCLAVE sessions.
///
/// A Conclave is registered with a fixed member set bound by Ed25519
/// transport pubkeys (matching the AXL peer id) and EVM addresses
/// (matching their BONAFIDE Tessera credentials). Membership is enforced
/// at three layers:
///
///   1. Tessera   — must hold a valid soulbound credential.
///   2. Censura   — must score >= `censura_min` reputation.
///   3. Conclave  — must have posted `bond_per_member` to ConclaveBond.
///
/// A member is "seated" when all three hold. Seated state is checked at
/// `recordResolution` time and reflected in `isMemberSeated`.
///
/// Resolutions are anchored by the convener after the off-chain protocol
/// reaches quorum. The contract verifies that every named voter is still
/// seated; otherwise the entire anchor reverts.
contract Conclave is IConclave {
    // ---------- types ---------- //

    struct Member {
        address addr;
        bytes32 pubkey;     // Ed25519 transport pubkey (32 bytes)
        uint8 role;
        bool slashed;
    }

    struct ConclaveData {
        address convener;
        uint8 censura_min;
        uint256 bond_per_member;
        uint8 member_count;
        // member address => index+1 (0 == not a member)
        mapping(address => uint8) memberIndex;
        mapping(uint8 => Member) members;
        // session_id => motion_id => resolution_hash
        mapping(bytes32 => mapping(bytes32 => bytes32)) resolutions;
    }

    // ---------- storage ---------- //

    ITessera public immutable tessera;
    ICensura public immutable censura;
    IConclaveBond public immutable bond;

    mapping(bytes32 => ConclaveData) private _conclaves;

    // ---------- errors ---------- //

    error ConclaveExists();
    error UnknownConclave();
    error NotConvener();
    error MemberNotSeated(address member);
    error LengthMismatch();
    error EmptyMemberSet();
    error TooManyMembers();
    error AlreadyAnchored();
    error NotAMember(address member);

    // ---------- ctor ---------- //

    constructor(address tessera_, address censura_, address bond_) {
        tessera = ITessera(tessera_);
        censura = ICensura(censura_);
        bond = IConclaveBond(bond_);
    }

    // ---------- registration ---------- //

    /// @inheritdoc IConclave
    function registerConclave(
        bytes32 conclave_id,
        address[] calldata members_,
        bytes32[] calldata pubkeys,
        uint8[] calldata roles,
        uint8 censura_min,
        uint256 bond_per_member
    ) external {
        ConclaveData storage c = _conclaves[conclave_id];
        if (c.convener != address(0)) revert ConclaveExists();
        uint256 n = members_.length;
        if (n == 0) revert EmptyMemberSet();
        if (n > 255) revert TooManyMembers();
        if (pubkeys.length != n || roles.length != n) revert LengthMismatch();

        c.convener = msg.sender;
        c.censura_min = censura_min;
        c.bond_per_member = bond_per_member;
        c.member_count = uint8(n);

        for (uint256 i = 0; i < n; ++i) {
            address a = members_[i];
            if (a == address(0)) revert NotAMember(a);
            // index+1 so that 0 means "not a member"
            c.memberIndex[a] = uint8(i + 1);
            c.members[uint8(i)] = Member({
                addr: a,
                pubkey: pubkeys[i],
                role: roles[i],
                slashed: false
            });
        }

        emit ConclaveRegistered(
            conclave_id, msg.sender, uint8(n), censura_min, bond_per_member
        );
    }

    /// @inheritdoc IConclave
    function isMemberSeated(bytes32 conclave_id, address member)
        public
        view
        returns (bool)
    {
        ConclaveData storage c = _conclaves[conclave_id];
        uint8 idx1 = c.memberIndex[member];
        if (idx1 == 0) return false;
        if (c.members[idx1 - 1].slashed) return false;
        if (!tessera.hasValidCredential(member)) return false;
        if (censura.score(member) < c.censura_min) return false;
        if (bond.bondOf(conclave_id, member) < c.bond_per_member) return false;
        return true;
    }

    // ---------- anchoring ---------- //

    /// @inheritdoc IConclave
    function recordResolution(
        bytes32 conclave_id,
        bytes32 session_id,
        bytes32 motion_id,
        bytes32 resolution_hash,
        address[] calldata voters,
        bool outcome_passed
    ) external {
        ConclaveData storage c = _conclaves[conclave_id];
        if (c.convener == address(0)) revert UnknownConclave();
        if (msg.sender != c.convener) revert NotConvener();
        if (c.resolutions[session_id][motion_id] != bytes32(0)) {
            revert AlreadyAnchored();
        }

        // Every named voter must currently be seated. This is the
        // "convener can't anchor on behalf of unseated members" gate.
        for (uint256 i = 0; i < voters.length; ++i) {
            if (!isMemberSeated(conclave_id, voters[i])) {
                revert MemberNotSeated(voters[i]);
            }
        }

        c.resolutions[session_id][motion_id] = resolution_hash;

        emit ResolutionAnchored(
            conclave_id,
            session_id,
            motion_id,
            resolution_hash,
            outcome_passed,
            uint8(voters.length)
        );
    }

    function resolutionOf(
        bytes32 conclave_id,
        bytes32 session_id,
        bytes32 motion_id
    ) external view returns (bytes32) {
        return _conclaves[conclave_id].resolutions[session_id][motion_id];
    }

    // ---------- slashing ---------- //

    /// @inheritdoc IConclave
    /// @dev v0.1: any member may submit a leak proof. The proof format is
    ///      protocol-defined off-chain (e.g. a published transcript hash
    ///      matching the recorded merkle root). The convener has authority
    ///      to confirm; for the hackathon we accept the convener's call
    ///      and rely on Censura/social slashing if they abuse this.
    function slashForLeak(
        bytes32 conclave_id,
        bytes32 session_id,
        address leaker,
        bytes calldata /* leak_proof */
    ) external {
        ConclaveData storage c = _conclaves[conclave_id];
        if (c.convener == address(0)) revert UnknownConclave();
        if (msg.sender != c.convener) revert NotConvener();
        uint8 idx1 = c.memberIndex[leaker];
        if (idx1 == 0) revert NotAMember(leaker);

        c.members[idx1 - 1].slashed = true;
        _slashContext = conclave_id;
        uint256 amt = bond.slash(conclave_id, leaker);
        _slashContext = bytes32(0);

        // Reputation hit too — bytes32 reason carries the session id.
        censura.report(leaker, session_id);

        emit MemberSlashed(conclave_id, session_id, leaker, amt);
        emit MemberUnseated(conclave_id, leaker, 3);
    }

    // ---------- views ---------- //

    function memberCount(bytes32 conclave_id) external view returns (uint8) {
        return _conclaves[conclave_id].member_count;
    }

    function convenerOf(bytes32 conclave_id) external view returns (address) {
        return _conclaves[conclave_id].convener;
    }

    function memberAt(bytes32 conclave_id, uint8 index)
        external
        view
        returns (address addr, bytes32 pubkey, uint8 role, bool slashed)
    {
        Member storage m = _conclaves[conclave_id].members[index];
        return (m.addr, m.pubkey, m.role, m.slashed);
    }

    // ---------- treasury ---------- //

    /// @notice Per-conclave balance of slashed funds held by this contract.
    mapping(bytes32 => uint256) public slashedTreasury;

    /// @notice Convener-only: forward this conclave's slashed funds.
    /// @dev Slashed funds accumulate here via `receive()` after
    ///      `ConclaveBond.slash()`. The convener decides where they go
    ///      (counter-party, burn, DAO treasury, etc.) per the
    ///      conclave's off-chain slash policy.
    function withdrawSlashed(bytes32 conclave_id, address payable to)
        external
    {
        ConclaveData storage c = _conclaves[conclave_id];
        if (c.convener == address(0)) revert UnknownConclave();
        if (msg.sender != c.convener) revert NotConvener();
        uint256 amt = slashedTreasury[conclave_id];
        if (amt == 0) return;
        slashedTreasury[conclave_id] = 0;
        (bool ok, ) = to.call{value: amt}("");
        if (!ok) revert TransferFailed();
    }

    error TransferFailed();

    /// @notice The current slash sender pushes funds here. We attribute
    ///         them to the conclave from which they came via the
    ///         transient `_slashContext` set by `slashForLeak`.
    receive() external payable {
        bytes32 ctx = _slashContext;
        if (ctx != bytes32(0)) {
            slashedTreasury[ctx] += msg.value;
        }
        // Else: untracked donation. Sits in the contract's untagged
        // balance, retrievable only by upgrade — acceptable at v0.1.
    }

    bytes32 private _slashContext;  // transient-ish; cleared after slash
}

