// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IMindX
/// @notice On-chain interface for the off-chain mindX API at mindx.pythai.net.
///         The contract merely stores attestations; the API signs them with a
///         registered key and anyone can submit the payload to settle on-chain.
interface IMindX {
    struct Attestation {
        bytes32 requestId;    // opaque id returned by mindX API
        bytes32 claimHash;    // keccak256 of the advisory blob
        uint64  issuedAt;
        uint32  modelVersion; // mindX model version
        uint16  riskScore;    // 0..10000 bps
        address subject;      // iDEBT holder the advice pertains to
    }

    event MindXKeyRotated(address indexed oldKey, address indexed newKey);
    event AttestationSettled(bytes32 indexed requestId, address indexed subject, uint16 riskScore);

    error BadSignature();
    error AttestationReplayed();
    error AttestationExpired();

    /// @notice Current mindX signing key.
    function signingKey() external view returns (address);

    /// @notice Rotate the mindX signing key (governance only).
    function rotateKey(address newKey) external;

    /// @notice Settle a mindX-signed attestation on-chain.
    function settle(Attestation calldata a, bytes calldata sig) external;

    /// @notice Retrieve the last settled risk score for a subject.
    function latestRiskScore(address subject) external view returns (uint16 score, uint64 at);
}
