// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title iNFT
 * @dev Immutable THOT implementation as ERC721
 */
contract iNFT is ERC721, ERC721URIStorage, Ownable {
    using Strings for uint256;

    struct ThotData {
        bytes32 dataCID;      // IPFS CID hash
        uint8 dimensions;     // 64, 512, or 768
        uint8 parallelUnits;  // Processing units
        uint40 timestamp;     // Creation time
        bool verified;        // Verification status
    }

    mapping(uint256 => ThotData) private _thotData;
    mapping(bytes32 => bool) private _cidExists;
    
    event ThotMinted(
        uint256 indexed tokenId,
        bytes32 indexed dataCID,
        uint8 dimensions,
        uint40 timestamp
    );

    constructor() ERC721("Immutable THOT", "iTHOT") Ownable(msg.sender) {}

    function mint(
        address recipient,
        bytes32 dataCID,
        uint8 dimensions,
        uint8 parallelUnits
    ) external onlyOwner returns (uint256) {
        require(!_cidExists[dataCID], "THOT already exists");
        require(
            dimensions == 64 || dimensions == 512 || dimensions == 768,
            "Invalid dimensions"
        );

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
        require(_exists(tokenId), "THOT does not exist");
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
