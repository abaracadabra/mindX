// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

import {
    IERC7857DataVerifier, TransferValidityProof, TransferValidityProofOutput,
    AccessProof, OwnershipProof, OracleType
} from "./bankon_interfaces.sol";

/// @title bankon_inft_oracle — v1 BANKON multisig EIP-712 attestation verifier
/// @notice Pluggable IERC7857DataVerifier. v1 stores a signer quorum (TEE-style
///         attestation). v2 module swaps in Intel SGX quote / ZKP verification
///         WITHOUT changing the iNFT — the iNFT only knows `verifier()`.
contract bankon_inft_oracle is IERC7857DataVerifier, Ownable, Pausable, EIP712 {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    error ProofReplayed(bytes32 nonce);
    error ProofExpired(bytes32 nonce);
    error InvalidQuorum();
    error NotEnoughSigners();
    error UnsupportedOracleType();

    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event QuorumUpdated(uint256 oldQuorum, uint256 newQuorum);

    mapping(address => bool) public isSigner;
    address[] public signers;
    uint256 public quorum;
    mapping(bytes32 => bool) internal usedProofs;
    mapping(bytes32 => uint256) internal proofTimestamps;
    uint256 public constant PROOF_GC_WINDOW = 7 days;

    bytes32 public constant TRANSFER_TYPEHASH = keccak256(
        "BankonTransfer(bytes32 oldDataHash,bytes32 newDataHash,bytes sealedKey,bytes encryptedPubKey,bytes nonce)"
    );

    constructor(address admin_, address[] memory signers_, uint256 quorum_)
        Ownable(admin_) EIP712("BankonINFTOracle", "1")
    {
        if (quorum_ == 0 || quorum_ > signers_.length) revert InvalidQuorum();
        for (uint256 i; i < signers_.length; ++i) {
            isSigner[signers_[i]] = true;
            signers.push(signers_[i]);
            emit SignerAdded(signers_[i]);
        }
        quorum = quorum_;
    }

    function addSigner(address s) external onlyOwner { isSigner[s] = true; signers.push(s); emit SignerAdded(s); }
    function setQuorum(uint256 q) external onlyOwner {
        if (q == 0 || q > signers.length) revert InvalidQuorum();
        emit QuorumUpdated(quorum, q); quorum = q;
    }
    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function _markNonce(bytes32 n) internal {
        if (usedProofs[n]) revert ProofReplayed(n);
        usedProofs[n] = true;
        proofTimestamps[n] = block.timestamp;
    }

    function cleanExpiredProofs(bytes32[] calldata nonces) external {
        for (uint256 i; i < nonces.length; ++i) {
            bytes32 n = nonces[i];
            if (usedProofs[n] && block.timestamp > proofTimestamps[n] + PROOF_GC_WINDOW) {
                delete usedProofs[n];
                delete proofTimestamps[n];
            }
        }
    }

    /// @notice Bundle-signed EIP-712 proof: `ownershipProof.proof` = abi.encode(bytes[] signatures)
    function verifyTransferValidity(TransferValidityProof[] calldata proofs)
        external override whenNotPaused returns (TransferValidityProofOutput[] memory outs)
    {
        outs = new TransferValidityProofOutput[](proofs.length);
        for (uint256 i; i < proofs.length; ++i) {
            TransferValidityProof calldata p = proofs[i];
            if (p.ownershipProof.oracleType != OracleType.TEE) revert UnsupportedOracleType();

            bytes32 nonceHash = keccak256(p.ownershipProof.nonce);
            _markNonce(nonceHash);

            bytes32 structHash = keccak256(abi.encode(
                TRANSFER_TYPEHASH,
                p.ownershipProof.oldDataHash,
                p.ownershipProof.newDataHash,
                keccak256(p.ownershipProof.sealedKey),
                keccak256(p.ownershipProof.encryptedPubKey),
                nonceHash
            ));
            bytes32 digest = _hashTypedDataV4(structHash);

            bytes[] memory sigs = abi.decode(p.ownershipProof.proof, (bytes[]));
            uint256 valid;
            address lastSigner;
            for (uint256 j; j < sigs.length; ++j) {
                address s = digest.recover(sigs[j]);
                if (isSigner[s] && s > lastSigner) { ++valid; lastSigner = s; }
            }
            if (valid < quorum) revert NotEnoughSigners();

            address assistant = p.accessProof.proof.length == 0
                ? address(0)
                : digest.recover(p.accessProof.proof);

            outs[i] = TransferValidityProofOutput({
                oldDataHash:        p.ownershipProof.oldDataHash,
                newDataHash:        p.ownershipProof.newDataHash,
                sealedKey:          p.ownershipProof.sealedKey,
                encryptedPubKey:    p.ownershipProof.encryptedPubKey,
                wantedKey:          p.accessProof.encryptedPubKey,
                accessAssistant:    assistant,
                accessProofNonce:   p.accessProof.nonce,
                ownershipProofNonce:p.ownershipProof.nonce
            });
        }
    }
}
