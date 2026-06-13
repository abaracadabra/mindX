// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {EIP712}        from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA}         from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

import {IBankonX402Attestor} from "./interfaces/IBankonExtensions.sol";

/// @title  BankonX402Attestor
/// @notice EIP-712 facilitator-key registry + nonce replay guard for x402
///         receipts from the GoPlausible Algorand facilitator. Called by the
///         BankonSubnameRegistrar / BankonEthRegistrar / BankonDomainHosting
///         when the user pays via the x402-avm rail (Algorand USDC, ASA
///         31566704).
contract BankonX402Attestor is IBankonX402Attestor, EIP712, AccessControl {
    using ECDSA for bytes32;

    bytes32 public constant CONSUMER_ROLE = keccak256("CONSUMER_ROLE");

    bytes32 private constant _RECEIPT_TYPEHASH = keccak256(
        "X402Receipt(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt)"
    );

    /// @dev facilitator EOA → active?
    mapping(address => bool) private _facilitators;
    /// @dev receiptHash → spent? Primary replay guard.
    mapping(bytes32 => bool) private _spent;
    /// @dev facilitator → highest seen nonce. Tracked for off-chain monitoring
    ///      ONLY — we no longer reject out-of-order nonces, because that
    ///      caused false rejects under parallel consumption by multiple
    ///      registrars (Flow A + B + C all share this attestor). Replay
    ///      protection is provided by `_spent[receiptHash]` alone.
    mapping(address => uint64) public lastNonce;

    error ReceiptExpired();
    error ReceiptAlreadyConsumed(bytes32 receiptHash);
    error FacilitatorNotRegistered(address facilitator);

    constructor(address admin)
        EIP712("BankonX402Attestor", "1")
    {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    // ── Admin ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonX402Attestor
    function setFacilitator(address facilitator, bool active)
        external
        override
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        _facilitators[facilitator] = active;
        emit FacilitatorRegistered(facilitator, active);
    }

    function grantConsumer(address consumer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(CONSUMER_ROLE, consumer);
    }

    // ── Verify ─────────────────────────────────────────────────────

    /// @inheritdoc IBankonX402Attestor
    function verify(X402Receipt calldata r)
        external
        override
        onlyRole(CONSUMER_ROLE)
        returns (bool)
    {
        if (block.timestamp > r.expiresAt) revert ReceiptExpired();
        if (_spent[r.receiptHash]) revert ReceiptAlreadyConsumed(r.receiptHash);

        bytes32 structHash = keccak256(abi.encode(
            _RECEIPT_TYPEHASH,
            r.receiptHash,
            r.claimant,
            r.usd6,
            r.nonce,
            r.expiresAt
        ));
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = digest.recover(r.signature);

        if (!_facilitators[signer]) revert FacilitatorNotRegistered(signer);

        // Track highest-seen nonce per facilitator for off-chain monitoring;
        // no longer enforced as monotonic (see lastNonce doc comment).
        if (r.nonce > lastNonce[signer]) lastNonce[signer] = r.nonce;

        _spent[r.receiptHash] = true;
        emit ReceiptConsumed(r.receiptHash, r.claimant, r.nonce);
        return true;
    }

    // ── Views ──────────────────────────────────────────────────────

    /// @inheritdoc IBankonX402Attestor
    function isReceiptSpent(bytes32 receiptHash) external view override returns (bool) {
        return _spent[receiptHash];
    }

    function isFacilitatorActive(address facilitator) external view returns (bool) {
        return _facilitators[facilitator];
    }
}
