// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../dnft/DynamicNFT.sol";
import "../dnft/interfaces/IDynamicNFT.sol";

/**
 * @title VaultKeyDynamic
 * @notice Keyminter for issuance of vault access: mints dynamic keys (dNFT) that grant access to the vault.
 * @dev Extends DynamicNFT; each minted token is a "vault access key". Backend access_gate checks balanceOf(wallet) or ownerOf(tokenId).
 * @dev Metadata can store scope (e.g. "user_folder") and optional expiry hint; metadata is updatable until frozen.
 */
contract VaultKeyDynamic is DynamicNFT {
    event VaultKeyMinted(
        uint256 indexed tokenId,
        address indexed to,
        string scope,
        string expiryHint
    );

    constructor(
        address initialOwner,
        address agenticPlace
    ) DynamicNFT(
        "MindX Vault Key",
        "VAULTKEY",
        initialOwner,
        agenticPlace
    ) {}

    /**
     * @notice Mint a vault access key (dynamic key with scope and optional expiry hint).
     * @param to Recipient (holder of the key gains vault access when backend checks this contract).
     * @param scope Short label for key scope (e.g. "user_folder", "full_vault").
     * @param expiryHint Optional expiry hint (e.g. "2025-12-31" or "" for none); not enforced on-chain.
     */
    function mintKey(
        address to,
        string calldata scope,
        string calldata expiryHint
    ) external onlyOwner returns (uint256) {
        string memory name = _keyName(scope, expiryHint);
        string memory description = scope;
        if (bytes(expiryHint).length > 0) {
            description = string(abi.encodePacked(scope, " (expiry: ", expiryHint, ")"));
        }
        IDynamicNFT.NFTMetadata memory meta = IDynamicNFT.NFTMetadata({
            name: name,
            description: description,
            imageURI: "",
            externalURI: "",
            thotCID: "",
            isDynamic: true,
            lastUpdated: block.timestamp
        });
        uint256 tokenId = mint(to, meta);
        emit VaultKeyMinted(tokenId, to, scope, expiryHint);
        return tokenId;
    }

    function _keyName(
        string memory scope,
        string memory expiryHint
    ) internal pure returns (string memory) {
        if (bytes(expiryHint).length == 0) {
            return string(abi.encodePacked("Vault Key: ", scope));
        }
        return string(abi.encodePacked("Vault Key: ", scope, " until ", expiryHint));
    }
}
