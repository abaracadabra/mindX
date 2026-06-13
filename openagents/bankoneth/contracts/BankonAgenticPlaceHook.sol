// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonAgenticPlaceHook} from "./interfaces/IBankonExtensions.sol";

/// @title  BankonAgenticPlaceHook
/// @notice Optional per-mint listing emitter. When a flow opts in to publish to
///         agenticplace.pythai.net, the registrar (Flow A / B / C) calls
///         `list(...)` which emits an `AgenticPlaceListing` event that the
///         off-chain indexer on agenticplace.pythai.net consumes to create the
///         marketplace card.
///
///         The webhook URL is configurable so the same contract can be pointed
///         at a staging indexer for testnet rehearsal.
contract BankonAgenticPlaceHook is IBankonAgenticPlaceHook, AccessControl {
    bytes32 public constant LISTER_ROLE = keccak256("LISTER_ROLE");

    string private _webhookURL;

    event WebhookURLUpdated(string oldURL, string newURL);

    constructor(address admin, string memory initialWebhookURL) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _webhookURL = initialWebhookURL;
    }

    /// @inheritdoc IBankonAgenticPlaceHook
    function setWebhookURL(string calldata url)
        external
        override
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        emit WebhookURLUpdated(_webhookURL, url);
        _webhookURL = url;
    }

    /// @inheritdoc IBankonAgenticPlaceHook
    function webhookURL() external view override returns (string memory) {
        return _webhookURL;
    }

    function grantLister(address lister) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _grantRole(LISTER_ROLE, lister);
    }

    /// @inheritdoc IBankonAgenticPlaceHook
    function list(
        bytes32 parentNode,
        bytes32 labelhash,
        address tbaAddress,
        uint256 zeroGTokenId,
        string calldata metadataURI,
        address author
    ) external override onlyRole(LISTER_ROLE) {
        emit AgenticPlaceListing(
            parentNode,
            labelhash,
            tbaAddress,
            zeroGTokenId,
            metadataURI,
            author
        );
    }
}
