// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IIdentityRegistry8004} from "../../interfaces/IBankon.sol";

/// @notice Minimal ERC-8004-shape identity registry mock.
contract MockIdentityRegistry is IIdentityRegistry8004 {
    uint256 public nextId = 1;
    mapping(uint256 => address) public ownerOf;
    mapping(uint256 => string)  public uriOf;
    mapping(uint256 => mapping(bytes32 => bytes)) public meta;

    function register(address agentWallet, string calldata agentURI)
        external override returns (uint256 agentId)
    {
        agentId = nextId++;
        ownerOf[agentId] = agentWallet;
        uriOf[agentId]   = agentURI;
    }

    function setMetadata(uint256 agentId, bytes32 key, bytes calldata value) external override {
        meta[agentId][key] = value;
    }
}
