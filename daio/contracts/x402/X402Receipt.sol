// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import {AccessControl}     from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonPaymentRouter} from "../ens/v1/interfaces/IBankon.sol";

/// @title  X402Receipt — canonical on-chain attestation for HTTP 402 settlements.
/// @author mindX
/// @notice Records a verified x402 payment receipt and (optionally) cascades into
///         BankonPaymentRouter for treasury split. Designed as a cross-chain pair
///         with `daio/contracts/algorand/x402_receipt.algo.ts` — same field set,
///         same event shape so a unified indexer joins both chains by receiptHash.
///
///         **What this contract does**
///         1. Verifies a signature over the receipt struct, supporting:
///              - EOA signers (ECDSA)
///              - Multisig signers (ERC-1271 / Safe) — via SignatureChecker
///         2. Enforces idempotency: a receiptHash can only be recorded once.
///         3. Emits a flat indexable event so off-chain systems can fan out.
///         4. Optionally calls IBankonPaymentRouter.recordReceipt for split accounting.
///
///         **What this contract does NOT do**
///         - Move tokens. Settlement is the ERC-20 `transferWithAuthorization`
///           the facilitator already executed. This is the attestation layer.
///         - Validate the receipt struct's economic content. The signature is
///           the trust boundary; payer asserts the values by signing.
///
///         The Algorand counterpart at `daio/contracts/algorand/x402_receipt.algo.ts`
///         exposes the same ABI signature and emits a structurally equivalent log
///         so a unified indexer reads `(chainKind, chainId, receiptHash)` triples.
contract X402Receipt is AccessControl {
    using MessageHashUtils for bytes32;

    /// @notice Optional downstream router. Address(0) = no cascade.
    ///         When non-zero, the router must grant REGISTRAR_ROLE to this
    ///         contract's address post-deploy so the cascade can land.
    IBankonPaymentRouter public immutable router;

    /// @notice Receipt hashes already recorded — anti-replay.
    mapping(bytes32 => bool) public seenReceipt;

    /// @notice Emitted on every accepted receipt. Cross-chain compatible: the
    ///         AVM counterpart emits a log with the same field set in arc4 form.
    event X402ReceiptRecorded(
        bytes32 indexed receiptHash,
        bytes32 indexed resourceHash,
        address payer,
        address payee,
        address asset,
        uint256 amount,
        uint64  chainId,
        uint64  blockNumber
    );

    error ReceiptAlreadyRecorded(bytes32 receiptHash);
    error ReceiptHashMismatch(bytes32 expected, bytes32 computed);
    error InvalidSignature();
    error ZeroPayer();

    constructor(address admin, IBankonPaymentRouter router_) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        router = router_;
    }

    // ─────────────────────────────────────────────────────────────────
    // Public surface
    // ─────────────────────────────────────────────────────────────────

    /// @notice Compute the canonical x402 receipt hash. Call this off-chain to
    ///         construct a `receiptHash` that matches what the contract checks.
    ///
    /// @dev    Encoding is `keccak256(abi.encode(...))` rather than packed —
    ///         abi.encode is unambiguous and forge-friendly. The AVM
    ///         counterpart uses sha256 over the same logical fields with an
    ///         AVM-shaped encoding; the cross-chain join key is `receiptHash`
    ///         per chain, not bit-identical hashes.
    function canonicalReceiptHash(
        address payer,
        address payee,
        address asset,
        uint256 amount,
        bytes32 resourceHash,
        bytes32 nonce
    ) public view returns (bytes32) {
        return keccak256(
            abi.encode(
                bytes32("x402-receipt-v1"),
                block.chainid,
                payer,
                payee,
                asset,
                amount,
                resourceHash,
                nonce
            )
        );
    }

    /// @notice Record a verified x402 receipt.
    ///
    /// @param receiptHash    Pre-computed via `canonicalReceiptHash`.
    /// @param payer          The account that authorized the payment.
    ///                       For multisig, this is the Safe address; the
    ///                       signature is verified via ERC-1271 callback.
    /// @param payee          The settlement recipient (informational only here).
    /// @param asset          Settlement asset (USDC contract on EVM rails).
    /// @param amount         Settlement amount in the asset's base units.
    /// @param resourceHash   keccak256 of the paid resource URL (for indexing).
    /// @param nonce          Unique per receipt. Caller-supplied; receipt hash
    ///                       collisions still revert via `seenReceipt`.
    /// @param signature      EIP-191 signature (`personal_sign`) of receiptHash
    ///                       by `payer`. EOA or ERC-1271 contract — both work.
    function recordX402Receipt(
        bytes32 receiptHash,
        address payer,
        address payee,
        address asset,
        uint256 amount,
        bytes32 resourceHash,
        bytes32 nonce,
        bytes calldata signature
    ) external {
        if (payer == address(0)) revert ZeroPayer();
        if (seenReceipt[receiptHash]) revert ReceiptAlreadyRecorded(receiptHash);

        bytes32 expected = canonicalReceiptHash(payer, payee, asset, amount, resourceHash, nonce);
        if (expected != receiptHash) revert ReceiptHashMismatch(expected, receiptHash);

        // SignatureChecker handles EOA (ECDSA) AND ERC-1271 multisig via fallback.
        // The signed digest is the EIP-191 prefixed hash so wallets can sign with
        // `personal_sign` directly without bespoke typed-data infra.
        bytes32 digest = receiptHash.toEthSignedMessageHash();
        if (!SignatureChecker.isValidSignatureNow(payer, digest, signature)) {
            revert InvalidSignature();
        }

        seenReceipt[receiptHash] = true;

        emit X402ReceiptRecorded(
            receiptHash,
            resourceHash,
            payer,
            payee,
            asset,
            amount,
            uint64(block.chainid),
            uint64(block.number)
        );

        // Cascade into router if wired. The router enforces its own anti-replay
        // (independent mapping). Post-deploy, the operator grants REGISTRAR_ROLE
        // on the router to this contract's address; without that grant the
        // cascade reverts and a fresh wire is required.
        if (address(router) != address(0)) {
            // `amount` is the asset's base units (USDC = 6 dp). Non-USDC rails
            // need a wrapper that converts before cascading.
            router.recordReceipt(receiptHash, amount, asset);
        }
    }
}
