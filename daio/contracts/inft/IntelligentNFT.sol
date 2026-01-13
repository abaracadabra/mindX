// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../dnft/DynamicNFT.sol";
import "./interfaces/IIntelligentNFT.sol";
import "../THOT/marketplace/IAgenticPlace.sol";

/**
 * @title IntelligentNFT
 * @notice ERC721 NFT with intelligence capabilities extending DynamicNFT
 * @dev iNFTs can interact with agents and exhibit autonomous behavior
 * @dev THOT artifacts are optional but can enhance intelligence
 * @dev Extends AgenticPlace foundational marketplace for skill trading
 */
contract IntelligentNFT is DynamicNFT, IIntelligentNFT {
    mapping(uint256 => IntelligenceConfig) private _intelligence;

    constructor(
        string memory name,
        string memory symbol,
        address initialOwner,
        address _agenticPlace
    ) DynamicNFT(name, symbol, initialOwner, _agenticPlace) {}

    /**
     * @notice Set AgenticPlace marketplace contract
     * @param _agenticPlace Address of AgenticPlace contract
     * @dev Overrides dNFT implementation
     */
    function setAgenticPlace(address _agenticPlace) external override onlyOwner {
        address oldPlace = address(agenticPlace);
        agenticPlace = IAgenticPlace(_agenticPlace);
        emit AgenticPlaceUpdated(oldPlace, _agenticPlace);
    }

    /**
     * @notice Offer this iNFT skill on AgenticPlace marketplace
     * @param tokenId The iNFT token ID
     * @param price Price to hire the skill
     * @param isETH True if payment in ETH, false for ERC20
     * @param paymentToken ERC20 token address (if not ETH)
     * @param expiresAt Expiration timestamp (0 for no expiration)
     * @dev Overrides dNFT implementation to add intelligence-specific checks
     */
    function offerSkillOnMarketplace(
        uint256 tokenId,
        uint256 price,
        bool isETH,
        address paymentToken,
        uint40 expiresAt
    ) external override {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(address(agenticPlace) != address(0), "AgenticPlace not set");
        
        // Ensure this contract is whitelisted in AgenticPlace
        require(
            agenticPlace.isNFTContractWhitelisted(address(this)),
            "iNFT contract not whitelisted in AgenticPlace"
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
    ) external onlyOwner returns (uint256) {
        // Call parent mint function
        uint256 tokenId = super.mint(to, nftMetadata);
        _intelligence[tokenId] = intelConfig;
        
        emit IntelligenceUpdated(tokenId, intelConfig);
        
        return tokenId;
    }

    /**
     * @notice Allow an agent to interact with the NFT
     * @param tokenId The token ID
     * @param interactionData Encoded interaction data
     */
    function agentInteract(
        uint256 tokenId,
        bytes calldata interactionData
    ) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        IntelligenceConfig memory config = _intelligence[tokenId];
        
        require(
            config.agentAddress == msg.sender || 
            owner() == msg.sender ||
            ownerOf(tokenId) == msg.sender,
            "Not authorized agent"
        );
        
        emit AgentInteraction(tokenId, msg.sender, interactionData);
        
        // If autonomous and agent is authorized, allow autonomous action
        if (config.autonomous && config.agentAddress == msg.sender) {
            // Autonomous behavior logic can be implemented here
            // This could trigger on-chain actions, state changes, etc.
        }
    }

    /**
     * @notice Update intelligence configuration
     * @param tokenId The token ID
     * @param newConfig New intelligence configuration
     */
    function updateIntelligence(
        uint256 tokenId,
        IntelligenceConfig memory newConfig
    ) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized to update"
        );
        
        _intelligence[tokenId] = newConfig;
        emit IntelligenceUpdated(tokenId, newConfig);
    }

    /**
     * @notice Get intelligence configuration for a token
     * @param tokenId The token ID
     * @return config The intelligence configuration
     */
    function intelligence(uint256 tokenId) 
        external 
        view 
        returns (IntelligenceConfig memory) 
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _intelligence[tokenId];
    }

    /**
     * @notice Mint with agent address (convenience function)
     * @param to Address to mint the NFT to
     * @param agentAddress Agent address for interaction
     * @param initialURI Initial token URI
     * @return tokenId The ID of the newly minted token
     */
    function mintWithAgent(
        address to,
        address agentAddress,
        string memory initialURI
    ) external onlyOwner returns (uint256) {
        NFTMetadata memory nftMetadata = NFTMetadata({
            name: "",
            description: "",
            imageURI: initialURI,
            externalURI: "",
            thotCID: "",
            isDynamic: true,
            lastUpdated: block.timestamp
        });
        
        IntelligenceConfig memory intelConfig = IntelligenceConfig({
            agentAddress: agentAddress,
            autonomous: false,
            behaviorCID: "",
            thotCID: "",
            intelligenceLevel: 0
        });
        
        return this.mintIntelligent(to, nftMetadata, intelConfig);
    }

    /**
     * @notice Link THOT CID to a token
     * @param tokenId The token ID
     * @param thotCID THOT artifact CID
     */
    function linkTHOT(uint256 tokenId, string memory thotCID) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized"
        );
        
        IntelligenceConfig memory config = _intelligence[tokenId];
        config.thotCID = thotCID;
        _intelligence[tokenId] = config;
        
        // Also update metadata THOT CID
        NFTMetadata memory meta = this.metadata(tokenId);
        meta.thotCID = thotCID;
        this.updateMetadata(tokenId, meta);
        
        emit IntelligenceUpdated(tokenId, config);
    }

    /**
     * @notice Trigger intelligence behavior
     * @param tokenId The token ID
     * @param input Input data for intelligence processing
     * @return output Output from intelligence processing
     */
    function triggerIntelligence(
        uint256 tokenId,
        bytes calldata input
    ) external returns (bytes memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        IntelligenceConfig memory config = _intelligence[tokenId];
        
        require(
            config.agentAddress == msg.sender || 
            owner() == msg.sender ||
            ownerOf(tokenId) == msg.sender,
            "Not authorized"
        );
        
        // Trigger agent interaction
        this.agentInteract(tokenId, input);
        
        // Return empty bytes for now - can be extended with actual intelligence processing
        return "";
    }

    /**
     * @notice Update agent address for a token
     * @param tokenId The token ID
     * @param newAgent New agent address
     */
    function updateAgent(uint256 tokenId, address newAgent) external {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(
            ownerOf(tokenId) == msg.sender || owner() == msg.sender,
            "Not authorized"
        );
        
        IntelligenceConfig memory config = _intelligence[tokenId];
        config.agentAddress = newAgent;
        _intelligence[tokenId] = config;
        
        emit IntelligenceUpdated(tokenId, config);
    }
}
