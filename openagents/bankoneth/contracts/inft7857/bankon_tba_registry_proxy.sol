// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Source: docs/…ERC-7857 iNFT and ERC-6551 TBA Integration.md (pragma relaxed to ^0.8.24).
pragma solidity ^0.8.24;

import {IERC6551Registry} from "./bankon_interfaces.sol";

/// @title bankon_tba_registry_proxy — thin event-emitting wrapper around the canonical 6551 registry
/// @notice Calls 0x000000006551c19487814612e58FE06813775758 and emits BANKON-flavored events so
///         AgenticPlace / indexers can pick up TBA creations without filtering the global registry.
contract bankon_tba_registry_proxy {
    IERC6551Registry public constant CANONICAL =
        IERC6551Registry(0x000000006551c19487814612e58FE06813775758);

    event BankonTbaCreated(
        address indexed account,
        address indexed iNftContract,
        uint256 indexed tokenId,
        address implementation,
        uint256 chainId,
        bytes32 salt
    );

    function createAccount(
        address implementation,
        bytes32 salt,
        uint256 chainId,
        address tokenContract,
        uint256 tokenId
    ) external returns (address acct) {
        acct = CANONICAL.createAccount(implementation, salt, chainId, tokenContract, tokenId);
        emit BankonTbaCreated(acct, tokenContract, tokenId, implementation, chainId, salt);
    }

    function account(
        address implementation,
        bytes32 salt,
        uint256 chainId,
        address tokenContract,
        uint256 tokenId
    ) external view returns (address) {
        return CANONICAL.account(implementation, salt, chainId, tokenContract, tokenId);
    }
}
