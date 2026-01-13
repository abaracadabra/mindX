// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Base64.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title gNFT - Graphics NFT
 * @dev Graphics component for visualization of THOT data
 */
contract gNFT is ERC721, Ownable {
    using Strings for uint256;

    struct VisualData {
        string baseImage;     // Base SVG or IPFS image
        string animationUrl;  // Optional 3D/animation URL
        string externalUrl;   // External viewer URL
        uint8 visualType;     // Type of visualization
        bool dynamic;         // Whether visual can be updated
    }

    mapping(uint256 => VisualData) private _visualData;
    mapping(uint256 => mapping(string => string)) private _attributes;
    uint256 private _tokenIdCounter;

    event VisualCreated(
        uint256 indexed tokenId,
        string baseImage,
        uint8 visualType
    );

    event VisualUpdated(
        uint256 indexed tokenId,
        string newBaseImage,
        uint40 timestamp
    );

    constructor() ERC721("Graphics NFT", "gNFT") Ownable(msg.sender) {
        _tokenIdCounter = 1;
    }

    function createVisual(
        address recipient,
        string memory baseImage,
        string memory animationUrl,
        string memory externalUrl,
        uint8 visualType,
        bool dynamic
    ) external onlyOwner returns (uint256) {
        uint256 tokenId = _tokenIdCounter++;

        _visualData[tokenId] = VisualData({
            baseImage: baseImage,
            animationUrl: animationUrl,
            externalUrl: externalUrl,
            visualType: visualType,
            dynamic: dynamic
        });

        _safeMint(recipient, tokenId);
        
        emit VisualCreated(tokenId, baseImage, visualType);
        return tokenId;
    }

    function updateVisual(
        uint256 tokenId,
        string memory newBaseImage,
        string memory newAnimationUrl
    ) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(_visualData[tokenId].dynamic, "Visual is static");

        VisualData storage visual = _visualData[tokenId];
        visual.baseImage = newBaseImage;
        visual.animationUrl = newAnimationUrl;

        emit VisualUpdated(tokenId, newBaseImage, uint40(block.timestamp));
    }

    function setAttribute(
        uint256 tokenId,
        string memory key,
        string memory value
    ) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        _attributes[tokenId][key] = value;
    }

    function tokenURI(uint256 tokenId) 
        public 
        view 
        override 
        returns (string memory) 
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        VisualData memory visual = _visualData[tokenId];

        return string(abi.encodePacked(
            'data:application/json;base64,',
            Base64.encode(bytes(abi.encodePacked(
                '{"name":"gNFT #', 
                tokenId.toString(),
                '","description":"Graphics NFT",',
                '"image":"', 
                visual.baseImage,
                '","animation_url":"',
                visual.animationUrl,
                '","external_url":"',
                visual.externalUrl,
                '"}'
            )))
        ));
    }
}
