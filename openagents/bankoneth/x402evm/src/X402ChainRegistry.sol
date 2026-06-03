// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// X402ChainRegistry — which EVM chains + assets are valid x402 settlement rails. One canonical
// USDC per chain (Base, Arc, Optimism, Polygon, Arbitrum, …) plus an extensible allow-map for
// extra settlement assets. The facilitator checks this before accepting a receipt.
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract X402ChainRegistry is Ownable {
    mapping(uint64 => address) public usdc;                          // chainId → canonical USDC
    mapping(uint64 => mapping(address => bool)) public allowedAsset; // chainId → asset → ok

    event ChainSet(uint64 indexed chainId, address usdc);
    event AssetSet(uint64 indexed chainId, address indexed asset, bool allowed);

    constructor(address owner_) Ownable(owner_) {}

    /// @notice Register a chain's canonical USDC (and allow it as a settlement asset).
    function setChain(uint64 chainId, address usdc_) external onlyOwner {
        usdc[chainId] = usdc_;
        allowedAsset[chainId][usdc_] = true;
        emit ChainSet(chainId, usdc_);
        emit AssetSet(chainId, usdc_, true);
    }

    function setAsset(uint64 chainId, address asset, bool allowed) external onlyOwner {
        allowedAsset[chainId][asset] = allowed;
        emit AssetSet(chainId, asset, allowed);
    }

    function isSettlementAsset(uint64 chainId, address asset) external view returns (bool) {
        return allowedAsset[chainId][asset];
    }
}
