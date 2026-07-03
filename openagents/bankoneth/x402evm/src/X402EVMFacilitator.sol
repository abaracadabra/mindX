// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// X402EVMFacilitator — the EVM-side x402 settlement attestor for BANKON / mindX / AgenticPlace
// service delivery. A facilitator (the bankon backend, or AgenticPlace's payment processor)
// observes an HTTP-402 USDC payment settle on an EVM chain (Base, Arc, Optimism, …) and signs an
// EIP-712 X402EVMReceipt; anyone may submit it here to record settlement. Two replay guards
// (monotonic per-facilitator nonce + spent-digest set), EIP-712 + ERC-1271 signatures.
// Downstream services (registrar, marketplace, mindX delivery) gate on isSettled(digest) or the
// X402EVMSettled event. Generalizes BankonX402Attestor (Algorand) + Pay2PlayArcSettlement (Arc)
// to every EVM rail.
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import {IX402EVM, X402EVMReceipt} from "./interfaces/IX402EVM.sol";
import {X402ChainRegistry} from "./X402ChainRegistry.sol";

contract X402EVMFacilitator is AccessControl, EIP712, IX402EVM {
    bytes32 public constant FACILITATOR_ADMIN = keccak256("FACILITATOR_ADMIN");
    bytes32 private constant RECEIPT_TYPEHASH = keccak256(
        "X402EVMReceipt(bytes32 resourceHash,address payer,address asset,uint256 amount,uint64 srcChainId,uint64 nonce,uint64 expiresAt)"
    );

    X402ChainRegistry public immutable registry;
    mapping(address => bool) public isFacilitator;
    mapping(address => uint64) public lastNonce;   // monotonic per facilitator
    mapping(bytes32 => bool) public settled;       // spent digest set

    event FacilitatorSet(address indexed facilitator, bool active);
    event X402EVMSettled(
        bytes32 indexed digest, bytes32 indexed resourceHash, address indexed payer,
        address asset, uint256 amount, uint64 srcChainId, uint64 nonce, address facilitator
    );

    error not_facilitator();
    error expired();
    error bad_chain_or_asset();
    error stale_nonce();
    error bad_sig();
    error already_settled();

    constructor(address admin, X402ChainRegistry registry_) EIP712("X402EVMFacilitator", "1") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FACILITATOR_ADMIN, admin);
        registry = registry_;
    }

    function setFacilitator(address f, bool active) external onlyRole(FACILITATOR_ADMIN) {
        isFacilitator[f] = active;
        emit FacilitatorSet(f, active);
    }

    function digestOf(X402EVMReceipt calldata r) public view returns (bytes32) {
        return _hashTypedDataV4(keccak256(abi.encode(
            RECEIPT_TYPEHASH, r.resourceHash, r.payer, r.asset, r.amount, r.srcChainId, r.nonce, r.expiresAt
        )));
    }

    /// @notice Record a facilitator-signed x402 settlement. Permissionless to submit; the signature
    ///         + replay guards + registry checks are the trust. Returns the receipt digest.
    function settle(X402EVMReceipt calldata r, address facilitator, bytes calldata sig)
        external returns (bytes32 digest)
    {
        if (!isFacilitator[facilitator]) revert not_facilitator();
        if (block.timestamp > r.expiresAt) revert expired();
        if (!registry.isSettlementAsset(r.srcChainId, r.asset)) revert bad_chain_or_asset();
        if (r.nonce <= lastNonce[facilitator]) revert stale_nonce();
        digest = digestOf(r);
        if (settled[digest]) revert already_settled();
        if (!SignatureChecker.isValidSignatureNow(facilitator, digest, sig)) revert bad_sig();
        lastNonce[facilitator] = r.nonce;
        settled[digest] = true;
        emit X402EVMSettled(digest, r.resourceHash, r.payer, r.asset, r.amount, r.srcChainId, r.nonce, facilitator);
    }

    function isSettled(bytes32 digest) external view returns (bool) { return settled[digest]; }
}
