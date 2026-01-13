// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Base64.sol";
import "./interfaces/IDynamicNFT.sol";
import "../THOT/marketplace/IAgenticPlace.sol";

/**
 * @title DynamicNFT
 * @notice ERC721 NFT with dynamic metadata support (ERC4906 compatible)
 * @dev Supports metadata updates, IPFS integration, and optional THOT artifact linking
 * @dev Can be used standalone or within mindX orchestration
 * @dev Extends AgenticPlace foundational marketplace for skill trading
 */
contract DynamicNFT is ERC721, ERC721URIStorage, Ownable, IDynamicNFT {
    mapping(uint256 => NFTMetadata) private _metadata;
    mapping(uint256 => bool) private _frozen;
    
    uint256 private _tokenIdCounter;
    string private _baseTokenURI;
    IAgenticPlace internal agenticPlace; // Foundational marketplace reference (internal for inheritance)

    event AgenticPlaceUpdated(address indexed oldPlace, address indexed newPlace);

    constructor(
        string memory name,
        string memory symbol,
        address initialOwner,
        address _agenticPlace
    ) ERC721(name, symbol) Ownable(initialOwner) {
        if (_agenticPlace != address(0)) {
            agenticPlace = IAgenticPlace(_agenticPlace);
        }
    }

    /**
     * @notice Set AgenticPlace marketplace contract
     * @param _agenticPlace Address of AgenticPlace contract
     */
    function setAgenticPlace(address _agenticPlace) external virtual onlyOwner {
        address oldPlace = address(agenticPlace);
        agenticPlace = IAgenticPlace(_agenticPlace);
        emit AgenticPlaceUpdated(oldPlace, _agenticPlace);
    }

    /**
     * @notice Offer this dNFT skill on AgenticPlace marketplace
     * @param tokenId The dNFT token ID
     * @param price Price to hire the skill
     * @param isETH True if payment in ETH, false for ERC20
     * @param paymentToken ERC20 token address (if not ETH)
     * @param expiresAt Expiration timestamp (0 for no expiration)
     */
    function offerSkillOnMarketplace(
        uint256 tokenId,
        uint256 price,
        bool isETH,
        address paymentToken,
        uint40 expiresAt
    ) external virtual {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(address(agenticPlace) != address(0), "AgenticPlace not set");
        
        // Ensure this contract is whitelisted in AgenticPlace
        require(
            agenticPlace.isNFTContractWhitelisted(address(this)),
            "dNFT contract not whitelisted in AgenticPlace"
        );

        agenticPlace.offerSkill(
            tokenId,
            address(this),
            price,
            isETH,
            paymentToken,
            expiresAt
        );
    }

    /**
     * @notice Mint a new dynamic NFT
     * @param to Address to mint the NFT to
     * @param nftMetadata Initial metadata for the NFT
     * @return tokenId The ID of the newly minted token
     */
    function mint(
        address to,
        NFTMetadata memory nftMetadata
    ) public onlyOwner returns (uint256) {
        uint256 tokenId = _tokenIdCounter++;
        _safeMint(to, tokenId);
        
        nftMetadata.isDynamic = true;
        nftMetadata.lastUpdated = block.timestamp;
        _metadata[tokenId] = nftMetadata;
        
        // Set token URI (IPFS or constructed JSON)
        string memory uri = _buildTokenURI(nftMetadata);
        _setTokenURI(tokenId, uri);
        
        return tokenId;
    }

    /**
     * @notice Set token URI directly (convenience function)
     * @param tokenId The token ID
     * @param newURI The new token URI
     */
    function setTokenURI(uint256 tokenId, string memory newURI) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(!_frozen[tokenId], "Token metadata is frozen");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized to update"
        );
        _setTokenURI(tokenId, newURI);
    }

    /**
     * @notice Update metadata for an existing NFT
     * @param tokenId The token ID to update
     * @param newMetadata The new metadata
     */
    function updateMetadata(
        uint256 tokenId,
        NFTMetadata memory newMetadata
    ) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(!_frozen[tokenId], "Token metadata is frozen");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized to update"
        );
        
        newMetadata.isDynamic = true;
        newMetadata.lastUpdated = block.timestamp;
        _metadata[tokenId] = newMetadata;
        
        // Update token URI
        string memory uri = _buildTokenURI(newMetadata);
        _setTokenURI(tokenId, uri);
        
        emit MetadataUpdated(tokenId, newMetadata);
    }

    /**
     * @notice Update token metadata using bytes (alternative interface)
     * @param tokenId The token ID
     * @param metadataBytes Encoded metadata
     */
    function updateTokenMetadata(uint256 tokenId, bytes calldata metadataBytes) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(!_frozen[tokenId], "Token metadata is frozen");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized to update"
        );
        
        // Decode metadata from bytes (simplified - in production, use proper encoding)
        // For now, this is a placeholder that sets URI directly if it's a string
        // In a full implementation, you'd decode the bytes to NFTMetadata struct
        string memory uri = string(metadataBytes);
        _setTokenURI(tokenId, uri);
    }

    /**
     * @notice Freeze metadata to prevent future updates
     * @param tokenId The token ID to freeze
     */
    function freezeMetadata(uint256 tokenId) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized"
        );
        _frozen[tokenId] = true;
        emit MetadataFrozen(tokenId);
    }

    /**
     * @notice Get metadata for a token
     * @param tokenId The token ID
     * @return metadata The metadata struct
     */
    function metadata(uint256 tokenId) external view returns (NFTMetadata memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _metadata[tokenId];
    }

    /**
     * @notice Check if metadata is frozen
     * @param tokenId The token ID
     * @return frozen True if metadata cannot be updated
     */
    function frozen(uint256 tokenId) external view returns (bool) {
        return _frozen[tokenId];
    }

    /**
     * @notice Build token URI from metadata
     * @dev If imageURI is an IPFS CID, returns ipfs:// format
     * @dev Otherwise constructs JSON metadata
     */
    function _buildTokenURI(NFTMetadata memory meta) private pure returns (string memory) {
        // If imageURI is provided and looks like IPFS CID, return direct IPFS URI
        if (bytes(meta.imageURI).length > 0 && 
            (keccak256(bytes(meta.imageURI)) != keccak256(bytes("")))) {
            // Check if it's already a full URI
            if (bytes(meta.imageURI)[0] == bytes("i")[0] && 
                bytes(meta.imageURI)[1] == bytes("p")[0] &&
                bytes(meta.imageURI)[2] == bytes("f")[0] &&
                bytes(meta.imageURI)[3] == bytes("s")[0]) {
                return meta.imageURI;
            }
            // Otherwise construct ipfs:// URI
            return string(abi.encodePacked("ipfs://", meta.imageURI));
        }
        
        // Build JSON metadata
        string memory json = string(abi.encodePacked(
            '{"name":"', meta.name, '",',
            '"description":"', meta.description, '",',
            '"image":"', bytes(meta.imageURI).length > 0 ? 
                string(abi.encodePacked("ipfs://", meta.imageURI)) : "", '",'
        ));
        
        if (bytes(meta.externalURI).length > 0) {
            json = string(abi.encodePacked(json, '"external_url":"', meta.externalURI, '",'));
        }
        
        if (bytes(meta.thotCID).length > 0) {
            json = string(abi.encodePacked(json, '"thot_cid":"', meta.thotCID, '",'));
        }
        
        json = string(abi.encodePacked(
            json,
            '"attributes":[',
            '{"trait_type":"Dynamic","value":', meta.isDynamic ? 'true' : 'false', '},',
            '{"trait_type":"Last Updated","value":"', _uint2str(meta.lastUpdated), '"}',
            ']}'
        ));
        
        // Encode as data URI
        return string(abi.encodePacked(
            "data:application/json;base64,",
            Base64.encode(bytes(json))
        ));
    }

    /**
     * @notice Convert uint256 to string
     */
    function _uint2str(uint256 _i) private pure returns (string memory) {
        if (_i == 0) {
            return "0";
        }
        uint256 j = _i;
        uint256 len;
        while (j != 0) {
            len++;
            j /= 10;
        }
        bytes memory bstr = new bytes(len);
        uint256 k = len;
        while (_i != 0) {
            k = k-1;
            uint8 temp = (48 + uint8(_i - _i / 10 * 10));
            bytes1 b1 = bytes1(temp);
            bstr[k] = b1;
            _i /= 10;
        }
        return string(bstr);
    }

    // Override required functions
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
