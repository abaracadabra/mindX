// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title iNFT - Intelligent NFT
 * @dev Immutable THOT implementation with full intelligence metadata
 * @notice Represents intelligent NFTs with THOT tensors, can be dynamic
 */
contract iNFT is ERC721, ERC721URIStorage, AccessControl {
    using Strings for uint256;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    struct ThotData {
        bytes32 dataCID;      // IPFS CID hash
        uint8 dimensions;     // 64, 512, or 768
        uint8 parallelUnits;  // Processing units
        uint40 timestamp;     // Creation time
        bool verified;        // Verification status
    }

    struct IntelligenceMetadata {
        string prompt;              // System prompt
        string persona;             // Persona JSON
        string modelDatasetCID;     // Model dataset IPFS CID
        bool isDynamic;             // Can metadata be updated
        uint40 lastUpdate;          // Last metadata update
    }

    mapping(uint256 => ThotData) private _thotData;
    mapping(uint256 => IntelligenceMetadata) private _intelligenceMetadata;
    mapping(bytes32 => bool) private _cidExists;
    mapping(uint256 => bool) private _isDynamic;
    
    event ThotMinted(
        uint256 indexed tokenId,
        bytes32 indexed dataCID,
        uint8 dimensions,
        uint40 timestamp
    );

    event IntelligenceMetadataUpdated(
        uint256 indexed tokenId,
        uint40 timestamp
    );

    constructor() ERC721("Intelligent NFT", "iNFT") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    /**
     * @dev Mint intelligent NFT with THOT data and intelligence metadata
     * @param recipient Recipient address
     * @param dataCID IPFS CID for THOT tensor data
     * @param dimensions THOT dimensions (64, 512, or 768)
     * @param parallelUnits Processing units
     * @param prompt System prompt
     * @param persona Persona JSON
     * @param modelDatasetCID Model dataset IPFS CID
     * @param isDynamic Whether metadata can be updated
     * @param tokenURI Token metadata URI
     */
    function mint(
        address recipient,
        bytes32 dataCID,
        uint8 dimensions,
        uint8 parallelUnits,
        string memory prompt,
        string memory persona,
        string memory modelDatasetCID,
        bool isDynamic,
        string memory tokenURI
    ) external onlyRole(MINTER_ROLE) returns (uint256) {
        require(!_cidExists[dataCID], "THOT already exists");
        require(
            dimensions == 64 || dimensions == 512 || dimensions == 768,
            "Invalid dimensions"
        );
        require(bytes(prompt).length > 0, "Prompt required");
        require(bytes(persona).length > 0, "Persona required");

        uint256 tokenId = uint256(
            keccak256(abi.encodePacked(dataCID, block.timestamp, recipient))
        );

        _thotData[tokenId] = ThotData({
            dataCID: dataCID,
            dimensions: dimensions,
            parallelUnits: parallelUnits,
            timestamp: uint40(block.timestamp),
            verified: true
        });

        _intelligenceMetadata[tokenId] = IntelligenceMetadata({
            prompt: prompt,
            persona: persona,
            modelDatasetCID: modelDatasetCID,
            isDynamic: isDynamic,
            lastUpdate: uint40(block.timestamp)
        });

        _cidExists[dataCID] = true;
        _isDynamic[tokenId] = isDynamic;
        _safeMint(recipient, tokenId);
        _setTokenURI(tokenId, tokenURI);

        emit ThotMinted(tokenId, dataCID, dimensions, uint40(block.timestamp));
        return tokenId;
    }

    /**
     * @dev Update intelligence metadata (only for dynamic iNFTs)
     */
    function updateIntelligenceMetadata(
        uint256 tokenId,
        string memory newPrompt,
        string memory newPersona,
        string memory newModelDatasetCID
    ) external {
        require(_exists(tokenId), "iNFT does not exist");
        require(_isDynamic[tokenId], "iNFT is not dynamic");
        require(ownerOf(tokenId) == msg.sender, "Not token owner");

        IntelligenceMetadata storage metadata = _intelligenceMetadata[tokenId];
        metadata.prompt = newPrompt;
        metadata.persona = newPersona;
        if (bytes(newModelDatasetCID).length > 0) {
            metadata.modelDatasetCID = newModelDatasetCID;
        }
        metadata.lastUpdate = uint40(block.timestamp);

        emit IntelligenceMetadataUpdated(tokenId, uint40(block.timestamp));
    }

    function getThotData(uint256 tokenId) 
        external 
        view 
        returns (ThotData memory) 
    {
        require(_exists(tokenId), "iNFT does not exist");
        return _thotData[tokenId];
    }

    function getIntelligenceMetadata(uint256 tokenId)
        external
        view
        returns (IntelligenceMetadata memory)
    {
        require(_exists(tokenId), "iNFT does not exist");
        return _intelligenceMetadata[tokenId];
    }

    function isDynamic(uint256 tokenId) external view returns (bool) {
        require(_exists(tokenId), "iNFT does not exist");
        return _isDynamic[tokenId];
    }

    // Override required functions
    function _burn(uint256 tokenId) 
        internal 
        override(ERC721, ERC721URIStorage) 
    {
        super._burn(tokenId);
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
