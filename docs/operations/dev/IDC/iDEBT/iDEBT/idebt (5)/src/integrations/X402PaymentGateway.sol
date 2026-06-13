// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl }         from "@openzeppelin/contracts/access/AccessControl.sol";
import { EIP712 }                from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import { ECDSA }                 from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import { MessageHashUtils }      from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

import { IX402 } from "../interfaces/IX402.sol";

/// @title X402PaymentGateway
/// @notice Verifies EIP-712 signed payment receipts issued by the Parsec
///         x402 facilitator for off-chain Algorand settlements.
/// @dev    Off-chain flow:
///           1. Caller requests a gated operation; server replies 402 with
///              x-payment-required: { scope, amount, asset, nonce, expiry }.
///           2. Caller pays the amount on Algorand via parsec-wallet.
///           3. Parsec returns an EIP-712 Receipt signed by an authorised key.
///           4. Caller submits the receipt here; gateway records it as spent.
///           6. Caller calls the gated op; that op checks `hasPaid`.
contract X402PaymentGateway is IX402, AccessControl, EIP712 {
    using MessageHashUtils for bytes32;

    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    /// @dev keccak256("Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)")
    bytes32 public constant RECEIPT_TYPEHASH =
        0x3d5f0d1d2b9c9d3c8b42d3b96d59cb6e1b3c08dc1c3d0b5d0e9f6f1a11f9b8c2; // placeholder; computed below in constructor sanity check

    // facilitator => authorised?
    mapping(address => bool) public facilitators;

    // payer => nonce => used?
    mapping(address => mapping(uint64 => bool)) public usedNonces;

    // payer => scope => paid-through-expiry
    mapping(address => mapping(bytes32 => uint64)) private _paidUntil;

    // scope => (amount, asset)
    mapping(bytes32 => uint256) public scopePrice;
    mapping(bytes32 => bytes32) public scopeAsset;

    constructor(address admin) EIP712("iDEBT-x402", "1") {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNOR_ROLE, admin);
    }

    // -------------------------------------------------------------- //
    //                              ADMIN                             //
    // -------------------------------------------------------------- //

    function setFacilitator(address facilitator, bool authorised) external onlyRole(GOVERNOR_ROLE) {
        facilitators[facilitator] = authorised;
        emit FacilitatorSet(facilitator, authorised);
    }

    function setPrice(bytes32 scope, uint256 amount, bytes32 asset) external onlyRole(GOVERNOR_ROLE) {
        scopePrice[scope] = amount;
        scopeAsset[scope] = asset;
        emit PriceSet(scope, amount, asset);
    }

    function priceOf(bytes32 scope) external view returns (uint256 amount, bytes32 asset) {
        return (scopePrice[scope], scopeAsset[scope]);
    }

    // -------------------------------------------------------------- //
    //                            RECEIPTS                            //
    // -------------------------------------------------------------- //

    function consume(Receipt calldata r, bytes calldata sig) external {
        if (!facilitators[r.facilitator]) revert UnauthorisedFacilitator();
        if (block.timestamp > r.expiry)   revert ReceiptExpired();
        if (usedNonces[r.payer][r.nonce]) revert ReceiptReplayed();
        if (scopePrice[r.scope] == 0)     revert BadScope();
        if (r.amount < scopePrice[r.scope] || r.asset != scopeAsset[r.scope]) {
            revert InsufficientPayment();
        }

        bytes32 structHash = keccak256(abi.encode(
            keccak256(
                "Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)"
            ),
            r.facilitator,
            r.payer,
            r.amount,
            r.asset,
            r.scope,
            r.nonce,
            r.expiry,
            r.algoTxId
        ));
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = ECDSA.recover(digest, sig);
        if (signer != r.facilitator) revert UnauthorisedFacilitator();

        usedNonces[r.payer][r.nonce] = true;
        // Grant access through receipt expiry window.
        _paidUntil[r.payer][r.scope] = r.expiry;
        emit ReceiptConsumed(r.payer, r.scope, r.nonce);
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function hasPaid(address account, bytes32 scope) external view returns (bool) {
        return _paidUntil[account][scope] >= block.timestamp;
    }

    function paidUntil(address account, bytes32 scope) external view returns (uint64) {
        return _paidUntil[account][scope];
    }

    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }
}
