// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ITHOTRegistry
 * @notice Interface for THOT registry and discovery system
 */
interface ITHOTRegistry {

    struct RegistryEntry {
        uint256 tokenId;
        address thotContract;        // THOTTensorNFT contract address
        bytes32 packageCID;
        string modelName;
        string architecture;
        uint256 parameterCount;
        address creator;
        uint256 createdAt;
        uint256 averageRating;       // Scaled by 100 (450 = 4.50 stars)
        uint256 ratingCount;
        uint256 deploymentCount;
        bool isVerified;             // Verified by DAO or trusted authority
    }

    // Events
    event THOTRegistered(
        address indexed thotContract,
        uint256 indexed tokenId,
        string modelName,
        address indexed creator
    );

    event THOTVerified(
        address indexed thotContract,
        uint256 indexed tokenId,
        bool verified
    );

    event THOTRatingUpdated(
        address indexed thotContract,
        uint256 indexed tokenId,
        uint256 averageRating,
        uint256 ratingCount
    );

    // Core Functions
    function registerTHOT(address thotContract, uint256 tokenId) external;
    function updateRegistryEntry(address thotContract, uint256 tokenId) external;
    function verifyTHOT(address thotContract, uint256 tokenId) external;
    function updateRating(address thotContract, uint256 tokenId, uint256 newRating) external;

    // Discovery
    function searchByArchitecture(string memory architecture) external view returns (RegistryEntry[] memory);
    function searchByParameterRange(uint256 minParams, uint256 maxParams) external view returns (RegistryEntry[] memory);
    function getTopRated(uint256 limit) external view returns (RegistryEntry[] memory);
    function getMostDeployed(uint256 limit) external view returns (RegistryEntry[] memory);
    function getByCreator(address creator) external view returns (RegistryEntry[] memory);

    // Verification
    function isVerified(address thotContract, uint256 tokenId) external view returns (bool);

    // Stats
    function getTotalTHOTs() external view returns (uint256);
    function getEntry(address thotContract, uint256 tokenId) external view returns (RegistryEntry memory);
}
