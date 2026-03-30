// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../ERC721Royalty.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title CreatorNFT
 * @notice Production example: Artist NFT platform with royalties and creator verification
 * @dev Demonstrates real-world creator economy use case with ERC2981 royalties
 */
contract CreatorNFT is ERC721Royalty {

    // Creator verification and metadata
    struct CreatorProfile {
        string name;
        string bio;
        string externalUrl;
        address paymentAddress;
        bool verified;
        uint256 totalRoyalties;
        uint256 totalSales;
    }

    mapping(address => CreatorProfile) public creatorProfiles;
    mapping(uint256 => address) public tokenCreators;
    mapping(uint256 => string) public tokenDescriptions;
    mapping(uint256 => uint256) public tokenPrices;
    mapping(uint256 => bool) public tokensForSale;

    // Platform configuration
    uint96 public platformFee = 250; // 2.5% platform fee
    address public platformFeeRecipient;
    uint96 public maxCreatorRoyalty = 1000; // 10% max creator royalty

    // Collection information
    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public mintPrice = 0.01 ether;
    bool public publicMintEnabled = false;

    // Verification system
    mapping(address => bool) public verificationAuthorities;

    // Events
    event CreatorRegistered(address indexed creator, string name);
    event CreatorVerified(address indexed creator, address indexed authority);
    event TokenListed(uint256 indexed tokenId, uint256 price);
    event TokenSold(uint256 indexed tokenId, address indexed buyer, uint256 price);
    event RoyaltyPaid(uint256 indexed tokenId, address indexed recipient, uint256 amount);

    /**
     * @notice Initialize Creator NFT platform
     * @param name Collection name
     * @param symbol Collection symbol
     * @param platformFeeRecipient_ Address to receive platform fees
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        address platformFeeRecipient_,
        address admin
    ) ERC721Royalty(
        name,
        symbol,
        platformFeeRecipient_, // Default royalty recipient
        platformFee,           // Default platform fee
        admin
    ) {
        platformFeeRecipient = platformFeeRecipient_;
        verificationAuthorities[admin] = true;
    }

    /**
     * @notice Register as a creator
     * @param name Creator name
     * @param bio Creator biography
     * @param externalUrl Creator website/social media
     * @param paymentAddress Address to receive payments
     */
    function registerCreator(
        string memory name,
        string memory bio,
        string memory externalUrl,
        address paymentAddress
    ) external {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(paymentAddress != address(0), "Payment address cannot be zero");

        creatorProfiles[msg.sender] = CreatorProfile({
            name: name,
            bio: bio,
            externalUrl: externalUrl,
            paymentAddress: paymentAddress,
            verified: false,
            totalRoyalties: 0,
            totalSales: 0
        });

        emit CreatorRegistered(msg.sender, name);
    }

    /**
     * @notice Verify a creator (only verification authorities)
     * @param creator Creator address
     */
    function verifyCreator(address creator) external {
        require(verificationAuthorities[msg.sender], "Not authorized to verify");
        require(bytes(creatorProfiles[creator].name).length > 0, "Creator not registered");

        creatorProfiles[creator].verified = true;
        emit CreatorVerified(creator, msg.sender);
    }

    /**
     * @notice Creator mints their artwork
     * @param description Artwork description
     * @param royaltyFee Creator royalty fee in basis points (max 10%)
     */
    function creatorMint(
        string memory description,
        uint96 royaltyFee
    ) external payable nonReentrant returns (uint256) {
        require(bytes(creatorProfiles[msg.sender].name).length > 0, "Must be registered creator");
        require(royaltyFee <= maxCreatorRoyalty, "Royalty fee too high");
        require(msg.value >= mintPrice, "Insufficient payment");
        require(nextTokenId() <= MAX_SUPPLY, "Max supply reached");

        uint256 tokenId = mint(
            msg.sender,
            creatorProfiles[msg.sender].paymentAddress,
            royaltyFee
        );

        tokenCreators[tokenId] = msg.sender;
        tokenDescriptions[tokenId] = description;

        // Update creator stats
        creatorProfiles[msg.sender].totalSales++;

        // Pay platform fee
        if (msg.value > mintPrice) {
            payable(msg.sender).transfer(msg.value - mintPrice);
        }
        payable(platformFeeRecipient).transfer(mintPrice);

        return tokenId;
    }

    /**
     * @notice Public mint (if enabled)
     * @param creator Creator to attribute the mint to
     */
    function publicMint(address creator) external payable nonReentrant returns (uint256) {
        require(publicMintEnabled, "Public mint not enabled");
        require(hasRole(MINTER_ROLE, msg.sender), "Must have minter role");
        require(msg.value >= mintPrice, "Insufficient payment");
        require(nextTokenId() <= MAX_SUPPLY, "Max supply reached");

        uint256 tokenId = mint(
            msg.sender,
            address(0), // Use default royalty
            0
        );

        tokenCreators[tokenId] = creator;

        if (msg.value > mintPrice) {
            payable(msg.sender).transfer(msg.value - mintPrice);
        }
        payable(platformFeeRecipient).transfer(mintPrice);

        return tokenId;
    }

    /**
     * @notice List token for sale
     * @param tokenId Token ID
     * @param price Sale price
     */
    function listForSale(uint256 tokenId, uint256 price) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(price > 0, "Price must be greater than 0");

        tokenPrices[tokenId] = price;
        tokensForSale[tokenId] = true;

        emit TokenListed(tokenId, price);
    }

    /**
     * @notice Remove token from sale
     * @param tokenId Token ID
     */
    function removeFromSale(uint256 tokenId) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");

        tokensForSale[tokenId] = false;
        delete tokenPrices[tokenId];
    }

    /**
     * @notice Buy token with automatic royalty distribution
     * @param tokenId Token ID
     */
    function buyToken(uint256 tokenId) external payable nonReentrant {
        require(tokensForSale[tokenId], "Token not for sale");
        require(msg.value >= tokenPrices[tokenId], "Insufficient payment");

        address seller = ownerOf(tokenId);
        uint256 salePrice = tokenPrices[tokenId];

        // Calculate royalty payment
        (address royaltyRecipient, uint256 royaltyAmount) = royaltyInfo(tokenId, salePrice);

        // Calculate platform fee
        uint256 platformFeeAmount = (salePrice * platformFee) / 10000;

        // Calculate seller payment
        uint256 sellerPayment = salePrice - royaltyAmount - platformFeeAmount;

        // Transfer token
        _transfer(seller, msg.sender, tokenId);

        // Remove from sale
        tokensForSale[tokenId] = false;
        delete tokenPrices[tokenId];

        // Distribute payments
        if (royaltyAmount > 0 && royaltyRecipient != address(0)) {
            payable(royaltyRecipient).transfer(royaltyAmount);

            // Update creator royalty stats
            address creator = tokenCreators[tokenId];
            if (creator != address(0)) {
                creatorProfiles[creator].totalRoyalties += royaltyAmount;
            }

            emit RoyaltyPaid(tokenId, royaltyRecipient, royaltyAmount);
        }

        if (platformFeeAmount > 0) {
            payable(platformFeeRecipient).transfer(platformFeeAmount);
        }

        payable(seller).transfer(sellerPayment);

        // Refund excess payment
        if (msg.value > salePrice) {
            payable(msg.sender).transfer(msg.value - salePrice);
        }

        emit TokenSold(tokenId, msg.sender, salePrice);
    }

    /**
     * @notice Get creator information for a token
     * @param tokenId Token ID
     * @return Creator profile
     */
    function getTokenCreator(uint256 tokenId) external view returns (CreatorProfile memory) {
        address creator = tokenCreators[tokenId];
        return creatorProfiles[creator];
    }

    /**
     * @notice Get token information
     * @param tokenId Token ID
     * @return creator Creator address
     * @return description Token description
     * @return price Current price (0 if not for sale)
     * @return forSale Whether token is for sale
     */
    function getTokenInfo(uint256 tokenId) external view returns (
        address creator,
        string memory description,
        uint256 price,
        bool forSale
    ) {
        return (
            tokenCreators[tokenId],
            tokenDescriptions[tokenId],
            tokenPrices[tokenId],
            tokensForSale[tokenId]
        );
    }

    /**
     * @notice Set mint price (admin only)
     * @param newMintPrice New mint price
     */
    function setMintPrice(uint256 newMintPrice) external onlyRole(DEFAULT_ADMIN_ROLE) {
        mintPrice = newMintPrice;
    }

    /**
     * @notice Toggle public minting (admin only)
     * @param enabled Whether public mint is enabled
     */
    function setPublicMintEnabled(bool enabled) external onlyRole(DEFAULT_ADMIN_ROLE) {
        publicMintEnabled = enabled;
    }

    /**
     * @notice Set max creator royalty (admin only)
     * @param maxRoyalty Maximum royalty in basis points
     */
    function setMaxCreatorRoyalty(uint96 maxRoyalty) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(maxRoyalty <= 2000, "Max royalty too high"); // Max 20%
        maxCreatorRoyalty = maxRoyalty;
    }

    /**
     * @notice Add verification authority (admin only)
     * @param authority Address to grant verification rights
     */
    function addVerificationAuthority(address authority) external onlyRole(DEFAULT_ADMIN_ROLE) {
        verificationAuthorities[authority] = true;
    }

    /**
     * @notice Remove verification authority (admin only)
     * @param authority Address to revoke verification rights
     */
    function removeVerificationAuthority(address authority) external onlyRole(DEFAULT_ADMIN_ROLE) {
        verificationAuthorities[authority] = false;
    }

    /**
     * @notice Emergency withdraw (admin only)
     */
    function emergencyWithdraw() external onlyRole(DEFAULT_ADMIN_ROLE) {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to withdraw");
        payable(msg.sender).transfer(balance);
    }
}