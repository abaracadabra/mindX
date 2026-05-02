// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

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
