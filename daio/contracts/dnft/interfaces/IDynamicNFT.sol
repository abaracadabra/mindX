// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IDynamicNFT
 * @notice Interface for Dynamic NFT contracts supporting ERC4906 metadata updates
 * @dev Dynamic NFTs can have their metadata updated after minting
 */
interface IDynamicNFT {
    struct NFTMetadata {
        string name;
        string description;
        string imageURI;        // IPFS CID or URL
        string externalURI;     // Optional external link
        string thotCID;         // Optional THOT artifact CID
        bool isDynamic;         // Can metadata be updated
        uint256 lastUpdated;    // Timestamp of last update
    }

    /**
     * @notice Emitted when NFT metadata is updated
     * @param tokenId The token ID that was updated
     * @param metadata The new metadata
     */
    event MetadataUpdated(uint256 indexed tokenId, NFTMetadata metadata);

    /**
     * @notice Emitted when metadata is frozen (cannot be updated)
     * @param tokenId The token ID that was frozen
     */
    event MetadataFrozen(uint256 indexed tokenId);

    /**
     * @notice Mint a new dynamic NFT
     * @param to Address to mint the NFT to
     * @param nftMetadata Initial metadata for the NFT
     * @return tokenId The ID of the newly minted token
     */
    function mint(
        address to,
        NFTMetadata memory nftMetadata
    ) external returns (uint256);

    /**
     * @notice Update metadata for an existing NFT
     * @param tokenId The token ID to update
     * @param newMetadata The new metadata
     */
    function updateMetadata(
        uint256 tokenId,
        NFTMetadata memory newMetadata
    ) external;

    /**
     * @notice Freeze metadata to prevent future updates
     * @param tokenId The token ID to freeze
     */
    function freezeMetadata(uint256 tokenId) external;

    /**
     * @notice Get metadata for a token
     * @param tokenId The token ID
     * @return metadata The metadata struct
     */
    function metadata(uint256 tokenId) external view returns (NFTMetadata memory);

    /**
     * @notice Check if metadata is frozen
     * @param tokenId The token ID
     * @return frozen True if metadata cannot be updated
     */
    function frozen(uint256 tokenId) external view returns (bool);
}
