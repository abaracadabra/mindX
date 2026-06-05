// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl }    from "@openzeppelin/contracts/access/AccessControl.sol";
import { EIP712 }           from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import { ECDSA }            from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

import { IMindX } from "../interfaces/IMindX.sol";

/// @title MindXBridge
/// @notice Settles signed advisory attestations produced by mindx.pythai.net.
///         The mindX API signs an EIP-712 Attestation with its registered key;
///         anyone can post it on-chain to surface the risk score.
contract MindXBridge is IMindX, AccessControl, EIP712 {
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    /// @dev keccak256 computed once on deploy; printed in event for auditability.
    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "Attestation(bytes32 requestId,bytes32 claimHash,uint64 issuedAt,uint32 modelVersion,uint16 riskScore,address subject)"
    );

    uint256 public maxAge = 1 days;

    address private _signingKey;

    mapping(bytes32 => bool) public consumed;

    struct LastScore {
        uint16 score;
        uint64 at;
    }
    mapping(address => LastScore) private _latest;

    constructor(address admin, address initialKey) EIP712("iDEBT-mindX", "1") {
        require(initialKey != address(0), "zero key");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNOR_ROLE, admin);
        _signingKey = initialKey;
        emit MindXKeyRotated(address(0), initialKey);
    }

    // -------------------------------------------------------------- //
    //                              ADMIN                             //
    // -------------------------------------------------------------- //

    function rotateKey(address newKey) external onlyRole(GOVERNOR_ROLE) {
        require(newKey != address(0), "zero key");
        emit MindXKeyRotated(_signingKey, newKey);
        _signingKey = newKey;
    }

    function setMaxAge(uint256 age) external onlyRole(GOVERNOR_ROLE) {
        maxAge = age;
    }

    // -------------------------------------------------------------- //
    //                           SETTLEMENT                           //
    // -------------------------------------------------------------- //

    function settle(Attestation calldata a, bytes calldata sig) external {
        if (consumed[a.requestId])                        revert AttestationReplayed();
        if (block.timestamp - a.issuedAt > maxAge)        revert AttestationExpired();

        bytes32 structHash = keccak256(abi.encode(
            ATTESTATION_TYPEHASH,
            a.requestId,
            a.claimHash,
            a.issuedAt,
            a.modelVersion,
            a.riskScore,
            a.subject
        ));
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = ECDSA.recover(digest, sig);
        if (signer != _signingKey) revert BadSignature();

        consumed[a.requestId] = true;
        _latest[a.subject] = LastScore({ score: a.riskScore, at: uint64(block.timestamp) });
        emit AttestationSettled(a.requestId, a.subject, a.riskScore);
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function signingKey() external view returns (address) {
        return _signingKey;
    }

    function latestRiskScore(address subject) external view returns (uint16 score, uint64 at) {
        LastScore memory s = _latest[subject];
        return (s.score, s.at);
    }
}
