// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title THOT - Transferable Hyper-Optimized Tensor
 * @dev Core contract for creating and managing THOT artifacts
 * @notice THOTs are standardized tensor vectors (64, 512, 768, 1024, 2048 dimensions)
 * @dev cypherpunk2048 standard: 1024 (embedding-native) and 2048 (high-capacity) added
 */
contract THOT is ERC721, ERC721URIStorage, Ownable {
    using Strings for uint256;

    struct THOTData {
        bytes32 dataCID;       // IPFS CID hash for THOT tensor data
        uint16 dimensions;     // THOT dimensions: 64, 512, 768, 1024, or 2048
        uint8 parallelUnits;   // Processing units
        uint40 timestamp;      // Creation time
        bool verified;         // Verification status
        string metadataURI;    // Additional metadata URI
    }

    mapping(uint256 => THOTData) private _thotData;
    mapping(bytes32 => bool) private _cidExists;
    mapping(bytes32 => uint256) private _cidToTokenId;
    uint256 private _tokenIdCounter;

    event THOTMinted(
        uint256 indexed tokenId,
        bytes32 indexed dataCID,
        uint16 dimensions,
        uint40 timestamp
    );

    event THOTVerified(uint256 indexed tokenId, bool verified);

    constructor() ERC721("Transferable Hyper-Optimized Tensor", "THOT") Ownable(msg.sender) {
        _tokenIdCounter = 1;
    }

    /**
     * @dev Mint a new THOT
     * @param recipient Address to receive the THOT
     * @param dataCID IPFS CID for THOT tensor data
     * @param dimensions THOT dimensions (64, 512, 768, 1024, or 2048)
     * @param parallelUnits Processing units
     * @param metadataURI Additional metadata URI
     * @return tokenId The ID of the newly minted THOT
     */
    function mintTHOT(
        address recipient,
        bytes32 dataCID,
        uint16 dimensions,
        uint8 parallelUnits,
        string memory metadataURI
    ) external onlyOwner returns (uint256) {
        require(!_cidExists[dataCID], "THOT already exists");
        require(_isValidDimension(dimensions), "Invalid dimensions");
        require(recipient != address(0), "Invalid recipient");

        uint256 tokenId = _tokenIdCounter++;
        
        _thotData[tokenId] = THOTData({
            dataCID: dataCID,
            dimensions: dimensions,
            parallelUnits: parallelUnits,
            timestamp: uint40(block.timestamp),
            verified: true,
            metadataURI: metadataURI
        });

        _cidExists[dataCID] = true;
        _cidToTokenId[dataCID] = tokenId;
        _safeMint(recipient, tokenId);
        _setTokenURI(tokenId, metadataURI);

        emit THOTMinted(tokenId, dataCID, dimensions, uint40(block.timestamp));
        return tokenId;
    }

    /**
     * @dev Mint THOT with string data (for TransmuteAgent compatibility)
     * @param dataHash String representation of data hash
     * @return tokenId The ID of the newly minted THOT
     */
    function mintTHOT(string memory dataHash) external onlyOwner returns (uint256) {
        bytes32 dataCID = keccak256(abi.encodePacked(dataHash));
        require(!_cidExists[dataCID], "THOT already exists");
        require(msg.sender != address(0), "Invalid recipient");

        uint256 tokenId = _tokenIdCounter++;
        
        _thotData[tokenId] = THOTData({
            dataCID: dataCID,
            dimensions: 512, // Default THOT512 standard
            parallelUnits: 1,
            timestamp: uint40(block.timestamp),
            verified: true,
            metadataURI: ""
        });

        _cidExists[dataCID] = true;
        _cidToTokenId[dataCID] = tokenId;
        _safeMint(msg.sender, tokenId);

        emit THOTMinted(tokenId, dataCID, 512, uint40(block.timestamp));
        return tokenId;
    }

    /**
     * @dev Get THOT data
     * @param tokenId The THOT token ID
     * @return THOTData structure
     */
    function getTHOTData(uint256 tokenId) 
        external 
        view 
        returns (THOTData memory) 
    {
        require(_ownerOf(tokenId) != address(0), "THOT does not exist");
        return _thotData[tokenId];
    }

    /**
     * @dev Get token ID by CID
     * @param dataCID IPFS CID
     * @return tokenId The token ID associated with the CID
     */
    function getTokenIdByCID(bytes32 dataCID) external view returns (uint256) {
        require(_cidExists[dataCID], "CID does not exist");
        return _cidToTokenId[dataCID];
    }

    /**
     * @dev Verify a THOT
     * @param tokenId The THOT token ID
     * @param verified Verification status
     */
    function verifyTHOT(uint256 tokenId, bool verified) external onlyOwner {
        require(_ownerOf(tokenId) != address(0), "THOT does not exist");
        _thotData[tokenId].verified = verified;
        emit THOTVerified(tokenId, verified);
    }

    /**
     * @dev Check if CID exists
     * @param dataCID IPFS CID
     * @return exists Whether the CID exists
     */
    function cidExists(bytes32 dataCID) external view returns (bool) {
        return _cidExists[dataCID];
    }

    /**
     * @dev Modular dimension validation — extend without modifying mint logic
     * Original: THOT64, THOT512, THOT768
     * cypherpunk2048: THOT1024 (embedding-native), THOT2048 (high-capacity)
     * @param dims Dimension value to validate
     * @return valid Whether the dimension is in the supported set
     */
    function _isValidDimension(uint16 dims) internal pure returns (bool) {
        return (
            dims == 8    ||  // THOT8    — root of THOT, the seed dimension
            dims == 64   ||  // THOT64   — lightweight vectors
            dims == 512  ||  // THOT512  — standard 8x8x8 3D knowledge clusters
            dims == 768  ||  // THOT768  — high-fidelity optimized tensors
            dims == 1024 ||  // THOT1024 — embedding-native (mxbai-embed-large)
            dims == 2048 ||  // THOT2048 — cypherpunk2048 high-capacity
            dims == 4096 ||  // THOT4096 — quantum-aware tensor space
            dims == 8192     // THOT8192 — quantum-aware high-dimensional
        );
    }

    // Override required functions
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721) returns (address) {
        return super._update(to, tokenId, auth);
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
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
