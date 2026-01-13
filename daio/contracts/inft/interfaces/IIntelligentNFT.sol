// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../dnft/interfaces/IDynamicNFT.sol";

/**
 * @title IIntelligentNFT
 * @notice Interface for Intelligent NFT contracts
 * @dev iNFTs extend dNFTs with on-chain intelligence capabilities
 * @dev Can interact with agents and exhibit autonomous behavior
 */
interface IIntelligentNFT is IDynamicNFT {
    struct IntelligenceConfig {
        address agentAddress;      // Agent that can interact
        bool autonomous;            // Can act autonomously
        string behaviorCID;        // IPFS CID for behavior definition
        string thotCID;            // Optional THOT for intelligence
        uint256 intelligenceLevel; // Level of intelligence (0-100)
    }

    /**
     * @notice Emitted when an agent interacts with the NFT
     * @param tokenId The token ID
     * @param agent Address of the interacting agent
     * @param interactionData Encoded interaction data
     */
    event AgentInteraction(
        uint256 indexed tokenId,
        address indexed agent,
        bytes interactionData
    );

    /**
     * @notice Emitted when intelligence configuration is updated
     * @param tokenId The token ID
     * @param config The new intelligence configuration
     */
    event IntelligenceUpdated(
        uint256 indexed tokenId,
        IntelligenceConfig config
    );

    /**
     * @notice Mint a new intelligent NFT
     * @param to Address to mint the NFT to
     * @param nftMetadata Initial metadata for the NFT
     * @param intelConfig Intelligence configuration
     * @return tokenId The ID of the newly minted token
     */
    function mintIntelligent(
        address to,
        NFTMetadata memory nftMetadata,
        IntelligenceConfig memory intelConfig
    ) external returns (uint256);

    /**
     * @notice Allow an agent to interact with the NFT
     * @param tokenId The token ID
     * @param interactionData Encoded interaction data
     */
    function agentInteract(
        uint256 tokenId,
        bytes calldata interactionData
    ) external;

    /**
     * @notice Update intelligence configuration
     * @param tokenId The token ID
     * @param newConfig New intelligence configuration
     */
    function updateIntelligence(
        uint256 tokenId,
        IntelligenceConfig memory newConfig
    ) external;

    /**
     * @notice Get intelligence configuration for a token
     * @param tokenId The token ID
     * @return config The intelligence configuration
     */
    function intelligence(uint256 tokenId) 
        external 
        view 
        returns (IntelligenceConfig memory);
}
