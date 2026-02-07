// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../inft/IntelligentNFT.sol";
import "../inft/interfaces/IIntelligentNFT.sol";
import "../dnft/interfaces/IDynamicNFT.sol";

/**
 * @title VaultKeyIntelligent
 * @notice Keyminter for issuance of vault access: mints intelligent keys (iNFT) that grant access to the vault.
 * @dev Extends IntelligentNFT; each minted token is a "vault access key" with an optional authorized agent (e.g. backend) that can agentInteract to log or revoke.
 * @dev Backend access_gate checks balanceOf(wallet) or ownerOf(tokenId). Backend may call agentInteract(tokenId, data) to log access.
 */
contract VaultKeyIntelligent is IntelligentNFT {
    event VaultKeyMintedIntelligent(
        uint256 indexed tokenId,
        address indexed to,
        string scope,
        string expiryHint,
        address agentAddress
    );

    constructor(
        address initialOwner,
        address agenticPlace
    ) IntelligentNFT(
        "MindX Vault Key i",
        "VAULTKEY-i",
        initialOwner,
        agenticPlace
    ) {}

    /**
     * @notice Mint an intelligent vault access key (scope, expiry hint, optional authorized agent).
     * @param to Recipient (holder of the key gains vault access when backend checks this contract).
     * @param scope Short label for key scope (e.g. "user_folder", "full_vault").
     * @param expiryHint Optional expiry hint (e.g. "2025-12-31" or ""); not enforced on-chain.
     * @param agentAddress Address allowed to agentInteract (e.g. mindX vault backend for logging/revoke); use address(0) to disable.
     */
    function mintKeyIntelligent(
        address to,
        string calldata scope,
        string calldata expiryHint,
        address agentAddress
    ) external onlyOwner returns (uint256) {
        string memory name = _keyName(scope, expiryHint);
        string memory description = scope;
        if (bytes(expiryHint).length > 0) {
            description = string(abi.encodePacked(scope, " (expiry: ", expiryHint, ")"));
        }
        IDynamicNFT.NFTMetadata memory nftMetadata = IDynamicNFT.NFTMetadata({
            name: name,
            description: description,
            imageURI: "",
            externalURI: "",
            thotCID: "",
            isDynamic: true,
            lastUpdated: block.timestamp
        });
        IIntelligentNFT.IntelligenceConfig memory intelConfig = IIntelligentNFT.IntelligenceConfig({
            agentAddress: agentAddress,
            autonomous: false,
            behaviorCID: "",
            thotCID: "",
            intelligenceLevel: 1
        });
        uint256 tokenId = super.mintIntelligent(to, nftMetadata, intelConfig);
        emit VaultKeyMintedIntelligent(tokenId, to, scope, expiryHint, agentAddress);
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
