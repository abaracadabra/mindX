// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IBANKON
/// @notice On-chain hook into the BANKON AlgoIDNFT sovereign identity system
///         (bankon.pythai.net). iDEBT uses BANKON to bind positions to
///         sovereign identities so that inheritance remains cryptographically
///         valid across chains and time.
interface IBANKON {
    struct SovereignId {
        bytes32 algoIdRoot; // Algorand AlgoIDNFT commitment root
        address evmBinding; // bound EVM address
        uint64  boundAt;
        bool    active;
    }

    event SovereignIdBound(bytes32 indexed algoIdRoot, address indexed evmBinding);
    event SovereignIdRevoked(bytes32 indexed algoIdRoot);

    error InvalidBinding();
    error NotBound();

    function bind(bytes32 algoIdRoot, bytes calldata algoSig) external;
    function revoke() external;
    function sovereignOf(address account) external view returns (SovereignId memory);
    function isBound(address account) external view returns (bool);
}
