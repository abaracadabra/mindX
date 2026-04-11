// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title iNFT
 * @dev Immutable THOT implementation as ERC721
 * @notice Supports THOT64, THOT512, THOT768, THOT1024, THOT2048 (cypherpunk2048 standard)
 */
contract iNFT is ERC721, ERC721URIStorage, Ownable {
    using Strings for uint256;

    struct ThotData {
        bytes32 dataCID;       // IPFS CID hash
        uint16 dimensions;     // 64, 512, 768, 1024, or 2048
        uint8 parallelUnits;   // Processing units
        uint40 timestamp;      // Creation time
        bool verified;         // Verification status
    }

    mapping(uint256 => ThotData) private _thotData;
    mapping(bytes32 => bool) private _cidExists;
    
    event ThotMinted(
        uint256 indexed tokenId,
        bytes32 indexed dataCID,
        uint16 dimensions,
        uint40 timestamp
    );

    constructor() ERC721("Immutable THOT", "iTHOT") Ownable(msg.sender) {}

    /**
     * @dev Modular dimension validation — extend without modifying mint
     * Original: THOT64, THOT512, THOT768
     * cypherpunk2048: THOT1024 (embedding-native), THOT2048 (high-capacity)
     */
    function _isValidDimension(uint16 dims) internal pure returns (bool) {
        return (
            dims == 8    ||  // THOT8    — root of THOT, the seed dimension
            dims == 64   ||  // THOT64   — lightweight
            dims == 512  ||  // THOT512  — standard 8x8x8
            dims == 768  ||  // THOT768  — high-fidelity
            dims == 1024 ||  // THOT1024 — embedding-native (mxbai-embed-large)
            dims == 2048 ||  // THOT2048 — cypherpunk2048 high-capacity
            dims == 4096 ||  // THOT4096 — quantum-aware tensor space
            dims == 8192     // THOT8192 — quantum-aware high-dimensional
        );
    }

    function mint(
        address recipient,
        bytes32 dataCID,
        uint16 dimensions,
        uint8 parallelUnits
    ) external onlyOwner returns (uint256) {
        require(!_cidExists[dataCID], "THOT already exists");
        require(_isValidDimension(dimensions), "Invalid dimensions");

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

        _cidExists[dataCID] = true;
        _safeMint(recipient, tokenId);

        emit ThotMinted(tokenId, dataCID, dimensions, uint40(block.timestamp));
        return tokenId;
    }

    function getThotData(uint256 tokenId)
        external
        view
        returns (ThotData memory)
    {
        require(_ownerOf(tokenId) != address(0), "THOT does not exist");
        return _thotData[tokenId];
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
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
