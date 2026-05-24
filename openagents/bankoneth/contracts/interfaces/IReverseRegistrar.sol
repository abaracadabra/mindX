// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

/// @notice Subset of the canonical ENS ReverseRegistrar we call from the
///         bankoneth registrar contracts. Mainnet
///         0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb. See
///         docs.ens.domains/web/naming-contracts for the full pattern.
///
///         `setName(string)` records the provided name as the reverse for
///         `msg.sender` (the calling contract). Combined with our admin-gated
///         `setReverseName(rr, name)` helper on each registrar, this lets the
///         treasury wire `registrar.bankon.eth` / `eth-registrar.bankon.eth`
///         / `host.bankon.eth` to each contract's address without changing
///         the constructor signature.
interface IReverseRegistrar {
    function setName(string memory name) external returns (bytes32);
    function setNameForAddr(address addr, address owner, address resolver, string memory name) external returns (bytes32);
    function claim(address owner) external returns (bytes32);
}
