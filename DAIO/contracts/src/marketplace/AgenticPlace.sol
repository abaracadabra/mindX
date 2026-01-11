// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "../core/iNFT.sol";

/**
 * @title AgenticPlace
 * @notice Decentralized marketplace for agent services and iNFTs
 * @dev Enhanced marketplace with royalty support and improved security
 */
contract AgenticPlace is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Address for address payable;

    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    iNFT public immutable iNFTContract;

    struct SkillOffer {
        uint256 skillTokenId;
        uint256 price;
        bool isETH;
        address paymentToken;
        address owner;
        bool isActive;
        uint40 createdAt;
        uint40 expiresAt;
    }

    struct RoyaltyInfo {
        address recipient;
        uint256 percentage; // Basis points (10000 = 100%)
    }

    mapping(uint256 => SkillOffer) public skillOffers;
    mapping(uint256 => RoyaltyInfo) public tokenRoyalties;
    mapping(address => bool) public whitelistedPaymentTokens;

    uint256 public constant MAX_ROYALTY_BPS = 2500; // 25%
    uint256 public constant BASIS_POINTS = 10000;

    event SkillOffered(
        uint256 indexed skillTokenId,
        uint256 price,
        bool isETH,
        address paymentToken,
        address indexed owner,
        uint40 expiresAt
    );

    event SkillHired(
        uint256 indexed skillTokenId,
        address indexed hirer,
        address indexed owner,
        uint256 price,
        bool isETH,
        uint256 royaltyAmount
    );

    event SkillRemoved(
        uint256 indexed skillTokenId,
        address indexed owner
    );

    event RoyaltySet(
        uint256 indexed tokenId,
        address recipient,
        uint256 percentage
    );

    event PaymentTokenWhitelisted(address indexed token, bool status);

    constructor(address _iNFTAddress) {
        require(_iNFTAddress != address(0), "Invalid iNFT contract address");
        iNFTContract = iNFT(_iNFTAddress);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
    }

    /**
     * @dev Offer an iNFT skill for hire
     */
    function offerSkill(
        uint256 skillTokenId,
        uint256 price,
        bool isETH,
        address paymentToken,
        uint40 durationDays
    ) external {
        require(iNFTContract.ownerOf(skillTokenId) == msg.sender, "Not token owner");
        require(price > 0, "Price must be greater than 0");
        
        if (!isETH) {
            require(paymentToken != address(0), "Invalid payment token");
            require(whitelistedPaymentTokens[paymentToken], "Payment token not whitelisted");
        }

        uint40 expiresAt = durationDays > 0 
            ? uint40(block.timestamp + (durationDays * 1 days))
            : type(uint40).max;

        skillOffers[skillTokenId] = SkillOffer({
            skillTokenId: skillTokenId,
            price: price,
            isETH: isETH,
            paymentToken: paymentToken,
            owner: msg.sender,
            isActive: true,
            createdAt: uint40(block.timestamp),
            expiresAt: expiresAt
        });

        emit SkillOffered(skillTokenId, price, isETH, paymentToken, msg.sender, expiresAt);
    }

    /**
     * @dev Hire a skill using ETH
     */
    function hireSkillETH(uint256 skillTokenId) external payable nonReentrant {
        SkillOffer memory offer = skillOffers[skillTokenId];
        require(offer.isActive, "Offer not active");
        require(offer.isETH, "Payment must be in ETH");
        require(msg.value >= offer.price, "Insufficient payment");
        require(
            offer.expiresAt == 0 || block.timestamp <= offer.expiresAt,
            "Offer expired"
        );

        uint256 royaltyAmount = _calculateRoyalty(skillTokenId, msg.value);
        uint256 ownerAmount = msg.value - royaltyAmount;

        // Transfer to owner
        payable(offer.owner).sendValue(ownerAmount);

        // Transfer royalty if set
        if (royaltyAmount > 0) {
            RoyaltyInfo memory royalty = tokenRoyalties[skillTokenId];
            if (royalty.recipient != address(0)) {
                payable(royalty.recipient).sendValue(royaltyAmount);
            }
        }

        emit SkillHired(skillTokenId, msg.sender, offer.owner, msg.value, true, royaltyAmount);
    }

    /**
     * @dev Hire a skill using ERC-20 tokens
     */
    function hireSkillERC20(uint256 skillTokenId, uint256 amount) external nonReentrant {
        SkillOffer memory offer = skillOffers[skillTokenId];
        require(offer.isActive, "Offer not active");
        require(!offer.isETH, "Payment must be in ERC-20");
        require(amount >= offer.price, "Insufficient payment");
        require(
            offer.expiresAt == 0 || block.timestamp <= offer.expiresAt,
            "Offer expired"
        );

        IERC20 paymentToken = IERC20(offer.paymentToken);
        
        uint256 royaltyAmount = _calculateRoyalty(skillTokenId, amount);
        uint256 ownerAmount = amount - royaltyAmount;

        // Transfer to owner
        paymentToken.safeTransferFrom(msg.sender, offer.owner, ownerAmount);

        // Transfer royalty if set
        if (royaltyAmount > 0) {
            RoyaltyInfo memory royalty = tokenRoyalties[skillTokenId];
            if (royalty.recipient != address(0)) {
                paymentToken.safeTransferFrom(msg.sender, royalty.recipient, royaltyAmount);
            }
        }

        emit SkillHired(skillTokenId, msg.sender, offer.owner, amount, false, royaltyAmount);
    }

    /**
     * @dev Remove a skill offer
     */
    function removeSkillOffer(uint256 skillTokenId) external {
        SkillOffer memory offer = skillOffers[skillTokenId];
        require(offer.owner == msg.sender, "Not offer owner");
        
        skillOffers[skillTokenId].isActive = false;
        emit SkillRemoved(skillTokenId, msg.sender);
    }

    /**
     * @dev Set royalty for a token
     */
    function setRoyalty(
        uint256 tokenId,
        address recipient,
        uint256 percentageBps
    ) external onlyRole(ADMIN_ROLE) {
        require(percentageBps <= MAX_ROYALTY_BPS, "Royalty too high");
        require(iNFTContract.ownerOf(tokenId) != address(0), "Token doesn't exist");

        tokenRoyalties[tokenId] = RoyaltyInfo({
            recipient: recipient,
            percentage: percentageBps
        });

        emit RoyaltySet(tokenId, recipient, percentageBps);
    }

    /**
     * @dev Whitelist payment token
     */
    function whitelistPaymentToken(address token, bool status) external onlyRole(ADMIN_ROLE) {
        whitelistedPaymentTokens[token] = status;
        emit PaymentTokenWhitelisted(token, status);
    }

    /**
     * @dev Get skill offer details
     */
    function getSkillOffer(uint256 skillTokenId) external view returns (SkillOffer memory) {
        return skillOffers[skillTokenId];
    }

    /**
     * @dev Get royalty info for token
     */
    function getRoyalty(uint256 tokenId) external view returns (RoyaltyInfo memory) {
        return tokenRoyalties[tokenId];
    }

    /**
     * @dev Calculate royalty amount
     */
    function _calculateRoyalty(uint256 tokenId, uint256 salePrice) 
        internal 
        view 
        returns (uint256) 
    {
        RoyaltyInfo memory royalty = tokenRoyalties[tokenId];
        if (royalty.recipient == address(0) || royalty.percentage == 0) {
            return 0;
        }
        return (salePrice * royalty.percentage) / BASIS_POINTS;
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
