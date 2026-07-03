// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IX402
/// @notice Contract-side surface for the x402 payment-required protocol
///         facilitated by Parsec (parsec.finance / parsec-wallet) on Algorand.
///         Off-chain, callers pay a micro-fee in ALGO or USDCa; the Parsec
///         facilitator posts a settlement receipt on-chain that this contract
///         verifies before granting access to gated operations.
interface IX402 {
    /// @notice A single payment receipt from the Parsec facilitator.
    /// @param  facilitator  authorised Parsec signer
    /// @param  payer        on-chain identity that paid (EVM binding)
    /// @param  amount       amount paid, asset-denominated
    /// @param  asset        bytes32("ALGO") or bytes32("USDCa") etc.
    /// @param  scope        what this receipt unlocks (function selector or topic)
    /// @param  nonce        monotonic per-payer nonce to prevent replay
    /// @param  expiry       unix timestamp after which receipt is invalid
    /// @param  algoTxId     Algorand tx id of the underlying payment
    struct Receipt {
        address facilitator;
        address payer;
        uint256 amount;
        bytes32 asset;
        bytes32 scope;
        uint64  nonce;
        uint64  expiry;
        bytes32 algoTxId;
    }

    event FacilitatorSet(address indexed facilitator, bool authorised);
    event ReceiptConsumed(address indexed payer, bytes32 indexed scope, uint64 nonce);
    event PriceSet(bytes32 indexed scope, uint256 amount, bytes32 asset);

    error UnauthorisedFacilitator();
    error ReceiptReplayed();
    error ReceiptExpired();
    error InsufficientPayment();
    error BadScope();

    function setFacilitator(address facilitator, bool authorised) external;
    function setPrice(bytes32 scope, uint256 amount, bytes32 asset) external;
    function priceOf(bytes32 scope) external view returns (uint256 amount, bytes32 asset);

    /// @notice Consume a receipt and gate access for msg.sender.
    /// @dev    Reverts on any validation failure; emits ReceiptConsumed on success.
    function consume(Receipt calldata r, bytes calldata sig) external;

    /// @notice Check if a scope was paid by an account (does not consume).
    function hasPaid(address account, bytes32 scope) external view returns (bool);
}
