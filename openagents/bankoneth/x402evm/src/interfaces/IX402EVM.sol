// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

/// @notice A facilitator-signed receipt attesting an HTTP-402 (x402) USDC settlement on an EVM
///         chain (Base, Arc, Optimism, …). The same shape covers every EVM rail; `srcChainId`
///         + `asset` say where/what settled. Mirrors the proven Pay2Play/Attestor receipt design.
struct X402EVMReceipt {
    bytes32 resourceHash;   // keccak256 of the paid resource / service id / endpoint
    address payer;          // who paid (and receives the entitlement/record)
    address asset;          // settlement token (USDC) on srcChainId
    uint256 amount;         // base units (6dp for USDC) settled
    uint64  srcChainId;     // the EVM chain the payment settled on (8453 Base, 5042002 Arc, …)
    uint64  nonce;          // strictly monotonic per facilitator (replay guard 1)
    uint64  expiresAt;      // unix seconds
}

interface IX402EVM {
    function settle(X402EVMReceipt calldata r, address facilitator, bytes calldata sig) external returns (bytes32 digest);
    function isSettled(bytes32 digest) external view returns (bool);
    function digestOf(X402EVMReceipt calldata r) external view returns (bytes32);
}
