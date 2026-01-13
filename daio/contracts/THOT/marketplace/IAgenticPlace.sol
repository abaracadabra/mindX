// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IAgenticPlace
 * @notice Interface for AgenticPlace foundational marketplace
 * @dev Allows iNFT, dNFT, and other contracts to interact with AgenticPlace
 */
interface IAgenticPlace {
    enum NFTType {
        NFRLT,      // NFT Royalty Token
        THOT,       // Transferable Hyper-Optimized Tensor
        AgentNFT,   // AgentFactory NFT
        ERC721      // Generic ERC721 (includes iNFT, dNFT, etc.)
    }

    struct SkillOffer {
        uint256 skillTokenId;
        NFTType nftType;
        address nftContract;
        uint256 price;
        bool isETH;
        address paymentToken;
        address owner;
        bool isActive;
        uint40 createdAt;
        uint40 expiresAt;
    }

    event SkillOffered(
        uint256 indexed skillTokenId,
        address indexed nftContract,
        NFTType nftType,
        uint256 price,
        bool isETH,
        address paymentToken,
        address indexed owner,
        uint40 expiresAt
    );

    event SkillHired(
        uint256 indexed skillTokenId,
        address indexed nftContract,
        address indexed hirer,
        address owner,
        uint256 price,
        bool isETH,
        uint256 royaltyAmount
    );

    function offerSkill(
        uint256 skillTokenId,
        address nftContract,
        uint256 price,
        bool isETH,
        address paymentToken,
        uint40 expiresAt
    ) external;

    function hireSkillETH(
        uint256 skillTokenId,
        address nftContract
    ) external payable;

    function hireSkillERC20(
        uint256 skillTokenId,
        address nftContract,
        uint256 amount
    ) external;

    function getSkillOffer(
        uint256 skillTokenId,
        address nftContract
    ) external view returns (SkillOffer memory);

    function whitelistNFTContract(
        address nftContract,
        NFTType nftType
    ) external;

    function isNFTContractWhitelisted(address nftContract) external view returns (bool);
    function getNFTType(address nftContract) external view returns (NFTType);
}
